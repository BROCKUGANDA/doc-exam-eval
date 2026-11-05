"""API tests, including the two controls that matter on a judge-reachable host.

The answer-key test is the important one: the platform serves the prompt and the documents
from the same origin as everything else, so a reference endpoint that is merely
"authenticated" would still be discoverable. It is asserted closed by default, and closed
under the default environment, and no response anywhere may contain credential-shaped text.
"""

from __future__ import annotations

import importlib
import json
import re

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    import backend.app.main as main_mod

    importlib.reload(main_mod)
    return TestClient(main_mod.app)


def test_health_reports_which_controls_are_open(client):
    body = client.get("/healthz").json()
    assert body["status"] == "ok"
    assert body["reference_exposed"] is False
    assert body["run_trigger_enabled"] is False


def test_lists_all_eight_tasks(client):
    rows = client.get("/api/v1/tasks").json()
    assert len(rows) == 8
    assert {r["case_id"] for r in rows} == {f"DOC-00{i}" for i in range(1, 9)}


def test_task_detail_exposes_prompt_but_not_answers(client):
    body = client.get("/api/v1/tasks/DOC-002").json()
    assert "rulebook" in body["instruction"].lower()
    assert "Total amount" in body["instruction"]
    blob = json.dumps(body)
    assert "GT-00" not in blob, "answer identifiers leaked through the task endpoint"
    assert "finding_id" not in blob


def test_documents_endpoint_is_the_model_visible_index(client):
    docs = client.get("/api/v1/tasks/DOC-002/documents").json()
    ids = [d["doc_id"] for d in docs["documents"]]
    assert "INV-001" in ids and "LC-001" in ids


def test_reference_endpoint_is_closed_by_default(client):
    """The answer key must not be fetchable from a host anyone can open."""
    for case_id in ("DOC-001", "DOC-002", "DOC-008"):
        resp = client.get(f"/api/v1/tasks/{case_id}/reference")
        assert resp.status_code == 404, (
            f"{case_id} reference returned {resp.status_code}; the answer key is exposed"
        )


def test_reference_opens_only_when_explicitly_enabled(monkeypatch):
    monkeypatch.setenv("DOCX_EXPOSE_REFERENCE", "1")
    import backend.app.main as main_mod

    importlib.reload(main_mod)
    scoped = TestClient(main_mod.app)
    resp = scoped.get("/api/v1/tasks/DOC-002/reference")
    assert resp.status_code == 200
    assert resp.json()["findings"]
    monkeypatch.setenv("DOCX_EXPOSE_REFERENCE", "0")
    importlib.reload(main_mod)


def test_run_trigger_is_disabled_by_default(client):
    assert client.post("/api/v1/runs").status_code == 503


def test_results_endpoint_matches_the_cli_artifact(client):
    from benchmark.paths import RESULTS_DIR

    api = client.get("/api/v1/results").json()
    disk = json.loads((RESULTS_DIR / "results.json").read_text(encoding="utf-8"))
    assert api == disk, "the dashboard and the CLI must not disagree"


def test_trial_list_omits_bodies_but_transcript_returns_them(client):
    listing = client.get("/api/v1/trials").json()
    assert listing["count"] > 0
    assert all("raw_output" not in t for t in listing["trials"])

    first = listing["trials"][0]
    detail = client.get(
        "/api/v1/transcripts",
        params={"model": f"{first['provider']}:{first['model_id']}", "task": first["case_id"], "trial": first["trial"]},
    ).json()
    assert detail["raw_output"]
    assert detail["scorecard"]["dimensions"]


def test_rulebook_and_coverage_endpoints(client):
    rb = client.get("/api/v1/rulebook").json()
    assert len(rb["rules"]) == 23
    assert rb["version"] == "1.0.0"

    cov = client.get("/api/v1/coverage").json()
    assert cov["rules_never_exercised"] == []
    assert cov["tasks"] == 8


def test_no_response_leaks_a_credential_shaped_string(client):
    """Defence in depth for the public host: even a misconfigured deployment must not echo
    a key that happens to be in the environment."""
    secret = re.compile(r"gsk_[A-Za-z0-9_\-]{16,}|AIza[A-Za-z0-9_\-]{20,}|sk-or-v1-[A-Za-z0-9]{16,}")
    paths = [
        "/healthz",
        "/api/v1/tasks",
        "/api/v1/tasks/DOC-001",
        "/api/v1/tasks/DOC-001/documents",
        "/api/v1/results",
        "/api/v1/rulebook",
        "/api/v1/coverage",
        "/api/v1/providers",
    ]
    for path in paths:
        resp = client.get(path)
        assert resp.status_code == 200, path
        assert not secret.search(resp.text), f"{path} contains a credential-shaped string"
