"""Panel runner: real requests, normalised output, deterministic grading, journaled.

Three properties here decide whether the results mean anything:

1. **The transcript keeps the raw bytes and the grader sees the normalised text.** Some
   providers wrap the answer in a reasoning block (qwen3.6-27b emits literal think tags).
   Grading the raw text would score a correct answer as unparseable; grading only the
   cleaned text without keeping the raw would make the transcript useless as evidence. Both
   are stored, and the transformation applied is recorded on the trial.

2. **A transport failure is never a model failure.** Empty completions, 429s and 5xx are
   journaled as provider/transport errors with their HTTP status, and are excluded from the
   denominator rather than counted as zeros. A 0% pass rate that is really an outage is the
   exact warning sign the guide says to investigate before reporting (p.11).

3. **Retries are bounded and honour retry-after.** Free tiers throttle; unbounded retrying
   just spends the day's quota on one model.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from typing import Any, Callable

from benchmark.generator.build import Scenario
from benchmark.graders.scoring import grade
from benchmark.harness.client import ProviderError, Completion, complete
from benchmark.harness.context import budget
from benchmark.harness.journal import Journal, Trial, utc_now
from benchmark.harness.panel import ModelSpec, Panel
from benchmark.harness.providers import Provider, provider
from benchmark.package import Package
from benchmark.rulebook.model import Rulebook
from benchmark.tasks import prompt_for
from benchmark.truth.engine import GroundTruth

RETRYABLE = {408, 409, 425, 429, 500, 502, 503, 504}

#: Consecutive provider failures tolerated before a model is abandoned for the run.
CIRCUIT_BREAKER = 3

THINK_BLOCK = re.compile(r"<\s*(think|thinking)\b[^>]*>.*?<\s*/\s*\1\s*>", re.IGNORECASE | re.DOTALL)
FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def normalize_output(text: str) -> tuple[str, list[str]]:
    """Reduce a model's reply to the reportable payload, recording what was removed."""
    notes: list[str] = []
    out = text

    stripped = THINK_BLOCK.sub("", out)
    if stripped != out:
        notes.append("removed think block(s)")
        out = stripped
    if "<" in out and "/think>" in out.lower():
        tail = re.split(r"<\s*/\s*think\s*>", out, flags=re.IGNORECASE)[-1]
        if tail.strip() != out.strip():
            notes.append("kept text after final think close tag")
            out = tail

    fenced = FENCE.sub("", out.strip())
    if fenced != out.strip():
        notes.append("stripped markdown code fence")
        out = fenced

    return out.strip(), notes


def _with_backoff(
    fn: Callable[[int], Completion],
    *,
    max_attempts: int = 5,
    sleep: Callable[[float], None] = time.sleep,
    base_delay: float = 2.0,
) -> tuple[Completion, int]:
    last: ProviderError | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn(attempt), attempt
        except ProviderError as exc:
            last = exc
            retryable = exc.status is None or exc.status in RETRYABLE
            if not retryable or attempt == max_attempts:
                exc.attempts = attempt  # type: ignore[attr-defined]
                raise
            delay = exc.retry_after if exc.retry_after else base_delay * (2 ** (attempt - 1))
            sleep(min(float(delay), 60.0))
    raise last  # pragma: no cover - loop always returns or raises


def run_panel(
    cases: dict[str, tuple[Package, GroundTruth]],
    scenarios: dict[str, Scenario],
    rb: Rulebook,
    panel: Panel,
    journal: Journal,
    *,
    call: Callable[..., Completion] = complete,
    sleep: Callable[[float], None] = time.sleep,
    resolve: Callable[[str], Provider] = provider,
    only: list[str] | None = None,
    on_trial: Callable[[Trial], None] | None = None,
) -> list[Trial]:
    done = journal.completed()
    written: list[Trial] = []
    targets = sorted(cases) if not only else [c for c in sorted(cases) if c in set(only)]

    for spec in panel.models:
        prov = resolve(spec.provider)
        consecutive_errors = 0
        abandoned = False

        for case_id in targets:
            if abandoned:
                break
            package, truth = cases[case_id]
            prompt = prompt_for(scenarios[case_id], package, rb)
            prompt_sha = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
            bud = budget(prompt, window=spec.window)

            for trial_index in range(1, panel.trials + 1):
                key = f"{case_id}::{spec.model_id}::{trial_index}"
                if key in done:
                    continue

                trial = Trial(
                    panel_id=panel.panel_id,
                    case_id=case_id,
                    model_id=spec.model_id,
                    provider=spec.provider,
                    trial=trial_index,
                    status="running",
                    started_at=utc_now(),
                    prompt_sha256=prompt_sha,
                    prompt_tokens_estimated=bud.prompt_tokens,
                    settings={
                        "temperature": panel.temperature,
                        "max_output_tokens": spec.max_output_tokens,
                        "assumed_window_tokens": spec.window,
                        "extra_request_params": spec.extra or {},
                        "context_fit": bud.to_dict(),
                    },
                )

                if not bud.fits:
                    trial.status = "skipped_context"
                    trial.error = (
                        f"prompt needs ~{bud.required_window} tokens of window but the panel "
                        f"assumes {spec.window}; refusing to send a prompt that may be truncated"
                    )
                    trial.finished_at = utc_now()
                    journal.append(trial)
                    written.append(trial)
                    if on_trial:
                        on_trial(trial)
                    continue

                try:
                    completion, attempts = _with_backoff(
                        lambda a: call(
                            prov,
                            spec.model_id,
                            prompt,
                            temperature=panel.temperature,
                            max_output_tokens=spec.max_output_tokens,
                            extra=spec.extra or None,
                        ),
                        sleep=sleep,
                    )
                except ProviderError as exc:
                    trial.status = "provider_error"
                    trial.error = str(exc)[:400]
                    trial.attempt = getattr(exc, "attempts", 1)
                    trial.finished_at = utc_now()
                    journal.append(trial)
                    written.append(trial)
                    if on_trial:
                        on_trial(trial)
                    consecutive_errors += 1
                    if consecutive_errors >= CIRCUIT_BREAKER:
                        # Quota exhaustion is a daily property of the account, not a transient
                        # blip. Retrying the remaining tasks would spend the window's time to
                        # produce the same 429, so the model is abandoned and reported as a
                        # coverage gap rather than silently padded with zeros.
                        print(
                            f"  !! {spec.spec_id}: {consecutive_errors} consecutive provider "
                            f"errors -- abandoning remaining tasks for this model",
                            file=sys.stderr,
                        )
                        abandoned = True
                        break
                    continue
                except Exception as exc:  # noqa: BLE001 - transport failure is data
                    consecutive_errors += 1
                    trial.status = "transport_error"
                    trial.error = f"{type(exc).__name__}: {exc}"[:400]
                    trial.finished_at = utc_now()
                    journal.append(trial)
                    written.append(trial)
                    if on_trial:
                        on_trial(trial)
                    continue

                consecutive_errors = 0
                trial.raw_output = completion.text
                trial.normalized_output, notes = normalize_output(completion.text)
                trial.normalization = notes
                trial.prompt_tokens_reported = completion.prompt_tokens
                trial.completion_tokens_reported = completion.completion_tokens
                trial.latency_s = round(completion.latency_s, 3)
                trial.settings.update(
                    {"content_field": completion.settings.get("content_field"), "attempts": attempts}
                )
                trial.finish_reason = completion.finish_reason
                trial.reasoning_tokens = completion.reasoning_tokens

                if completion.finish_reason == "length":
                    # We cut the model off. Grading this would record a transport limit as a
                    # capability failure, which is what invalidated panel 1.
                    trial.status = "truncated_output"
                    trial.error = (
                        f"completion hit max_output_tokens={spec.max_output_tokens} "
                        f"(reasoning_tokens={completion.reasoning_tokens}); not graded"
                    )
                    trial.finished_at = utc_now()
                    journal.append(trial)
                    written.append(trial)
                    if on_trial:
                        on_trial(trial)
                    continue

                # A truncated prompt shows up as the provider reporting far fewer prompt
                # tokens than we counted. Recorded rather than silently graded.
                reported = completion.prompt_tokens
                if reported and bud.prompt_tokens and reported < int(bud.prompt_tokens * 0.8):
                    trial.settings["possible_truncation"] = {
                        "estimated": bud.prompt_tokens,
                        "reported": reported,
                    }

                try:
                    card = grade(truth, package, trial.normalized_output, rb)
                    trial.scorecard = card.to_dict()
                    trial.status = "ok"
                except Exception as exc:  # noqa: BLE001 - a grader crash must not lose the transcript
                    trial.status = "graded_error"
                    trial.error = f"{type(exc).__name__}: {exc}"[:400]

                trial.finished_at = utc_now()
                journal.append(trial)
                written.append(trial)
                if on_trial:
                    on_trial(trial)

    return written


def regrade(journal: Journal, cases: dict[str, tuple[Package, GroundTruth]], rb: Rulebook) -> dict[str, int]:
    """Re-score every stored transcript with the current grader, without a single request.

    Graders get fixed — the citation-resolution bug is the example — and re-running a panel
    to re-apply a grading change would spend quota to reproduce a result that is already on
    disk. The transcripts are the evidence; the score is a function of the transcript and the
    grader, so it is recomputed, and the raw output is never rewritten.
    """
    records = list(journal.records())
    changed = {"regraded": 0, "unchanged": 0, "skipped": 0}
    for rec in records:
        if rec.get("status") != "ok":
            changed["skipped"] += 1
            continue
        pair = cases.get(rec["case_id"])
        if not pair:
            changed["skipped"] += 1
            continue
        package, truth = pair
        card = grade(truth, package, rec.get("normalized_output", ""), rb)
        if card.to_dict() != rec.get("scorecard"):
            rec["scorecard"] = card.to_dict()
            changed["regraded"] += 1
        else:
            changed["unchanged"] += 1

    tmp = journal.path.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    tmp.replace(journal.path)
    return changed


def panel_totals(panel: Panel, n_cases: int) -> dict[str, Any]:
    return {
        "models": len(panel.models),
        "tasks": n_cases,
        "trials_per_task": panel.trials,
        "planned_requests": len(panel.models) * n_cases * panel.trials,
    }
