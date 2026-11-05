"""Aggregation: journal records into the results table the guide asks for.

Two reporting choices are deliberate:

1. **Failed and skipped trials stay visible.** A table that quietly drops rows where the
   provider returned 429 makes the remaining numbers look like a complete matrix. Every
   model reports how many trials it actually has, and any shortfall is called out.

2. **Capability ordering is checked, not assumed.** The guide (p.11) says if a smaller model
   beats a frontier model, look for ambiguity or grader problems before claiming a finding.
   So inversions are computed and surfaced as a warning against the specific task, which
   turns that advice into something a reviewer can see rather than a promise.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import mean, pstdev
from typing import Any

from benchmark.harness.journal import Journal

DIMENSIONS = ("recall", "precision", "rule_mapping", "evidence", "severity", "uncertainty", "format")

#: Rough capability order for the inversion check. Only used to raise a flag for
#: investigation; it is not a benchmark result and is not reported as one.
CAPABILITY_RANK = {
    "groq:openai/gpt-oss-120b": 5,
    "groq:qwen/qwen3.8-27b": 4,
    "groq:openai/gpt-oss-20b": 3,
    "groq:qwen/qwen3.6-27b": 3,
    "gemini:models/gemini-3.5-flash-lite": 2,
    "gemini:models/gemini-flash-lite-latest": 2,
    "groq:allam-2-7b": 1,
}


def _scores(rec: dict[str, Any]) -> dict[str, float]:
    card = rec.get("scorecard") or {}
    return {d["name"]: float(d["points"]) for d in card.get("dimensions", [])}


def _ratios(rec: dict[str, Any]) -> dict[str, float]:
    card = rec.get("scorecard") or {}
    return {d["name"]: float(d["ratio"]) for d in card.get("dimensions", [])}


def panel_wide(journal: Journal) -> dict[str, Any]:
    """Headline numbers for the whole panel, computed from the journal.

    The README quotes a pass rate, a per-dimension credit table and a missed-code ranking.
    Those used to be transcribed by hand, which makes them exactly the kind of number that can
    drift from the data it came from. They are derived here instead, so `--regrade` regenerates
    every figure the README asserts.
    """
    from collections import Counter

    ok = [r for r in journal.records() if r.get("status") == "ok" and r.get("scorecard")]
    passed = [r for r in ok if r["scorecard"].get("passed")]
    credit = {d: round(100.0 * mean([_ratios(r).get(d, 0.0) for r in ok]), 1) for d in DIMENSIONS} if ok else {}
    missed: Counter[str] = Counter()
    for r in ok:
        missed.update(r["scorecard"].get("safety_metrics", {}).get("missed_codes", []))
    return {
        "trials_scored": len(ok),
        "trials_passed": len(passed),
        "pass_rate_pct": round(100.0 * len(passed) / len(ok), 1) if ok else None,
        "mean_total": round(mean([float(r["scorecard"]["total"]) for r in ok]), 2) if ok else None,
        "dimension_credit_pct": [[d, v] for d, v in sorted(credit.items(), key=lambda kv: kv[1])],
        # Pairs, not a dict: results.json is serialised with sort_keys=True, which would
        # silently turn a ranked counter into an alphabetical one.
        "missed_code_counts": [[c, n] for c, n in missed.most_common()],
        "cap_counts": [[c, n] for c, n in Counter(
            cap for r in ok for cap in r["scorecard"].get("caps", [])).most_common()],
    }


def aggregate(journal: Journal, panel_models: list[str]) -> dict[str, Any]:
    by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in journal.records():
        by_model[f"{rec['provider']}:{rec['model_id']}"].append(rec)

    models_out: dict[str, Any] = {}
    warnings: list[str] = []

    for spec_id in panel_models:
        recs = by_model.get(spec_id, [])
        ok = [r for r in recs if r.get("status") == "ok"]
        statuses = defaultdict(int)
        for r in recs:
            statuses[r.get("status", "?")] += 1

        per_task: dict[str, Any] = {}
        for case_id in sorted({r["case_id"] for r in ok}):
            trials = [r for r in ok if r["case_id"] == case_id]
            totals = [float((r.get("scorecard") or {}).get("total", 0.0)) for r in trials]
            passed = [bool((r.get("scorecard") or {}).get("passed")) for r in trials]
            caps = sorted({c for r in trials for c in (r.get("scorecard") or {}).get("caps", [])})
            dims = {d: mean([_scores(r).get(d, 0.0) for r in trials]) for d in DIMENSIONS} if trials else {}
            per_task[case_id] = {
                "trials": len(trials),
                "mean_total": round(mean(totals), 2) if totals else None,
                "spread": round(pstdev(totals), 2) if len(totals) > 1 else 0.0,
                "pass_at_k": any(passed),
                "pass_hat_k": all(passed) and bool(passed),
                "pass_rate": round(sum(passed) / len(passed), 4) if passed else None,
                "dimension_means": {k: round(v, 2) for k, v in dims.items()},
                "caps_observed": caps,
            }

        all_totals = [t["mean_total"] for t in per_task.values() if t["mean_total"] is not None]
        models_out[spec_id] = {
            "trials_recorded": len(recs),
            "trials_scored": len(ok),
            "status_counts": dict(statuses),
            "tasks_covered": len(per_task),
            "overall_mean_total": round(mean(all_totals), 2) if all_totals else None,
            "tasks_passed_hat_k": sum(1 for t in per_task.values() if t["pass_hat_k"]),
            "tasks_passed_at_k": sum(1 for t in per_task.values() if t["pass_at_k"]),
            "critical_false_clearances": sum(
                1
                for r in ok
                if "CRITICAL_FALSE_CLEARANCE" in (r.get("scorecard") or {}).get("caps", [])
            ),
            "fabricated_on_clean": sum(
                1 for r in ok if "FABRICATED_ON_CLEAN_PRESENTATION" in (r.get("scorecard") or {}).get("caps", [])
            ),
            "mean_prompt_tokens": round(mean([r.get("prompt_tokens_reported") or 0 for r in ok]), 1) if ok else None,
            "mean_completion_tokens": round(mean([r.get("completion_tokens_reported") or 0 for r in ok]), 1) if ok else None,
            "mean_latency_s": round(mean([r.get("latency_s") or 0 for r in ok]), 2) if ok else None,
            "per_task": per_task,
        }

        if len(recs) != len(ok):
            warnings.append(
                f"{spec_id}: {len(recs) - len(ok)} trial(s) did not score "
                f"({dict(statuses)}) — coverage is incomplete, not zero-performance"
            )

    # Capability ordering check per task. Rows are sorted ascending by assumed capability, so
    # an inversion is the *weaker* model outscoring the stronger one. The first version of
    # this compared the pair the wrong way round and reported every normal result as an
    # anomaly, which would have filled the README with invented warnings.
    for case_id in sorted({t for m in models_out.values() for t in m["per_task"]}):
        rows = [
            (CAPABILITY_RANK.get(spec, 0), float(m["per_task"][case_id]["mean_total"] or 0), spec)
            for spec, m in models_out.items()
            if case_id in m["per_task"] and m["per_task"][case_id]["mean_total"] is not None
        ]
        rows.sort(key=lambda x: x[0])
        for (rank_lo, score_lo, spec_lo), (rank_hi, score_hi, spec_hi) in zip(rows, rows[1:]):
            if rank_lo != rank_hi and score_lo > score_hi + 10:
                warnings.append(
                    f"{case_id}: weaker-ranked {spec_lo} outscored stronger-ranked {spec_hi} "
                    f"by {score_lo - score_hi:.1f} points. Guide p.11 says check task ambiguity "
                    "and grader behaviour before treating this as a finding."
                )

    return {"models": models_out, "warnings": warnings, "panel_wide": panel_wide(journal)}


def to_markdown(result: dict[str, Any], panel: dict[str, Any]) -> str:
    lines = [
        "# Results",
        "",
        f"Panel `{panel.get('panel_id')}` · {panel.get('trials_per_task')} trials per task · "
        f"temperature {panel.get('temperature')}",
        "",
        "| Model | Scored trials | Tasks covered | Mean score | pass@k tasks | pass^k tasks | Critical false clearances | Mean prompt tok | Mean latency |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    def show(v: Any, suffix: str = "") -> str:
        return f"{v}{suffix}" if v is not None else "—"

    for spec, m in result["models"].items():
        covered = show(m["tasks_covered"]) if m["trials_scored"] else "0 (no scored trials)"
        lines.append(
            f"| `{spec}` | {m['trials_scored']} | {covered} | {show(m['overall_mean_total'])} | "
            f"{show(m['tasks_passed_at_k'])} | {show(m['tasks_passed_hat_k'])} | "
            f"{show(m['critical_false_clearances'])} | {show(m['mean_prompt_tokens'])} | "
            f"{show(m['mean_latency_s'], 's')} |"
        )

    pw = result.get("panel_wide", {})
    if pw:
        lines += [
            "",
            f"## Panel-wide: {pw['trials_scored']} scored trials, {pw['trials_passed']} passed "
            f"({pw['pass_rate_pct']}%), mean {pw['mean_total']}/100",
            "",
            "| Dimension | Mean credit |",
            "|---|---|",
        ]
        lines += [f"| {d} | {v}% |" for d, v in pw["dimension_credit_pct"]]
        lines += ["", "| Most-missed code | Trials |", "|---|---|"]
        lines += [f"| `{c}` | {n} |" for c, n in pw["missed_code_counts"][:8]]
        lines += ["", "| Cap fired | Trials |", "|---|---|"]
        lines += [f"| `{c}` | {n} |" for c, n in pw["cap_counts"]]

    lines += ["", "## Per task", ""]
    for spec, m in result["models"].items():
        lines.append(f"### `{spec}`")
        lines.append("")
        lines.append("| Task | Trials | Mean | Spread | pass@k | pass^k | caps seen |")
        lines.append("|---|---|---|---|---|---|---|")
        for case, t in m["per_task"].items():
            lines.append(
                f"| {case} | {t['trials']} | {t['mean_total']} | {t['spread']} | "
                f"{'yes' if t['pass_at_k'] else 'no'} | {'yes' if t['pass_hat_k'] else 'no'} | "
                f"{', '.join(t['caps_observed']) or '—'} |"
            )
        lines.append("")

    if result["warnings"]:
        lines += ["## Warnings and coverage gaps", ""]
        lines += [f"- {w}" for w in result["warnings"]]
        lines.append("")

    excluded = panel.get("excluded_after_probing", [])
    lines += [
        "## Excluded after probing (never silently absent)",
        "",
        *([f"- `{e['candidate']}` — {e['reason']}" for e in excluded] or ["- none"]),
        "",
    ]
    return "\n".join(lines)
