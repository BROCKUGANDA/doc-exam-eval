#!/usr/bin/env python3
"""DOC-EXAM harness entry point.

Everything here runs with no API key and no database. That is deliberate: the Participant
Guide grades Reproducibility on a judge reaching your main results from a clean environment
using the README, so the verification path cannot depend on a service a judge does not have.

    python run_eval.py --validate        rulebook/engine/grader proof (no key needed)
    python run_eval.py --write-tasks     materialise task/, reference/, transcripts layout
    python run_eval.py --review-sheet    write docs/expert-review.md for the examiner sign-off
    python run_eval.py --discover        ask each configured provider what its key can reach
    python run_eval.py --dry-run         token, cost and wall-clock estimate for a panel
    python run_eval.py --live            Phase B: run models (requires keys)

--live is intentionally not implemented in this build. It fails loudly rather than
simulating results, because fabricated trial data would invalidate every claim in the
submission.
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

from benchmark.generator.build import build_case
from benchmark.generator.scenarios import SCENARIOS
from benchmark.graders.scoring import grade
from benchmark.harness.context import budget
from benchmark.harness.providers import available_providers, discover, provider
from benchmark.paths import MODELS_LOCK, REPO_ROOT, ensure_dirs
from benchmark.rulebook import rulebook
from benchmark.tasks import prompt_for, write_tasks
from benchmark.validation.fixtures import build_fixtures, check, reference_output, reference_total
from benchmark.validation.lint_tasks import lint, suite_report

RB = rulebook()
CASES = {cid: build_case(sc, RB) for cid, sc in SCENARIOS.items()}


def _cases_for_tasks():
    return {cid: (built.package, built.truth) for cid, built in CASES.items()}


def cmd_validate(verbose: bool = False) -> int:
    """The gate. Fails if the engine disagrees with intent, a reference does not pass, a
    wrong answer is accepted, or a rule is graded but never exercised."""
    failures: list[str] = []

    for cid in sorted(CASES):
        built = CASES[cid]
        if not built.intent_ok:
            failures += [f"{cid}/intent: {m}" for m in built.intent_mismatches]

        for problem in lint(SCENARIOS[cid], built.package, built.truth, RB):
            failures.append(f"{cid}/lint: {problem}")

        ref_card = grade(built.truth, built.package, reference_output(built.truth, built.package, RB), RB)
        if not ref_card.passed:
            failures.append(f"{cid}/reference: score {ref_card.total:.1f} caps {ref_card.caps} dims {[(d.name, d.points) for d in ref_card.dimensions]}")

        ref_total = reference_total(built.truth, built.package, RB)
        for fixture in build_fixtures(built.truth, built.package, RB):
            for problem in check(fixture, built.truth, built.package, RB, ref_total):
                failures.append(f"{cid}/{fixture.name}: {problem}")

    report = suite_report(_cases_for_tasks(), RB)
    if report["kinds_without_evaluator"]:
        failures.append(f"rule kinds with no evaluator: {report['kinds_without_evaluator']}")
    if report["rules_never_exercised"]:
        failures.append(f"rules declared but never exercised by any task: {report['rules_never_exercised']}")

    fixtures = {cid: build_fixtures(b, p, RB) for cid, (p, b) in _cases_for_tasks().items()}
    print(json.dumps({"rulebook": RB.version, "rulebook_fingerprint": RB.fingerprint(), **report}, indent=2))
    print(f"fixture corpus size: {sum(len(v) for v in fixtures.values())}")

    if failures:
        print(f"\nFAILED {len(failures)} check(s):", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print(
        f"\nPASS  tasks={len(CASES)}  fixtures={sum(len(v) for v in fixtures.values())}  "
        f"rules_exercised={report['rules_exercised']}/{report['producer_rules']}"
    )
    return 0


def cmd_write_tasks() -> int:
    ensure_dirs()
    written = write_tasks(_cases_for_tasks(), SCENARIOS, RB)
    print(f"wrote {len(written)} task folders under {REPO_ROOT / 'benchmark' / 'tasks'}")
    for path in written:
        prompt = (path / "instruction.md").read_text(encoding="utf-8")
        b = budget(prompt, window=131_072)
        print(f"  {path.name}: prompt ~{b.prompt_tokens} tokens (estimated with o200k_base)")
    return 0


def cmd_review_sheet() -> int:
    from benchmark.reporting import write_expert_review

    out = write_expert_review(_cases_for_tasks(), SCENARIOS, RB, REPO_ROOT / "docs" / "expert-review.md")
    print(f"wrote {out}")
    return 0


def cmd_discover() -> int:
    report = discover()
    ensure_dirs()
    MODELS_LOCK.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"\npinned to {MODELS_LOCK}")
    configured = [p.name for p in available_providers() if p.configured]
    if not configured:
        print("No provider keys found in the environment. Copy .env.example to .env and add one.")
    return 0


def cmd_dry_run(models: list[str], trials: int) -> int:
    """Token and cost arithmetic before any money is spent. Costs are listed-price
    estimates at the rates passed in, and are labelled as estimates — never billed."""
    if not models:
        print("--dry-run needs --model NAME[,NAME...]")
        return 2
    rows = []
    for cid in sorted(CASES):
        built = CASES[cid]
        prompt = prompt_for(SCENARIOS[cid], built.package, RB)
        b = budget(prompt, window=131_072)
        rows.append({"case_id": cid, "prompt_tokens": b.prompt_tokens, "findings": len(built.truth.findings)})
    total_prompt = sum(r["prompt_tokens"] for r in rows)
    trials_total = len(CASES) * trials * len(models)
    est_output = 1400
    print(json.dumps({
        "per_case": rows,
        "trials_total": trials_total,
        "input_tokens_total": total_prompt * trials * len(models),
        "output_tokens_assumed_per_trial": est_output,
        "output_tokens_total": est_output * trials_total,
        "cost_note": "Free-tier providers bill nothing; report actual billed and list-price estimated separately in results.",
    }, indent=2))
    return 0


def cmd_live() -> int:
    print(
        "Live model trials are not implemented in this build.\n"
        "It would be possible to fabricate a results table here. That is why it is refused:\n"
        "the submission's claims must be backed by transcripts that exist (Guide p.20, rule 7).\n"
        "Use --discover to pin model ids, then --validate to prove the grader.",
        file=sys.stderr,
    )
    return 3


#: Providers the probe may address. Kept explicit so a typo in --model is reported rather
#: than silently skipped.
PROVIDER_NAMES = ("groq", "gemini", "openrouter", "ollama_local")

#: Every id here was read out of benchmark/results/models.lock.json, which --discover wrote
#: from the providers themselves. Nothing in this list is recalled from documentation or
#: invented, because an invented model id only fails at the provider -- the worst possible
#: place to discover it.
DEFAULT_PROBE = [
    "openrouter:anthropic/claude-haiku-4.5",
    "openrouter:anthropic/claude-fable-5.1",
    "openrouter:openai/gpt-4.1-mini",
    "openrouter:deepseek/deepseek-v3.2",
    "openrouter:meta-llama/llama-4-scout",
    "gemini:models/gemini-2.5-flash",
    "gemini:models/gemini-2.5-pro",
    "gemini:models/gemini-3.1-pro-preview",
    "groq:openai/gpt-oss-120b",
    "groq:openai/gpt-oss-20b",
    "groq:qwen/qwen3.8-27b",
]


def cmd_probe(models: list[str]) -> int:
    """One tiny real request per candidate model.

    Listing a model id proves the key can see it. Only a completed request proves the key can
    *use* it within whatever quota applies, and quota is exactly what decides the panel. So
    this is run before any experiment is designed, and its output is what the README's model
    table is allowed to be built from.
    """
    from benchmark.harness.client import ProviderError, complete
    from benchmark.harness.providers import provider

    candidates = models or DEFAULT_PROBE
    if not candidates:
        print("--probe needs --model provider:model or a default list")
        return 2

    probe_prompt = (
        'Reply with exactly this JSON and nothing else: {"ok": true, "n": 2}'
    )
    rows = []
    for spec in candidates:
        if ":" not in spec:
            print(f"skip malformed candidate {spec!r} (expected provider:model)")
            continue
        pname, model = spec.split(":", 1)
        if pname not in PROVIDER_NAMES:
            print(f"skip unknown provider {pname!r}")
            continue
        p = provider(pname)
        if not p.configured:
            rows.append({"candidate": spec, "status": "no_key"})
            continue
        try:
            c = complete(p, model, probe_prompt, temperature=0.0, max_output_tokens=64)
            rows.append({"candidate": spec, "status": "ok", **c.to_dict(), "text": c.text[:80]})
        except ProviderError as exc:
            rows.append({"candidate": spec, "status": "error", "http": exc.status, "detail": str(exc)[:200]})
        except Exception as exc:  # noqa: BLE001 - a probe failure is data, not a crash
            rows.append({"candidate": spec, "status": "error", "detail": f"{type(exc).__name__}: {exc}"[:200]})

    print(json.dumps(rows, indent=2))
    ok = [r for r in rows if r["status"] == "ok"]
    print(f"\n{len(ok)}/{len(rows)} candidates callable")
    ensure_dirs()
    (MODELS_LOCK.parent / "probe.json").write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"written to {MODELS_LOCK.parent / 'probe.json'}")
    return 0 if ok else 1


def cmd_live(models: list[str], trials: int | None, tasks: list[str]) -> int:
    """Run the panel for real.

    Refuses rather than fabricates when there is nothing callable, and prints a plan before
    spending quota so the cost is a decision rather than a surprise.
    """
    from benchmark.harness.journal import Journal
    from benchmark.harness.panel import ModelSpec, from_probe
    from benchmark.harness.report import aggregate, to_markdown
    from benchmark.harness.runner import panel_totals, run_panel
    from benchmark.paths import PROBE_FILE, RESULTS_DIR

    ensure_dirs()
    if not PROBE_FILE.is_file():
        print("No probe results. Run 'python run_eval.py --discover' then '--probe' first:\n"
              "the panel is built from models that actually answered, not from a remembered list.",
              file=sys.stderr)
        return 2

    panel = from_probe(PROBE_FILE, trials=trials or 3)
    if models:
        wanted = set(models)
        panel.models = [m for m in panel.models if m.spec_id in wanted]
        unknown = wanted - {m.spec_id for m in panel.models}
        if unknown:
            print(f"not in the callable panel (see probe.json): {sorted(unknown)}", file=sys.stderr)
    if not panel.models:
        print("Panel is empty after filtering — nothing callable to run.", file=sys.stderr)
        return 2

    cases = _cases_for_tasks()
    targets = tasks or sorted(cases)
    missing = [t for t in targets if t not in cases]
    if missing:
        print(f"unknown task(s): {missing}", file=sys.stderr)
        return 2

    totals = panel_totals(panel, len(targets))
    est_tokens = totals["planned_requests"] * 5200
    print(f"panel {panel.panel_id}: {totals['models']} models x {totals['tasks']} tasks "
          f"x {totals['trials_per_task']} trials = {totals['planned_requests']} requests")
    print(f"~{est_tokens:,} input tokens at ~5.2k per prompt; excluded after probing: "
          f"{len(panel.excluded)}")

    journal = Journal(RESULTS_DIR / "runs" / f"{panel.panel_id}.jsonl")
    done = journal.completed()
    if done:
        print(f"resuming: {len(done)} trial(s) already recorded and will not be re-spent")

    def progress(t) -> None:
        if t.status == "ok":
            card = t.scorecard or {}
            print(f"  {t.case_id} {t.provider}:{t.model_id} #{t.trial} -> "
                  f"{card.get('total')} {'PASS' if card.get('passed') else 'fail'} "
                  f"{t.latency_s}s caps={card.get('caps')}")
        else:
            print(f"  {t.case_id} {t.provider}:{t.model_id} #{t.trial} -> {t.status}: {t.error[:110]}")

    written = run_panel(cases, SCENARIOS, RB, panel, journal, only=targets, on_trial=progress)
    print(f"\n{len(written)} trial(s) this invocation")

    result = aggregate(journal, [m.spec_id for m in panel.models])
    (RESULTS_DIR / "results.json").write_text(
        json.dumps({"panel": panel.to_dict(), "totals": totals, **result}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    (RESULTS_DIR / "results.md").write_text(to_markdown(result, panel.to_dict()), encoding="utf-8", newline="\n")
    print(f"wrote {RESULTS_DIR / 'results.md'} and results.json")
    if result["warnings"]:
        print(f"{len(result['warnings'])} coverage/ordering warning(s) recorded")
    return 0


def cmd_regrade() -> int:
    """Re-score stored transcripts with the current grader. No network, no quota."""
    from benchmark.harness.journal import Journal
    from benchmark.harness.report import aggregate, to_markdown
    from benchmark.harness.runner import regrade
    from benchmark.paths import RESULTS_DIR

    runs = sorted((RESULTS_DIR / "runs").glob("*.jsonl")) if (RESULTS_DIR / "runs").is_dir() else []
    if not runs:
        print("no journal yet; run --live first")
        return 2
    for path in runs:
        journal = Journal(path)
        counts = regrade(journal, _cases_for_tasks(), RB)
        panel_ids = {r.get("panel_id") for r in journal.records()}
        model_ids = sorted({f"{r['provider']}:{r['model_id']}" for r in journal.records()})
        result = aggregate(journal, model_ids)
        panel_meta = {"panel_id": ",".join(sorted(x for x in panel_ids if x)), "trials_per_task": "regraded",
                      "temperature": 0.0, "excluded_after_probing": []}
        (RESULTS_DIR / "results.json").write_text(
            json.dumps({"panel": panel_meta, "totals": counts, **result}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n")
        (RESULTS_DIR / "results.md").write_text(
            to_markdown(result, panel_meta), encoding="utf-8", newline="\n")
        print(f"{path.name}: {counts}")
    return 0


def cmd_report() -> int:
    from benchmark.harness.report import aggregate, to_markdown
    from benchmark.paths import PROBE_FILE, RESULTS_DIR

    if not RESULTS_DIR.joinpath("results.json").is_file():
        print("no results yet; run --live first")
        return 2
    blob = json.loads(RESULTS_DIR.joinpath("results.json").read_text(encoding="utf-8"))
    print(json.dumps({"totals": blob["totals"], "warnings": blob["warnings"]}, indent=2))
    for spec, m in blob["models"].items():
        print(f"{spec:46} scored={m['trials_scored']:>3} mean={m['overall_mean_total']} "
              f"pass^k tasks={m['tasks_passed_hat_k']}/{m['tasks_covered']} "
              f"criticalFC={m['critical_false_clearances']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="DOC-EXAM benchmark harness")
    ap.add_argument("--validate", action="store_true", help="prove engine, tasks and graders (no keys needed)")
    ap.add_argument("--offline", action="store_true", help="validate and write the task/reference layout")
    ap.add_argument("--write-tasks", action="store_true")
    ap.add_argument("--review-sheet", action="store_true")
    ap.add_argument("--discover", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--live", action="store_true", help="run the panel against real providers")
    ap.add_argument("--report", action="store_true", help="print the aggregated results table")
    ap.add_argument("--regrade", action="store_true", help="re-score stored transcripts with the current grader (no network)")
    ap.add_argument("--task", action="append", default=[], help="restrict to a task id, repeatable")
    ap.add_argument("--probe", action="store_true", help="send one real request per candidate model")
    ap.add_argument("--model", action="append", default=[], help="model id, repeatable or comma-separated")
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--list-rules", action="store_true")
    args = ap.parse_args(argv)

    if args.list_rules:
        for r in RB.rules:
            print(f"{r.id}  {r.kind:34} {r.severity:10} {','.join(r.codes)}")
        return 0

    if args.validate or args.offline:
        rc = cmd_validate()
        return rc if rc != 0 or not args.offline else cmd_write_tasks()
    if args.write_tasks:
        return cmd_write_tasks()
    if args.review_sheet:
        return cmd_review_sheet()
    if args.discover:
        return cmd_discover()
    if args.dry_run:
        models = [m.strip() for entry in args.model for m in entry.split(",") if m.strip()]
        return cmd_dry_run(models, args.trials)
    if args.probe:
        return cmd_probe([m.strip() for m in args.model if m.strip()])
    if args.regrade:
        return cmd_regrade()
    if args.report:
        return cmd_report()
    if args.live:
        return cmd_live([m.strip() for entry in args.model for m in entry.split(",") if m.strip()],
                        args.trials, args.task)

    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
