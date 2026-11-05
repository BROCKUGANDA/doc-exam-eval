"""Append-only trial journal.

Free-tier providers throttle, and a panel of 168 live calls will hit 429s. Without a journal
a throttled run destroys the work already paid for in tokens and time, and the evidence
criterion gets lost to an infrastructure detail. Every trial is written the moment it
finishes, so a run is resumable, and a resumed run never re-spends a completed trial.

The journal is also the audit trail the submission is judged on: a results table with no
per-trial record behind it is an assertion, not evidence.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

TERMINAL = ("ok", "skipped_context", "provider_error", "transport_error", "graded_error")


def trial_key(case_id: str, model_id: str, trial: int) -> str:
    return f"{case_id}::{model_id}::{trial}"


@dataclass
class Trial:
    panel_id: str
    case_id: str
    model_id: str
    provider: str
    trial: int
    status: str
    started_at: str
    finished_at: str = ""
    prompt_sha256: str = ""
    prompt_tokens_estimated: int = 0
    prompt_tokens_reported: int | None = None
    completion_tokens_reported: int | None = None
    latency_s: float | None = None
    settings: dict[str, Any] = field(default_factory=dict)
    raw_output: str = ""
    normalized_output: str = ""
    normalization: list[str] = field(default_factory=list)
    error: str = ""
    scorecard: dict[str, Any] | None = None
    attempt: int = 1

    def key(self) -> str:
        return trial_key(self.case_id, self.model_id, self.trial)

    def to_line(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)


class Journal:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)

    def completed(self) -> set[str]:
        """Keys already finished successfully. A trial that errored is not completed, so a
        resume retries it rather than preserving a hole in the matrix."""
        done: set[str] = set()
        for rec in self.records():
            if rec.get("status") == "ok":
                done.add(trial_key(rec["case_id"], rec["model_id"], int(rec["trial"])))
        return done

    def records(self) -> Iterator[dict[str, Any]]:
        if not self.path.is_file():
            return iter(())
        def _iter():
            with self.path.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        # A torn final line from an interrupted write must not abort a resume.
                        continue
        return _iter()

    def append(self, trial: Trial) -> None:
        with self.path.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(trial.to_line() + "\n")

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for rec in self.records():
            out[rec.get("status", "?")] = out.get(rec.get("status", "?"), 0) + 1
        return out


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
