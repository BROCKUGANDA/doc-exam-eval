"""Artifact store — the platform reads what the CLI wrote, and nothing else.

There is deliberately no database behind this. The journal and results files are the
evidence; a second copy in Postgres could drift from them, and a dashboard whose numbers
disagree with `run_eval.py` is worse than no dashboard. So every endpoint here is a view over
files the benchmark already produces, and the same figures appear in the UI, the README and
the ZIP.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any

from benchmark.paths import REPO_ROOT, TASKS_DIR

_TASK_ID = re.compile(r"DOC-\d{3}\Z")


class StoreError(Exception):
    pass


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise StoreError(f"missing artifact: {path.relative_to(REPO_ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


class ArtifactStore:
    def __init__(self, root: Path = REPO_ROOT):
        self.root = root
        self.tasks_dir = root / "benchmark" / "tasks"
        self.results_dir = root / "benchmark" / "results"
        self.runs_dir = self.results_dir / "runs"

    def _task_dir(self, case_id: str) -> Path:
        """Resolve a task only when its identifier is a single expected path component."""
        if _TASK_ID.fullmatch(case_id) is None:
            raise StoreError("invalid task id")
        return self.tasks_dir / case_id

    # ---- tasks -------------------------------------------------------------
    def list_tasks(self) -> list[dict[str, Any]]:
        out = []
        for case_dir in sorted(p for p in self.tasks_dir.glob("DOC-*") if p.is_dir()):
            meta = self.task_meta(case_dir.name)
            out.append(
                {
                    "case_id": case_dir.name,
                    "title": meta.get("title"),
                    "expected_findings": meta.get("expected_findings"),
                    "expected_unresolved": meta.get("expected_unresolved"),
                    "prompt_tokens_estimate": meta.get("prompt_tokens_estimate"),
                    "has_instruction": (case_dir / "instruction.md").is_file(),
                }
            )
        return out

    def task_meta(self, case_id: str) -> dict[str, Any]:
        path = self._task_dir(case_id) / "task.toml"
        if not path.is_file():
            raise StoreError(f"no task.toml for {case_id}")
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
        return {**raw.get("task", {}), **raw.get("environment", {}), **raw.get("grading", {})}

    def instruction(self, case_id: str) -> str:
        path = self._task_dir(case_id) / "instruction.md"
        if not path.is_file():
            raise StoreError(f"no instruction for {case_id}")
        return path.read_text(encoding="utf-8")

    def documents(self, case_id: str) -> dict[str, Any]:
        """The machine index: doc ids, pages, fields with their locations.

        This is the model-visible package, so serving it publicly leaks nothing.
        """
        return _read_json(self._task_dir(case_id) / "environment" / "documents.json")

    def reference(self, case_id: str) -> dict[str, Any]:
        """Ground truth. Callers must gate this behind the exposure flag."""
        return _read_json(self._task_dir(case_id) / "solution" / "reference.json")

    def grader_config(self, case_id: str) -> dict[str, Any]:
        return _read_json(self._task_dir(case_id) / "tests" / "grader_config.json")

    # ---- results ----------------------------------------------------------
    def results(self) -> dict[str, Any]:
        return _read_json(self.results_dir / "results.json")

    def probe(self) -> list[dict[str, Any]]:
        path = self.results_dir / "probe.json"
        return _read_json(path) if path.is_file() else []

    def models_lock(self) -> dict[str, Any]:
        path = self.results_dir / "models.lock.json"
        return _read_json(path) if path.is_file() else {}

    def trials(self, model_id: str | None = None, case_id: str | None = None) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        if not self.runs_dir.is_dir():
            return records
        for path in sorted(self.runs_dir.glob("*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if model_id and f"{rec.get('provider')}:{rec.get('model_id')}" != model_id:
                    continue
                if case_id and rec.get("case_id") != case_id:
                    continue
                records.append(rec)
        return records

    def transcript(self, model_id: str, case_id: str, trial: int) -> dict[str, Any] | None:
        for rec in self.trials(model_id, case_id):
            if int(rec.get("trial", 0)) == int(trial):
                return rec
        return None

    # ---- rulebook ---------------------------------------------------------
    def rulebook(self) -> dict[str, Any]:
        from benchmark.rulebook import rulebook

        rb = rulebook()
        return {
            "version": rb.version,
            "fingerprint": rb.fingerprint(),
            "markdown": rb.markdown(),
            "rules": [
                {
                    "id": r.id,
                    "title": r.title,
                    "kind": r.kind,
                    "severity": r.severity,
                    "codes": r.codes,
                    "applies_to": {"docs": r.applies_to.docs, "fields": r.applies_to.fields},
                    "statement": str(r.statement).strip(),
                }
                for r in rb.rules
            ],
            "codes": sorted(rb.codes),
            "code_to_rules": {k: v for k, v in sorted(rb.code_to_rules.items())},
        }

    def coverage(self) -> dict[str, Any]:
        """Which rules and codes the tasks actually exercise, straight from the linter."""
        from benchmark.generator.build import build_case
        from benchmark.generator.scenarios import SCENARIOS
        from benchmark.rulebook import rulebook
        from benchmark.validation.lint_tasks import suite_report

        rb = rulebook()
        cases = {cid: (b.package, b.truth) for cid, b in ((k, build_case(v, rb)) for k, v in SCENARIOS.items())}
        return suite_report(cases, rb)
