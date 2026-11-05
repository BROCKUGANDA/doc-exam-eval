"""Platform API — a read-only view over the benchmark's own artifacts.

Two safety controls exist because this host is reachable by judges:

1. **Reference answers are closed by default.** `solution/reference.json` is the answer key.
   Serving it from the same origin as the model-facing prompt would let a curious model, or
   a reviewer clicking around, see the expected findings. The endpoint returns 404 unless
   `DOCX_EXPOSE_REFERENCE=1` is set explicitly, and a test asserts the default is closed.
   Caddy's read-only rule blocks mutating methods but cannot block a GET, so the app has to
   make this decision itself.

2. **Run triggering is closed by default.** `DOCX_ENABLE_RUN_TRIGGER=1` is required, so a
   misrouted hostname cannot make the platform spend provider quota.

Nothing here imports FastAPI into the benchmark path, so `run_eval.py --validate` still runs
with these packages uninstalled.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from backend.app.store import ArtifactStore, StoreError

EXPOSE_REFERENCE = os.environ.get("DOCX_EXPOSE_REFERENCE", "0") == "1"
ENABLE_RUN_TRIGGER = os.environ.get("DOCX_ENABLE_RUN_TRIGGER", "0") == "1"

app = FastAPI(
    title="DOC-EXAM platform",
    description="Documentary credit examination benchmark: tasks, evidence, results.",
    version="1.0.0",
)
store = ArtifactStore()


def _fail(exc: StoreError) -> None:
    raise HTTPException(status_code=404, detail=str(exc))


@app.get("/healthz")
def health() -> dict[str, Any]:
    """Used by Caddy's health-checked upstreams, so a dead API is a clear 502 upstream."""
    return {
        "status": "ok",
        "reference_exposed": EXPOSE_REFERENCE,
        "run_trigger_enabled": ENABLE_RUN_TRIGGER,
    }


@app.get("/api/v1/tasks")
def tasks() -> Any:
    try:
        return store.list_tasks()
    except StoreError as exc:
        _fail(exc)


@app.get("/api/v1/tasks/{case_id}")
def task_detail(case_id: str) -> Any:
    try:
        return {
            "meta": store.task_meta(case_id),
            "instruction": store.instruction(case_id),
            "grader_config": store.grader_config(case_id),
        }
    except StoreError as exc:
        _fail(exc)


@app.get("/api/v1/tasks/{case_id}/documents")
def task_documents(case_id: str) -> Any:
    """The document index the model sees. Contains no answers."""
    try:
        return store.documents(case_id)
    except StoreError as exc:
        _fail(exc)


@app.get("/api/v1/tasks/{case_id}/reference")
def task_reference(case_id: str) -> Any:
    if not EXPOSE_REFERENCE:
        # 404 rather than 403: a forbidden marker would confirm the endpoint exists and
        # invite probing on a host that is deliberately reachable by anyone with the link.
        raise HTTPException(status_code=404, detail="not found")
    try:
        return store.reference(case_id)
    except StoreError as exc:
        _fail(exc)


@app.get("/api/v1/results")
def results() -> Any:
    try:
        return store.results()
    except StoreError as exc:
        _fail(exc)


@app.get("/api/v1/trials")
def trials(model: str | None = Query(None), task: str | None = Query(None), limit: int = 500) -> Any:
    rows = store.trials(model, task)
    # Transcript bodies are large; the list view returns scores and pointers only.
    for rec in rows:
        rec.pop("raw_output", None)
        rec.pop("normalized_output", None)
    return {"count": len(rows), "trials": rows[:limit]}


@app.get("/api/v1/transcripts")
def transcript(model: str = Query(...), task: str = Query(...), trial: int = Query(1)) -> Any:
    """Full evidence for one trial: prompt hash, settings, raw and normalised output, and the
    per-dimension scorecard. This is what the README's failure analysis points at."""
    rec = store.transcript(model, task, trial)
    if rec is None:
        raise HTTPException(status_code=404, detail="no such trial")
    return rec


@app.get("/api/v1/rulebook")
def rulebook() -> Any:
    return store.rulebook()


@app.get("/api/v1/coverage")
def coverage() -> Any:
    return store.coverage()


@app.get("/api/v1/integrity")
def integrity() -> Any:
    """The grader's own proof: fixture corpus size per task and the lever inventory that the
    mutation suite is required to break. Displayed because 'we validated the grader' is worth
    nothing unless a reviewer can see what was validated."""
    from benchmark.generator.build import build_case
    from benchmark.generator.scenarios import SCENARIOS
    from benchmark.rulebook import rulebook
    from benchmark.validation.fixtures import build_fixtures
    from benchmark.validation.levers import GRADER_LEVERS, INDEX_LEVERS

    rb = rulebook()
    fixtures = {}
    for case_id, scenario in sorted(SCENARIOS.items()):
        built = build_case(scenario, rb)
        fixtures[case_id] = [f.name for f in build_fixtures(built.truth, built.package, rb)]

    return {
        "fixtures_by_task": fixtures,
        "fixture_total": sum(len(v) for v in fixtures.values()),
        "grader_levers": GRADER_LEVERS,
        "index_levers": INDEX_LEVERS,
        "rulebook_version": rb.version,
        "rulebook_fingerprint": rb.fingerprint(),
    }


@app.get("/api/v1/providers")
def providers() -> Any:
    """Reachability evidence from the live probe. Keys are never included or read here."""
    return {"probe": store.probe(), "models_lock": store.models_lock()}


@app.post("/api/v1/runs")
def start_run() -> Any:
    if not ENABLE_RUN_TRIGGER:
        raise HTTPException(
            status_code=503,
            detail="run triggering is disabled on this deployment; set DOCX_ENABLE_RUN_TRIGGER=1",
        )
    return JSONResponse({"accepted": False, "reason": "not implemented in this build"}, status_code=501)


@app.exception_handler(StoreError)
def _store_error(_: Any, exc: StoreError) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=404)
