"""Task packaging, prompt hygiene, and the pinned coverage gaps.

Two jobs here. First, prove the model-visible prompt cannot contain the answer. Second,
pin the rules and codes the suite does *not* exercise to an exact list: a gap that is
written down is a disclosed limitation, while a gap that grows silently is a false claim
about coverage.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmark.generator.build import build_case
from benchmark.generator.scenarios import SCENARIOS
from benchmark.rulebook import rulebook
from benchmark.tasks import BRIEFS, prompt_for, write_tasks
from benchmark.validation.lint_tasks import lint, suite_report

RB = rulebook()
CASES = {cid: build_case(sc, RB) for cid, sc in SCENARIOS.items()}
IDS = sorted(CASES)

#: Documented limitations. If this list grows, either add a task that exercises the new
#: gap or delete the rule — do not extend the list without deciding which is true.
KNOWN_UNEXERCISED_CODES = {
    "DOCUMENT_DATED_AFTER_PRESENTATION",
    "INSPECTION_DATED_AFTER_SHIPMENT",
    "QUANTITY_TOLERANCE_EXCEEDED",
}


def _pairs():
    return {cid: (built.package, built.truth) for cid, built in CASES.items()}


def test_every_task_lints_clean():
    problems = []
    for cid in IDS:
        built = CASES[cid]
        problems += [f"{cid}: {p}" for p in lint(SCENARIOS[cid], built.package, built.truth, RB)]
    assert not problems, "\n".join(problems)


def test_prompt_never_contains_the_answer():
    for cid in IDS:
        built = CASES[cid]
        prompt = prompt_for(SCENARIOS[cid], built.package, RB)
        truth_blob = json.dumps(built.truth.to_dict(), sort_keys=True)

        # The reference is a separate artefact; nothing in it may be reachable from the prompt.
        for path in ("solution/reference.json", "ground_truth", "reference.json"):
            assert path not in prompt, f"{cid}: prompt references {path}"
        for f in built.truth.findings:
            assert f.finding_id not in prompt, f"{cid}: prompt leaks finding id {f.finding_id}"
        assert "GT-" not in prompt, f"{cid}: prompt leaks computed finding identifiers"
        assert truth_blob[:200] not in prompt

        # Author-only commentary stays out of the model's view.
        if SCENARIOS[cid].note:
            assert SCENARIOS[cid].note.strip() not in prompt, f"{cid}: author note leaked into prompt"


def test_prompt_states_everything_that_is_graded():
    for cid in IDS:
        built = CASES[cid]
        prompt = prompt_for(SCENARIOS[cid], built.package, RB)
        assert RB.markdown() in prompt, f"{cid}: rulebook missing from prompt"
        assert built.package.text_block().strip() in prompt, f"{cid}: documents missing from prompt"
        for code in {f.code for f in built.truth.findings}:
            assert f"- {code}" in prompt, f"{cid}: graded code {code} was never offered to the model"
        for rule_id in {f.rule_id for f in built.truth.findings}:
            assert rule_id in prompt, f"{cid}: graded rule {rule_id} absent from the supplied rulebook"


def test_coverage_gaps_are_exactly_the_documented_list():
    report = suite_report(_pairs(), RB)
    assert set(report["codes_never_exercised"]) == KNOWN_UNEXERCISED_CODES, (
        "coverage changed: if a rule was added or a defect stopped being planted, either "
        "exercise it in a task or update this list deliberately"
    )
    assert report["rules_never_exercised"] == []
    assert report["kinds_without_evaluator"] == []
    assert report["evaluators_for_undeclared_kinds"] == []


def test_suite_has_headroom_and_spread():
    """Guide p.11: an eval where everything scores 0 or everything scores 100 shows nothing.
    Checked structurally here, against the reference answers, before any model runs."""
    report = suite_report(_pairs(), RB)
    assert report["total_ground_truth_findings"] >= 12
    assert report["clean_tasks"] >= 1, "at least one task must test restraint"
    severities = [f.severity for _, truth in _pairs().values() for f in truth.findings]
    assert "minor" in severities and "critical" in severities, "severity must be discriminating"
    assert sum(1 for _, truth in _pairs().values() if truth.unresolved) >= 2, (
        "uncertainty escalation is barely measurable without several unestablishable fields"
    )


def test_truth_is_reproducible_from_seeds():
    for cid in IDS:
        again = build_case(SCENARIOS[cid], RB)
        assert again.truth.to_dict() == CASES[cid].truth.to_dict(), f"{cid}: truth is not deterministic"
        assert again.package.to_dict() == CASES[cid].package.to_dict(), f"{cid}: package is not deterministic"


def test_write_tasks_separates_prompt_from_reference(tmp_path: Path):
    written = write_tasks(_pairs(), SCENARIOS, RB, out_root=tmp_path)
    assert len(written) == len(IDS)
    for case_dir in written:
        assert (case_dir / "instruction.md").is_file()
        assert (case_dir / "task.toml").is_file()
        assert (case_dir / "environment" / "documents.json").is_file()
        assert (case_dir / "solution" / "reference.json").is_file()
        assert (case_dir / "tests" / "grader_config.json").is_file()
        instruction = (case_dir / "instruction.md").read_text(encoding="utf-8")
        assert "GT-" not in instruction
        assert "acceptable_assessments" not in instruction


def test_every_task_has_a_brief_and_no_brief_is_empty():
    assert set(BRIEFS) == set(SCENARIOS)
    for case_id, brief in BRIEFS.items():
        assert len(brief) > 60, f"{case_id}: brief too thin to scope an examination"


@pytest.mark.parametrize("case_id", IDS)
def test_each_task_has_at_least_one_reference_passing_grader(case_id):
    from benchmark.graders.scoring import grade
    from benchmark.validation.fixtures import reference_output

    built = CASES[case_id]
    card = grade(built.truth, built.package, reference_output(built.truth, built.package, RB), RB)
    assert card.passed and not card.caps
