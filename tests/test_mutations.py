"""Mutation testing: prove the grader-verification suite can actually fail.

Every entry breaks one lever of the grader. For each, the fixture corpus must notice —
otherwise the 65 green tests mean nothing, because a broken grader would look identical
to a working one.

This mirrors the concern that a scan walking zero files, or a check that passes for the
wrong reason, is indistinguishable from a real pass.
"""

from __future__ import annotations

import pytest

from benchmark.generator.build import build_case
from benchmark.generator.scenarios import SCENARIOS
from benchmark.graders import scoring
from benchmark.graders.output_schema import split_format_errors
from benchmark.rulebook import rulebook
from benchmark.validation.fixtures import build_fixtures, check, reference_total

RB = rulebook()
CASES = {cid: build_case(sc, RB) for cid, sc in SCENARIOS.items()}
IDS = sorted(CASES)


def _corpus_problems() -> list[str]:
    """Run the whole corpus and return every assertion failure it produces."""
    problems: list[str] = []
    for case_id in IDS:
        built = CASES[case_id]
        ref_total = reference_total(built.truth, built.package, RB)
        for fixture in build_fixtures(built.truth, built.package, RB):
            problems.extend(f"{case_id}/{fixture.name}: {p}" for p in check(fixture, built.truth, built.package, RB, ref_total))
    return problems


# Captured before any patching, so a mutation that wraps the real lever calls the real
# one rather than recursing into itself.
_ORIG = {
    name: getattr(scoring, name)
    for name in (
        "_recall_ratio",
        "_precision_ratio",
        "_evidence_covers",
        "_matched_ratio",
        "_uncertainty_ratio",
        "_apply_caps",
        "_hallucinated_document",
        "split_format_errors",
        "parse_output",
        "_gt_accepts_field",
    )
}

# Each mutation replaces a grader lever with a deliberately wrong version.
MUTATIONS: dict[str, tuple[str, object]] = {
    "recall_always_full": ("_recall_ratio", lambda matched, total: 1.0),
    "precision_never_penalised": ("_precision_ratio", lambda reported, fabricated, total: 1.0),
    "evidence_traceability_free": ("_evidence_covers", lambda package, finding, evidence: True),
    "rule_mapping_free": (
        "_matched_ratio",
        lambda matched, total, quality, lever: 1.0 if lever == "rule" else _ORIG["_matched_ratio"](matched, total, quality, lever),
    ),
    "severity_free": (
        "_matched_ratio",
        lambda matched, total, quality, lever: 1.0 if lever == "severity" else _ORIG["_matched_ratio"](matched, total, quality, lever),
    ),
    "uncertainty_free": ("_uncertainty_ratio", lambda truth, covered, spurious, reported: 1.0),
    "missed_critical_not_capped": (
        "_apply_caps",
        lambda total, caps, truth, missed, disc, assess, hall, acceptable, flag: _ORIG["_apply_caps"](
            total, caps, truth, [], disc, assess, hall, acceptable, flag
        ),
    ),
    "false_accusation_not_capped": (
        "_apply_caps",
        lambda total, caps, truth, missed, disc, assess, hall, acceptable, flag: _ORIG["_apply_caps"](
            total, caps, truth, missed, disc, assess, hall, acceptable, False
        ),
    ),
    "hallucinated_evidence_not_capped": (
        "_hallucinated_document",
        lambda package, evidence: False,
    ),
    "wrong_determination_allowed": (
        "_apply_caps",
        lambda total, caps, truth, missed, disc, assess, hall, acceptable, flag: _ORIG["_apply_caps"](
            total, caps, truth, missed, disc, assess, hall, set(acceptable) | {assess}, flag
        ),
    ),
    "structural_errors_treated_as_extra_keys": (
        "split_format_errors",
        lambda errors: ([], list(errors)),
    ),
    "prose_accepted_as_output": (
        "parse_output",
        lambda raw: ({"case_id": "X", "assessment": "CLEAR", "documents_reviewed": ["A"], "discrepancies": [], "unresolved_questions": [], "summary": "s"}, None),
    ),
    "field_matching_requires_exact_name": (
        "_gt_accepts_field",
        lambda gt, model_field: gt.field == model_field,
    ),
}

# The evidence-index lever lives in benchmark.package, not the grader. This mutation reverts
# citation resolution to the exact-match-only behaviour that a live gpt-oss transcript proved
# was wrong, so the fix is protected by something that can fail rather than by a single test
# that could rot unnoticed.
from benchmark import package as pkg_mod
from benchmark.domain import normalize_location


def _exact_only_resolve(self, doc_id: str, location: str):
    table = self._by_doc.get(doc_id)
    if table is None:
        return None
    return table.get(normalize_location(location))


PACKAGE_MUTATIONS: dict[str, tuple[str, object]] = {
    "citation_resolution_reverted_to_exact_match": ("resolve", _exact_only_resolve),
}


def _citation_regression_problems() -> list[str]:
    """Re-run the citation regression tests as plain assertions."""
    from tests.test_graders import (
        test_citation_quoted_with_its_value_earns_traceability,
        test_longest_label_wins_so_specific_fields_are_not_absorbed,
        test_loosening_citations_did_not_weaken_fabrication_detection,
    )

    problems: list[str] = []
    for fn in (
        test_citation_quoted_with_its_value_earns_traceability,
        test_longest_label_wins_so_specific_fields_are_not_absorbed,
        test_loosening_citations_did_not_weaken_fabrication_detection,
    ):
        try:
            fn()
        except AssertionError as exc:
            problems.append(f"{fn.__name__}: {exc}")
    return problems


@pytest.mark.parametrize("mutation", sorted(PACKAGE_MUTATIONS))
def test_package_index_mutation_is_detected(mutation):
    name, replacement = PACKAGE_MUTATIONS[mutation]
    original = getattr(pkg_mod.EvidenceIndex, name)
    setattr(pkg_mod.EvidenceIndex, name, replacement)
    try:
        problems = _citation_regression_problems()
    finally:
        setattr(pkg_mod.EvidenceIndex, name, original)

    assert problems, (
        f"index lever {mutation!r} was broken and no test noticed; the citation-resolution "
        "fix found from a real transcript is not protected"
    )
    assert _citation_regression_problems() == [], "restoring the lever did not restore green"


@pytest.mark.parametrize("mutation", sorted(MUTATIONS))
def test_mutation_is_detected(mutation):
    target, replacement = MUTATIONS[mutation]
    original = getattr(scoring, target)
    setattr(scoring, target, replacement)
    try:
        problems = _corpus_problems()
    finally:
        setattr(scoring, target, original)

    assert problems, (
        f"grader lever '{target}' was broken as {mutation!r} and the fixture corpus "
        "still reported everything green — the corpus cannot detect this class of failure."
    )

    # The suite must also be trustworthy the moment the lever is restored.
    assert _corpus_problems() == []


def test_corpus_is_green_without_mutations():
    assert _corpus_problems() == []
