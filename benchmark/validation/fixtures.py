"""The grader's own test corpus: correct answers, and deliberately wrong ones.

Participant Guide p.17 grades this directly — "It accepts every reference solution and
rejects deliberately wrong answers" — and p.22 lists it as a pre-submission checkbox.
Every fixture is derived from computed ground truth, so as scenarios are added the corpus
grows without anyone hand-writing expected scores.

Each fixture carries its own assertions rather than a bare expected pass/fail, because the
point is to prove a *specific lever* works: that flipping severity costs exactly the
severity dimension, that citing a nonexistent document is caught, that shotgun-reporting
every code in the vocabulary cannot pass.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field as dc_field
from typing import Any, Callable

from benchmark.graders.scoring import (
    CAP_FABRICATED_ON_CLEAN,
    CAP_HALLUCINATED_EVIDENCE,
    CAP_MISSED_CRITICAL,
    CAP_UNPARSEABLE,
    CAP_WRONG_DETERMINATION,
    PASS_THRESHOLD,
    grade,
)
from benchmark.package import Package
from benchmark.rulebook.model import Rulebook
from benchmark.truth.engine import GroundFinding, GroundTruth

# A fabricated finding that looks plausible: real code, real document, wrong target field.
_UNRELATED_EVIDENCE = "Remarks"


@dataclass
class Fixture:
    name: str
    output: Any
    assertions: dict[str, Any] = dc_field(default_factory=dict)
    note: str = ""


def _evidence_for(finding: GroundFinding, use_synonym: bool = False) -> list[dict]:
    out = []
    for ev in finding.evidence:
        label = ev.label
        if use_synonym:
            label = label.upper().replace(" ", "  ")  # same field, different rendering
        out.append({"document_id": ev.doc_id, "page": ev.page, "location": label})
    return out


def _discrepancy(finding: GroundFinding, *, rule_id: str | None = None, severity: str | None = None,
                 synonyms: bool = False, evidence: list[dict] | None = None) -> dict:
    return {
        "code": finding.code,
        "field": finding.field,
        "severity": severity or finding.severity,
        "observed_values": dict(finding.observed),
        "rule_id": rule_id or finding.rule_id,
        "evidence": evidence if evidence is not None else _evidence_for(finding, synonyms),
        "explanation": finding.statement,
        "escalation_required": finding.severity == "critical",
    }


def reference_output(truth: GroundTruth, package: Package, rb: Rulebook) -> dict:
    """The oracle report: exactly what the engine computed, in the required contract."""
    unresolved = [
        {
            "field": u.field,
            "reason": u.reason,
            "evidence": [{"document_id": d, "page": 1, "location": u.field} for d in u.docs],
            "explanation": u.note,
        }
        for u in truth.unresolved
    ]
    return {
        "case_id": truth.case_id,
        "assessment": sorted(truth.acceptable_assessments)[0],
        "documents_reviewed": package.document_ids(),
        "discrepancies": [_discrepancy(f) for f in truth.findings],
        "unresolved_questions": unresolved,
        "summary": f"{len(truth.findings)} discrepancy(ies), {len(truth.unresolved)} unestablishable field(s).",
    }


def _with(output: dict, **changes) -> dict:
    out = copy.deepcopy(output)
    out.update(changes)
    return out


def build_fixtures(truth: GroundTruth, package: Package, rb: Rulebook) -> list[Fixture]:
    """One entry per grader lever. Skips levers the task cannot exercise."""
    reference = reference_output(truth, package, rb)
    fixtures: list[Fixture] = [
        Fixture(
            "reference_solution",
            reference,
            {"passed": True, "caps_empty": True, "total_gte": 95.0},
            "A known-correct report must pass, which proves the task is solvable and "
            "the grader accepts a correct answer.",
        ),
        Fixture(
            "alternative_valid_representation",
            _alternative(reference, package),
            {"passed": True, "caps_empty": True},
            "Same findings, reordered, with paraphrased field labels, extra correct "
            "evidence and an unrequested 'confidence' key. Must not be false-failed.",
        ),
        Fixture(
            "malformed_json",
            "I examined the documents and found some issues, roughly three of them.",
            {"total_eq": 0.0, "caps_include": [CAP_UNPARSEABLE], "passed": False},
            "Prose instead of the contract cannot be credited.",
        ),
        Fixture(
            "missing_required_key",
            _without_assessment(reference),
            {"dim_zero": ["format"], "format_zeroed": True},
            "A structurally invalid report loses the format dimension.",
        ),
        Fixture(
            "shotgun_every_code",
            _shotgun(reference, truth, rb, package),
            {"passed": False, "precision_lte": 0.35},
            "The guide's named gaming attack (p.12): list every possible answer and hope. "
            "Must not pass, and precision must collapse.",
        ),
        Fixture(
            "blanket_escalation",
            _blanket_escalation(reference, truth),
            {"uncertainty_zero_or_low": True, "passed": False, "caps_non_empty": True},
            "Escalating everything is not recognising uncertainty: it must fail, and for a "
            "reason the grader can name rather than by accident.",
        ),
    ]

    wrong_state = _a_wrong_state(truth)
    if wrong_state:
        fixtures.append(
            Fixture(
                "wrong_final_determination",
                _with(reference, assessment=wrong_state),
                {"passed": False, "caps_include": [CAP_WRONG_DETERMINATION], "total_gte": 60.0},
                "Every finding listed correctly, but the headline call is wrong. The "
                "determination is the outcome being graded, so this alone must fail the "
                "trial while the dimensions stay visible for analysis.",
            )
        )

    criticals = truth.critical_findings()
    if criticals:
        fixtures += [
            Fixture(
                "missed_one_critical",
                _with(reference, discrepancies=[d for i, d in enumerate(reference["discrepancies"]) if i != _first_critical(truth)])
                if _first_critical(truth) is not None else reference,
                {"total_eq": 0.0, "caps_include": [CAP_MISSED_CRITICAL], "passed": False},
                "A missed critical discrepancy is the catastrophic professional error.",
            ),
            Fixture(
                "false_clearance",
                _with(reference, assessment="CLEAR", discrepancies=[]),
                {"total_eq": 0.0, "caps_include": [CAP_MISSED_CRITICAL], "passed": False},
                "Approving a non-compliant presentation.",
            ),
        ]

    # Drop a genuinely non-critical finding, so this fixture measures partial credit and
    # not the missed-critical cap under a misleading name.
    minor_positions = [i for i, f in enumerate(truth.findings) if f.severity != "critical"]
    if minor_positions:
        drop = minor_positions[0]
        fixtures.append(
            Fixture(
                "missed_one_minor",
                _with(reference, discrepancies=[d for j, d in enumerate(reference["discrepancies"]) if j != drop]),
                {"lt_reference": True, "caps_absent": [CAP_MISSED_CRITICAL]},
                "Partial credit: dropping a non-critical finding must cost points, not "
                "the whole trial.",
            )
        )

    if truth.findings:
        first = truth.findings[0]
        fixtures += [
            Fixture(
                "wrong_rule_cited",
                _with(
                    reference,
                    discrepancies=[_discrepancy(f, rule_id=_other_rule(rb, f.rule_id)) for f in truth.findings],
                ),
                {"dim_zero": ["rule_mapping"], "lt_reference": True},
                "Right defect, wrong governing rule.",
            ),
            Fixture(
                "wrong_severity",
                _with(
                    reference,
                    discrepancies=[_discrepancy(f, severity="minor" if f.severity == "critical" else "critical") for f in truth.findings],
                ),
                {"lt_reference": True},
                "Severity must come from the rulebook, not from the model's instinct.",
            ),
            Fixture(
                "evidence_not_the_compared_field",
                _with(
                    reference,
                    discrepancies=[
                        _discrepancy(f, evidence=[{"document_id": package.document_ids()[0], "page": 1, "location": _UNRELATED_EVIDENCE}])
                        for f in truth.findings
                    ],
                ),
                {"dim_zero": ["evidence"]},
                "Findings still match by name, but traceability is not earned.",
            ),
            Fixture(
                "hallucinated_document",
                _with(
                    reference,
                    discrepancies=[
                        _discrepancy(f, evidence=[{"document_id": "ZZZ-999", "page": 1, "location": "Total amount"}])
                        for f in truth.findings
                    ],
                ),
                {"passed": False, "hallucination_flagged": True, "caps_include": [CAP_HALLUCINATED_EVIDENCE]},
                "Citing a document that is not in the package.",
            ),
            Fixture(
                "one_extra_fabricated",
                _with(reference, discrepancies=reference["discrepancies"] + [_fabricated(package)]),
                {"lt_reference": True},
                "Never reward a model for reporting more discrepancies than exist.",
            ),
            Fixture(
                "spurious_unresolved",
                _with(reference, unresolved_questions=reference["unresolved_questions"] + _fake_unresolved(3)),
                {"lt_reference": True},
                "Inventing uncertainty costs the uncertainty dimension.",
            ),
        ]

    if not truth.findings and not truth.unresolved:
        fixtures.append(
            Fixture(
                "false_accusation_on_clean",
                _with(reference, assessment="DISCREPANCIES_FOUND", discrepancies=[_plausible_finding(package)]),
                {"total_eq": 0.0, "caps_include": [CAP_FABRICATED_ON_CLEAN], "passed": False},
                "DOC-001 measures restraint. A fabricated discrepancy on a compliant "
                "presentation must not earn partial credit.",
            )
        )

    return fixtures


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------
def _first_critical(truth: GroundTruth) -> int | None:
    for i, finding in enumerate(truth.findings):
        if finding.severity == "critical":
            return i
    return None


def _a_wrong_state(truth: GroundTruth) -> str | None:
    for state in ("CLEAR", "DISCREPANCIES_FOUND", "INSUFFICIENT_EVIDENCE", "HUMAN_REVIEW_REQUIRED"):
        if state not in set(truth.acceptable_assessments):
            return state
    return None


def _alternative(reference: dict, package: Package) -> dict:
    out = copy.deepcopy(reference)
    out["discrepancies"] = list(reversed(out["discrepancies"]))
    for d in out["discrepancies"]:
        d["field"] = d["field"].upper().replace("_", " ")
        d["confidence"] = 0.9
        d["evidence"] = d["evidence"] + [
            {"document_id": package.document_ids()[1], "page": 1, "location": "Credit Amount"}
        ]
    out["summary"] = out["summary"].upper()
    return out


def _without_assessment(reference: dict) -> dict:
    out = copy.deepcopy(reference)
    out.pop("assessment")
    return out


def _shotgun(reference: dict, truth: GroundTruth, rb: Rulebook, package: Package) -> dict:
    out = copy.deepcopy(reference)
    reported = []
    for code in sorted(rb.codes):
        reported.append(
            {
                "code": code,
                "field": "everything",
                "severity": "critical",
                "observed_values": {},
                "rule_id": next(iter(rb.code_to_rules.get(code, ["RULE-DOC-001"]))),
                "evidence": [{"document_id": package.document_ids()[0], "page": 1, "location": "Remarks"}],
                "explanation": "Possible issue.",
                "escalation_required": True,
            }
        )
    out["discrepancies"] = reported
    out["assessment"] = "DISCREPANCIES_FOUND"
    return out


def _blanket_escalation(reference: dict, truth: GroundTruth) -> dict:
    out = copy.deepcopy(reference)
    out["discrepancies"] = []
    out["unresolved_questions"] = _fake_unresolved(10)
    out["assessment"] = "HUMAN_REVIEW_REQUIRED"
    return out


def _fake_unresolved(count: int) -> list[dict]:
    return [
        {
            "field": f"immaterial_detail_{i}",
            "reason": "absent",
            "evidence": [],
            "explanation": "Could not be confirmed.",
        }
        for i in range(count)
    ]


def _other_rule(rb: Rulebook, rule_id: str) -> str:
    for candidate in rb.by_id:
        if candidate != rule_id:
            return candidate
    return rule_id


def _fabricated(package: Package) -> dict:
    ids = package.document_ids()
    return {
        "code": "DESCRIPTION_CONTRADICTS_CREDIT",
        "field": "vessel name",
        "severity": "critical",
        "observed_values": {"invoice": "unspecified"},
        "rule_id": "RULE-DESC-001",
        "evidence": [{"document_id": ids[0], "page": 1, "location": "Vessel / Voyage"}],
        "explanation": "The vessel name does not match the credit.",
        "escalation_required": True,
    }


def _plausible_finding(package: Package) -> dict:
    ids = package.document_ids()
    return {
        "code": "AMOUNT_EXCEEDS_CREDIT",
        "field": "total_amount",
        "severity": "critical",
        "observed_values": {"invoice": "USD 100,000.00", "credit": "USD 100,000.00"},
        "rule_id": "RULE-AMT-001",
        "evidence": [{"document_id": ids[1], "page": 1, "location": "Total amount"}],
        "explanation": "The invoice exceeds the credit amount.",
        "escalation_required": True,
    }


# ---------------------------------------------------------------------------
# Assertion runner
# ---------------------------------------------------------------------------
def check(fixture: Fixture, truth: GroundTruth, package: Package, rb: Rulebook, reference_total: float) -> list[str]:
    card = grade(truth, package, fixture.output, rb)
    a = fixture.assertions
    problems: list[str] = []

    if "passed" in a and card.passed != a["passed"]:
        problems.append(f"expected passed={a['passed']} got {card.passed} (total {card.total:.1f}, caps {card.caps})")
    if a.get("caps_empty") and card.caps:
        problems.append(f"expected no caps, got {card.caps}")
    if a.get("caps_non_empty") and not card.caps:
        problems.append("expected at least one cap, got none")
    if "caps_include" in a:
        for cap in a["caps_include"]:
            if cap not in card.caps:
                problems.append(f"expected cap {cap}, got {card.caps}")
    if a.get("caps_absent"):
        for cap in a["caps_absent"]:
            if cap in card.caps:
                problems.append(f"did not expect cap {cap}")
    if "total_eq" in a and abs(card.total - a["total_eq"]) > 1e-9:
        problems.append(f"expected total {a['total_eq']} got {card.total:.2f}")
    if "total_gte" in a and card.total < a["total_gte"]:
        problems.append(f"expected total >= {a['total_gte']} got {card.total:.2f}")
    if a.get("lt_reference") and card.total >= reference_total:
        problems.append(f"expected total below reference ({reference_total:.1f}) got {card.total:.2f}")
    for dim in a.get("dim_zero", []):
        got = next((d for d in card.dimensions if d.name == dim), None)
        if got is None or got.points > 1e-9:
            problems.append(f"expected dimension {dim} to score 0, got {got.points if got else 'missing'}")
    if a.get("precision_lte") is not None:
        prec = next((d for d in card.dimensions if d.name == "precision"), None)
        if prec is None or prec.ratio > a["precision_lte"]:
            problems.append(f"expected precision ratio <= {a['precision_lte']}, got {prec.ratio if prec else 'missing'}")
    if a.get("uncertainty_zero_or_low"):
        unc = next((d for d in card.dimensions if d.name == "uncertainty"), None)
        if unc is None or unc.ratio > 0.2:
            problems.append(f"expected low uncertainty credit, got {unc.ratio if unc else 'missing'}")
    if a.get("hallucination_flagged") and not card.safety.get("hallucinated_document_cited"):
        problems.append("expected a hallucinated-document flag in safety metrics")
    return problems


def reference_total(truth: GroundTruth, package: Package, rb: Rulebook) -> float:
    return grade(truth, package, reference_output(truth, package, rb), rb).total
