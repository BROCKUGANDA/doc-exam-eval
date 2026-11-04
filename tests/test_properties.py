"""Grader invariants, checked with generated inputs rather than hand-picked ones.

These are the properties that must hold for *any* report, not just the fixtures: a score
never escapes its bounds, the order of findings never changes the verdict, and adding
unsupported claims never raises the score. If any of these were violated, a headline
result could be an artifact of dict ordering or luck rather than performance.
"""

from __future__ import annotations

import copy
import random

from hypothesis import HealthCheck, given, settings, strategies as st

from benchmark.generator.build import build_case
from benchmark.generator.scenarios import SCENARIOS
from benchmark.graders.scoring import grade
from benchmark.rulebook import rulebook
from benchmark.validation.fixtures import _fabricated, reference_output

RB = rulebook()
CASES = {cid: build_case(sc, RB) for cid, sc in SCENARIOS.items()}
IDS = sorted(CASES)


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(permutation_seed=st.integers(0, 500))
def test_order_of_findings_never_changes_the_score(permutation_seed):
    for case_id in IDS:
        built = CASES[case_id]
        base = reference_output(built.truth, built.package, RB)
        shuffled = copy.deepcopy(base)
        random.Random(permutation_seed).shuffle(shuffled["discrepancies"])
        shuffled["unresolved_questions"] = list(reversed(shuffled["unresolved_questions"]))
        a = grade(built.truth, built.package, base, RB)
        b = grade(built.truth, built.package, shuffled, RB)
        assert a.total == b.total, f"{case_id}: ordering changed the score ({a.total} vs {b.total})"
        assert a.passed == b.passed


@settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(extra=st.integers(1, 8))
def test_adding_unsupported_claims_never_raises_the_score(extra):
    for case_id in IDS:
        built = CASES[case_id]
        base = reference_output(built.truth, built.package, RB)
        reference_total = grade(built.truth, built.package, base, RB).total

        padded = copy.deepcopy(base)
        padded["discrepancies"] = padded["discrepancies"] + [_fabricated(built.package) for _ in range(extra)]
        padded_total = grade(built.truth, built.package, padded, RB).total
        assert padded_total <= reference_total, (
            f"{case_id}: reporting {extra} fabricated finding(s) raised the score from "
            f"{reference_total} to {padded_total} — the eval would reward hallucination"
        )


def test_score_is_bounded_for_every_case():
    for case_id in IDS:
        built = CASES[case_id]
        for label, output in (
            ("reference", reference_output(built.truth, built.package, RB)),
            ("empty", {}),
            ("prose", "the documents look broadly fine to me"),
            ("all codes", {"case_id": case_id, "assessment": "CLEAR", "documents_reviewed": ["X"],
                            "discrepancies": [{"code": c, "field": "f", "severity": "minor", "rule_id": "RULE-AMT-001",
                                               "evidence": [{"document_id": built.package.document_ids()[0], "page": 1, "location": "Total amount"}],
                                               "explanation": "x"} for c in sorted(RB.codes)]}),
        ):
            card = grade(built.truth, built.package, output, RB)
            assert 0.0 <= card.total <= 100.0, f"{case_id}/{label}: total {card.total} out of bounds"


def test_a_correct_answer_is_never_scored_below_a_stricter_but_still_correct_one():
    """Adding *extra correct* evidence to a reference finding must not lose marks —
    the guide's warning against checks so strict they reject correct answers."""
    built = CASES["DOC-005"]
    base = reference_output(built.truth, built.package, RB)
    stricter = copy.deepcopy(base)
    for d in stricter["discrepancies"]:
        d["evidence"] = d["evidence"] + [{"document_id": "LC-001", "page": 1, "location": "Credit Amount"}]
    assert grade(built.truth, built.package, stricter, RB).total >= grade(
        built.truth, built.package, base, RB
    ).total
