"""Grader reliability: every task's reference solution must pass, and every
deliberately wrong answer must be rejected for the right reason.

This is the 20-point criterion, so it is exercised across all scenarios rather than on
one hand-picked example.
"""

from __future__ import annotations

import pytest

from benchmark.generator.build import build_case
from benchmark.generator.scenarios import SCENARIOS
from benchmark.graders.scoring import grade
from benchmark.rulebook import rulebook
from benchmark.validation.fixtures import build_fixtures, check, reference_output, reference_total

RB = rulebook()
CASES = {cid: build_case(sc, RB) for cid, sc in SCENARIOS.items()}
IDS = sorted(CASES)


@pytest.mark.parametrize("case_id", IDS)
def test_reference_solution_passes(case_id):
    built = CASES[case_id]
    card = grade(built.truth, built.package, reference_output(built.truth, built.package, RB), RB)
    assert card.caps == [], f"reference must not trip a cap: {card.caps}"
    assert card.passed, f"reference must pass, got {card.total}: {[d.detail for d in card.dimensions]}"
    assert card.total >= 95, f"reference should score near-full marks, got {card.total}"


@pytest.mark.parametrize("case_id", IDS)
def test_computed_truth_matches_author_intent(case_id):
    assert CASES[case_id].intent_ok, CASES[case_id].intent_mismatches


@pytest.mark.parametrize("case_id", IDS)
def test_grader_rejects_wrong_answers(case_id):
    built = CASES[case_id]
    ref_total = reference_total(built.truth, built.package, RB)
    failures = []
    for fixture in build_fixtures(built.truth, built.package, RB):
        problems = check(fixture, built.truth, built.package, RB, ref_total)
        if problems:
            failures.append(f"{fixture.name}: " + "; ".join(problems))
    assert not failures, "grader did not behave as specified:\n" + "\n".join(failures)


@pytest.mark.parametrize("case_id", IDS)
def test_fixtures_cover_the_major_levers(case_id):
    """A corpus that silently shrinks stops proving anything. The count is asserted so
    adding a task cannot quietly reduce coverage."""
    built = CASES[case_id]
    names = {f.name for f in build_fixtures(built.truth, built.package, RB)}
    core = {"reference_solution", "alternative_valid_representation", "malformed_json",
            "missing_required_key", "shotgun_every_code", "blanket_escalation"}
    assert core <= names, f"missing levers: {core - names}"
    assert len(names) >= 6


def test_grade_is_deterministic():
    built = CASES["DOC-002"]
    out = reference_output(built.truth, built.package, RB)
    totals = [grade(built.truth, built.package, out, RB).total for _ in range(3)]
    assert len(set(totals)) == 1, f"same input must grade identically, got {totals}"


def test_untraceable_claim_is_not_credited():
    """A finding with no evidence at all cannot match, so it counts as unsupported
    rather than as a lucky guess."""
    built = CASES["DOC-002"]
    wrong = reference_output(built.truth, built.package, RB)
    wrong["discrepancies"] = [
        {
            "code": "CURRENCY_MISMATCH",
            "field": "whatever",
            "severity": "critical",
            "observed_values": {},
            "rule_id": "RULE-AMT-003",
            "evidence": [],
            "explanation": "no citation",
            "escalation_required": False,
        }
    ]
    card = grade(built.truth, built.package, wrong, RB)
    assert card.matched == []
    assert card.safety["unsupported_discrepancy_rate"] == 1.0
