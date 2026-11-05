"""Panel specification — which models the experiment runs, and why each is there.

The default panel is derived from benchmark/results/probe.json, i.e. from requests that
actually completed, rather than from a typed list of models someone remembered. That matters
because the probe disproved two ids that the published Groq models page lists, and an
unreachable model in the panel would show up as a 0% pass rate instead of an absent row.

Context windows are deliberately conservative and labelled as assumed. The budget gate uses
them to *refuse* a trial rather than risk a truncated prompt, so an under-estimate costs a
missing data point while an over-estimate would silently corrupt one.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# provider:model_id -> (family, closed_weights, assumed_window_tokens, note)
#: Windows are not reported by /models, so these are conservative assumptions, not vendor
#: claims. A wrong value can only ever cause a refusal, never a truncated prompt.
CLASSIFICATION: dict[str, tuple[str, bool, int, str]] = {
    "groq:openai/gpt-oss-120b": ("openai/gpt-oss", True, 131_072, "largest open-weight callable here"),
    "groq:openai/gpt-oss-20b": ("openai/gpt-oss", True, 131_072, "smaller sibling of the 120b"),
    "groq:qwen/qwen3.8-27b": ("qwen", True, 131_072, "emits clean JSON; no think tags"),
    "groq:qwen/qwen3.6-27b": ("qwen", True, 131_072, "wraps output in <think> tags"),
    # Measured, not assumed: sending the real DOC-001 prompt (~5,004 tokens) returns
    # HTTP 400 "Please reduce the length of the messages". The gate's refusal is therefore
    # backed by provider behaviour rather than by a guess.
    "groq:allam-2-7b": ("allam", True, 4_096, "verified: HTTP 400 rejects the 5k task prompt"),
    "gemini:models/gemini-3.5-flash-lite": ("gemini", False, 1_048_576, "closed, lightweight tier"),
    "gemini:models/gemini-flash-lite-latest": ("gemini", False, 1_048_576, "closed, lightweight tier"),
    "openrouter:*": ("various", None, 0, "402 insufficient credits — not callable"),
}

# Reasoning models spend part of the completion budget on hidden thinking. At 3000
# tokens several providers returned truncated JSON, which the grader scored as 0 and
# which looked like a capability failure. The budget now leaves room for a long report.
MAX_OUTPUT_TOKENS = 8000

#: Bumped when a harness fix invalidates a previous run. Panel 1 was produced before reasoning effort was pinned, so its zeros are artifacts and must not be reported as results.
PANEL_VERSION = "02"

#: Reasoning controls, keyed by family. Measured, not guessed: at Groq's default effort,
#: gpt-oss-20b spent 2,998 of 3,000 and 7,998 of 8,000 completion tokens on hidden thinking
#: and returned no answer at all, which the grader scored as a capability failure.
REASONING_PARAMS: dict[str, dict[str, object]] = {
    "openai/gpt-oss": {"reasoning_effort": "low"},
}


@dataclass
class ModelSpec:
    provider: str
    model_id: str
    family: str
    closed_weights: bool
    window: int
    max_output_tokens: int = MAX_OUTPUT_TOKENS
    note: str = ""
    #: Published list price in USD per million tokens, with the date it was read. Left None
    #: unless verified, because an invented rate would put a false number in the results table.
    rate_in_per_mtok: float | None = None
    rate_out_per_mtok: float | None = None
    #: Extra request-body parameters. Groq's gpt-oss defaults to a reasoning effort that
    #: consumes the whole completion budget and returns no answer; without pinning this to
    #: "low" the model scores 0 for a reason that has nothing to do with the task.
    extra: dict[str, object] | None = None

    @property
    def spec_id(self) -> str:
        return f"{self.provider}:{self.model_id}"


@dataclass
class Panel:
    panel_id: str
    models: list[ModelSpec]
    trials: int = 3
    temperature: float = 0.0
    source: str = "derived from probe.json"
    excluded: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "panel_id": self.panel_id,
            "trials_per_task": self.trials,
            "temperature": self.temperature,
            "source": self.source,
            "models": [
                {
                    "spec_id": m.spec_id,
                    "provider": m.provider,
                    "model_id": m.model_id,
                    "family": m.family,
                    "closed_weights": m.closed_weights,
                    "assumed_window_tokens": m.window,
                    "max_output_tokens": m.max_output_tokens,
                    "note": m.note,
                    "rate_in_per_mtok": m.rate_in_per_mtok,
                    "rate_out_per_mtok": m.rate_out_per_mtok,
                }
                for m in self.models
            ],
            "excluded_after_probing": self.excluded,
        }


def from_probe(probe_path: Path, panel_path: Path | None = None, trials: int = 3) -> Panel:
    """Build the runnable panel from measured probe results."""
    if panel_path and panel_path.is_file():
        raw = json.loads(panel_path.read_text(encoding="utf-8"))
        models = [
            ModelSpec(
                provider=m["provider"],
                model_id=m["model_id"],
                family=m.get("family", m["model_id"]),
                closed_weights=bool(m.get("closed_weights", True)),
                window=int(m.get("window", 16_000)),
                max_output_tokens=int(m.get("max_output_tokens", MAX_OUTPUT_TOKENS)),
                note=m.get("note", ""),
                rate_in_per_mtok=m.get("rate_in_per_mtok"),
                rate_out_per_mtok=m.get("rate_out_per_mtok"),
            )
            for m in raw.get("models", [])
        ]
        return Panel(
            panel_id=raw.get("panel_id") or "panel-01",
            models=models,
            trials=int(raw.get("trials_per_task", trials)),
            temperature=float(raw.get("temperature", 0.0)),
            source=str(panel_path),
        )

    rows = json.loads(probe_path.read_text(encoding="utf-8"))
    models: list[ModelSpec] = []
    excluded: list[dict[str, str]] = []
    for row in rows:
        candidate = row["candidate"]
        if row["status"] == "ok":
            fam, closed, window, note = CLASSIFICATION.get(candidate, (candidate, True, 16_000, ""))
            provider, _, model_id = candidate.partition(":")
            models.append(
                ModelSpec(
                    provider=provider,
                    model_id=model_id,
                    family=fam,
                    closed_weights=closed,
                    window=window,
                    note=note,
                    extra=dict(REASONING_PARAMS.get(fam, {})),
                )
            )
        else:
            excluded.append({"candidate": candidate, "reason": _reason(row)})

    return Panel(panel_id=f"panel-{PANEL_VERSION}-probe-derived", models=models, trials=trials, excluded=excluded)


def _reason(row: dict[str, Any]) -> str:
    detail = str(row.get("detail", ""))
    http = row.get("http")
    if http == 402:
        return "HTTP 402 insufficient credits"
    if http == 429:
        return "HTTP 429 quota exceeded"
    if http == 404:
        return "HTTP 404 model not available to this account"
    if http == 503:
        return "HTTP 503 service unavailable"
    if "no usable text" in detail:
        return "HTTP 200 with no usable text in content or reasoning"
    return f"HTTP {http} {detail[:80]}"
