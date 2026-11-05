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
    assert card.total <= 100, f"no report can be worth more than the rubric: {card.total}"


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


# ---------------------------------------------------------------------------
# Citation resolution. A live gpt-oss trial cited "Total amount: USD 105,000.00"
# — the correct location quoted with its value — and scored 0/15 on traceability.
# That is a systematic bias against every model, so it is pinned by tests.
# ---------------------------------------------------------------------------
def test_citation_quoted_with_its_value_earns_traceability():
    built = CASES["DOC-002"]
    truth = built.truth
    finding = next(f for f in truth.findings if f.code == "AMOUNT_EXCEEDS_CREDIT")
    report = {
        "case_id": "DOC-002",
        "assessment": "DISCREPANCIES_FOUND",
        "documents_reviewed": built.package.document_ids(),
        "discrepancies": [
            {
                "code": finding.code,
                "field": "invoice_total_amount",
                "severity": finding.severity,
                "observed_values": dict(finding.observed),
                "rule_id": finding.rule_id,
                "evidence": [
                    {"document_id": "INV-001", "page": 1, "location": "Total amount: USD 105,000.00"},
                    {"document_id": "LC-001", "page": 1, "location": "Credit Amount: USD 100,000.00"},
                ],
                "explanation": finding.statement,
                "escalation_required": True,
            }
        ],
        "unresolved_questions": [],
        "summary": "value-quoted citation",
    }
    card = grade(truth, built.package, report, RB)
    evidence = next(d for d in card.dimensions if d.name == "evidence")
    assert evidence.points > 0, "a correct location quoted with its value must be credited"
    assert card.fabricated == []


def test_loosening_citations_did_not_weaken_fabrication_detection():
    """The containment step must still refuse locations that name nothing."""
    built = CASES["DOC-002"]
    for bogus in ("Remarks", "General observations", "Port of discharge"):
        resolved = built.package.index.resolve("INV-001", bogus)
        assert resolved is None, f"{bogus!r} resolved to {resolved!r} on the invoice"


def test_longest_label_wins_so_specific_fields_are_not_absorbed():
    built = CASES["DOC-001"]
    resolved = built.package.index.resolve("LC-001", "Amount Tolerance Condition: NO TOLERANCE")
    assert resolved == "amount_condition", resolved


def test_right_defect_with_weak_citation_earns_recall_not_traceability():
    """Detection and traceability are separate dimensions and must be scored separately.

    A model that finds the partial-shipment breach but cites the quantity line rather than
    the two bill-of-lading numbers has done the harder thing. Counting that as a miss
    understates recall, which is the number this benchmark is most read for.
    """
    built = CASES["DOC-005"]
    gt = next(f for f in built.truth.findings if f.code == "PARTIAL_SHIPMENT_NOT_PERMITTED")
    report = {
        "case_id": "DOC-005",
        "assessment": "DISCREPANCIES_FOUND",
        "documents_reviewed": built.package.document_ids(),
        "discrepancies": [
            {
                "code": gt.code,
                "field": "shipment_split",
                "severity": gt.severity,
                "observed_values": {"bills": "2"},
                "rule_id": gt.rule_id,
                "evidence": [{"document_id": "BL-001", "page": 1, "location": "Quantity Shipped"}],
                "explanation": "Two transport documents presented while partial shipment is prohibited.",
                "escalation_required": True,
            }
        ],
        "unresolved_questions": [],
        "summary": "weak citation",
    }
    card = grade(built.truth, built.package, report, RB)
    assert gt.finding_id in card.matched, "the defect was found but not credited"
    assert card.fabricated == []
    evidence = next(d for d in card.dimensions if d.name == "evidence")
    assert evidence.points == 0.0, "wrong location must still cost the evidence dimension"


def test_shotgun_cannot_collect_recall_through_weak_citations():
    """The tier-3 match requires a resolvable citation, so naming every code with vague
    evidence must not earn detection credit."""
    built = CASES["DOC-002"]
    ids = built.package.document_ids()
    report = {
        "case_id": "DOC-002",
        "assessment": "DISCREPANCIES_FOUND",
        "documents_reviewed": ids,
        "discrepancies": [
            {
                "code": code,
                "field": "everything",
                "severity": "critical",
                "observed_values": {},
                "rule_id": next(iter(RB.code_to_rules.get(code, ["RULE-AMT-001"]))),
                "evidence": [{"document_id": ids[0], "page": 1, "location": "Remarks"}],
                "explanation": "possible",
                "escalation_required": True,
            }
            for code in sorted(RB.codes)
        ],
        "unresolved_questions": [],
        "summary": "shotgun",
    }
    card = grade(built.truth, built.package, report, RB)
    assert card.passed is False
    assert card.safety["unsupported_discrepancy_rate"] > 0.9


def test_repeating_one_unknown_earns_one_credit_not_three():
    """Epistemic honesty is counted per unknown, not per reported line.

    A live gpt-oss-20b trial on DOC-003 asked the same unresolvable quantity question three
    times, each time pairing a different pair of documents. Counted per line, three credits
    against a single unknown bought 30 points from a 10-point dimension and the trial scored
    102.5 — a mark the rubric cannot express, and free credit for padding.
    """
    built = CASES["DOC-003"]
    report = reference_output(built.truth, built.package, RB)
    open_items = report["unresolved_questions"]
    assert open_items, "DOC-003 must leave at least one question genuinely open"
    report["unresolved_questions"] = [dict(item) for item in open_items] * 3

    card = grade(built.truth, built.package, report, RB)
    uncertainty = next(d for d in card.dimensions if d.name == "uncertainty")
    assert card.spurious_unresolved == [], "a repeated true unknown is not noise"
    assert uncertainty.ratio == 1.0, f"three lines for one unknown scored {uncertainty.ratio}: {uncertainty.detail}"
    assert uncertainty.points == uncertainty.weight, "a dimension cannot pay more than its weight"
    assert card.total <= 100, f"padding the same question raised the total to {card.total}"
