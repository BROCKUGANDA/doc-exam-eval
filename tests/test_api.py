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


def test_task_endpoint_rejects_malformed_ids(client):
    response = client.get("/api/v1/tasks/not-a-task")
    assert response.status_code == 404
    assert response.json()["detail"] == "invalid task id"


@pytest.mark.parametrize(
    "method", ["task_meta", "instruction", "documents", "reference", "grader_config"]
)
def test_artifact_store_rejects_task_ids_that_are_not_path_components(tmp_path, method):
    from backend.app.store import ArtifactStore, StoreError

    store = ArtifactStore(root=tmp_path)
    with pytest.raises(StoreError, match="invalid task id"):
        getattr(store, method)("../../README.md")


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


def test_trial_list_omits_bodies_but_transcript_returns_them(tmp_path):
    """Run against a journal the test writes, not against the author's panel results.

    The first version read `benchmark/results/runs/`, which passes on the machine that ran the
    panel and fails in a container built from a clean clone — the image deliberately excludes
    the journals (.dockerignore), because shipping them is the packer's job, not the image's.
    A test that is green on one box is not a test.
    """
    import backend.app.main as main_mod
    from backend.app.store import ArtifactStore

    runs = tmp_path / "benchmark" / "results" / "runs"
    runs.mkdir(parents=True)
    record = {
        "provider": "groq", "model_id": "openai/test-model", "case_id": "DOC-001", "trial": 1,
        "status": "ok", "raw_output": '```json\n{"assessment": "CLEAR"}\n```',
        "normalized_output": {"assessment": "CLEAR"},
        "scorecard": {
            "total": 88.0, "passed": True,
            "dimensions": [{"name": "recall", "weight": 25, "ratio": 1.0, "points": 25.0,
                            "detail": "2/2 findings detected"}],
        },
        "settings": {"temperature": 0.0, "max_output_tokens": 8000}, "latency_s": 1.2,
    }
    records = [dict(record, trial=trial) for trial in (1, 2, 3)]
    (runs / "panel-test.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in records), encoding="utf-8", newline="\n"
    )

    importlib.reload(main_mod)
    main_mod.store = ArtifactStore(root=tmp_path)
    scoped = TestClient(main_mod.app)

    listing = scoped.get("/api/v1/trials", params={"limit": 1, "offset": 1}).json()
    assert listing["count"] == 3, "count must describe the full filtered result set"
    assert listing["limit"] == 1 and listing["offset"] == 1
    assert [trial["trial"] for trial in listing["trials"]] == [2]
    assert all("raw_output" not in t for t in listing["trials"]), "the list must not carry bodies"

    detail = scoped.get(
        "/api/v1/transcripts",
        params={"model": "groq:openai/test-model", "task": "DOC-001", "trial": 1},
    ).json()
    assert detail["raw_output"]
    assert detail["scorecard"]["dimensions"]

    missing = scoped.get(
        "/api/v1/transcripts",
        params={"model": "groq:openai/test-model", "task": "DOC-002", "trial": 1},
    )
    assert missing.status_code == 404, "an unrecorded trial is absent, not silently empty"


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": -1}, {"limit": 501}, {"offset": -1}])
def test_trial_list_rejects_invalid_page_windows(client, params):
    response = client.get("/api/v1/trials", params=params)
    assert response.status_code == 422


def test_transcript_rejects_invalid_task_and_trial_parameters(client):
    invalid_task = client.get("/api/v1/transcripts", params={"model": "demo", "task": "../README"})
    invalid_trial = client.get(
        "/api/v1/transcripts", params={"model": "demo", "task": "DOC-001", "trial": 0}
    )
    assert invalid_task.status_code == 422
    assert invalid_trial.status_code == 422


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
