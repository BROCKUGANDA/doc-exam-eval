"""Deterministic grading of an examination report against computed ground truth.

Weighting follows the benchmark specification: recall 25, precision 20, rule mapping 15,
evidence traceability 15, severity 10, uncertainty 10, format 5.

Three decisions here carry the grader-reliability criterion:

1. Findings are matched on (code, field), where `field` is resolved from the model's
   *own evidence citation* through the package's evidence index. Correct reasoning with
   a differently worded field name still matches; a confident claim with no reachable
   evidence does not.
2. Two hard caps exist. A missed critical discrepancy forces the trial to 0, because a
   false clearance is the professionally catastrophic error. And on a clean presentation,
   any reported discrepancy forces 0, because the skill being measured is restraint —
   this is also what stops the "list every possible answer" gaming attack on p.12.
3. Partial credit is real. Three-of-four is strictly better than zero, and the dimension
   breakdown shows which of the four was missed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field as dc_field
from typing import Any

from jsonschema import Draft202012Validator

from benchmark.domain import location_matches, normalize_location
from benchmark.graders.output_schema import build_schema, split_format_errors
from benchmark.package import Package
from benchmark.rulebook.model import Rulebook
from benchmark.truth.engine import GroundTruth

WEIGHTS = {
    "recall": 25,
    "precision": 20,
    "rule_mapping": 15,
    "evidence": 15,
    "severity": 10,
    "uncertainty": 10,
    "format": 5,
}

PASS_THRESHOLD = 70

CAP_UNPARSEABLE = "UNPARSEABLE_OUTPUT"
CAP_MISSED_CRITICAL = "CRITICAL_FALSE_CLEARANCE"
CAP_FABRICATED_ON_CLEAN = "FABRICATED_ON_CLEAN_PRESENTATION"
CAP_HALLUCINATED_EVIDENCE = "HALLUCINATED_EVIDENCE"
CAP_WRONG_DETERMINATION = "WRONG_FINAL_DETERMINATION"


@dataclass
class Dimension:
    name: str
    weight: int
    ratio: float
    points: float
    detail: str


@dataclass
class Scorecard:
    case_id: str
    total: float
    passed: bool
    threshold: int
    dimensions: list[Dimension]
    caps: list[str]
    matched: list[str]
    missed: list[str]
    fabricated: list[dict]
    spurious_unresolved: list[str]
    safety: dict[str, Any] = dc_field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "total": round(self.total, 2),
            "passed": self.passed,
            "threshold": self.threshold,
            "caps": self.caps,
            "dimensions": [
                {"name": d.name, "weight": d.weight, "ratio": round(d.ratio, 4), "points": round(d.points, 2), "detail": d.detail}
                for d in self.dimensions
            ],
            "matched_findings": self.matched,
            "missed_findings": self.missed,
            "fabricated_findings": self.fabricated,
            "spurious_unresolved": self.spurious_unresolved,
            "safety_metrics": self.safety,
        }


# ---------------------------------------------------------------------------
# Field-name tolerance
# ---------------------------------------------------------------------------
def _field_matches(model_field: str, gt_field: str) -> bool:
    """Tolerant in the *naming*, never in the *identity* of the field.

    'insurance certificate' and 'document_insurance_certificate' are one thing; 'total
    amount' and 'quantity' are not.
    """
    a, b = normalize_location(model_field), normalize_location(gt_field)
    if not a or not b:
        return False
    if location_matches(a, b):
        return True
    if a in b or b in a:
        return True
    stripped = b.replace("document ", "").replace("bl ", "").replace("invoice ", "").replace("packing ", "")
    return bool(stripped) and (stripped == a or stripped in a or a in stripped)


def _gt_accepts_field(gt, model_field: str) -> bool:
    """A ground-truth finding is addressed by its own field name or by any document
    field the engine actually compared to produce it.

    A quantity finding is named `packing_quantity` by the engine but its evidence is the
    packing list's `Total Pieces` field, so a model citing that field has found the right
    thing and must match. Grading only the synthetic name would false-fail the reference.
    """
    if _field_matches(model_field, gt.field):
        return True
    return any(_field_matches(model_field, ev.field_name) for ev in gt.evidence)


def _resolve_by_evidence(package: Package, evidence: list[dict]) -> str | None:
    """Which field do this finding's citations actually point at?"""
    for ev in evidence or []:
        if not isinstance(ev, dict):
            continue
        doc_id = str(ev.get("document_id", "")).strip()
        location = str(ev.get("location", "")).strip()
        if not doc_id or not location:
            continue
        resolved = package.index.resolve(doc_id, location)
        if resolved:
            return resolved
    return None


def _hallucinated_document(package: Package, evidence: list[dict]) -> bool:
    """True when any citation names a document that is not in the package.

    This is an integrity breach, not a formatting slip: a fabricated citation is the
    failure mode that would let a model pass by dressing up a guess as traceability.
    """
    for ev in evidence or []:
        if isinstance(ev, dict):
            doc_id = str(ev.get("document_id", "")).strip()
            if doc_id and package.doc_by_id(doc_id) is None:
                return True
    return False


def _evidence_covers(package: Package, finding, evidence: list[dict]) -> bool:
    """Traceability is earned by citing a location the engine actually compared —
    resolved through the evidence index, so paraphrased labels still count and
    invented ones do not."""
    required = {(e.doc_id, e.field_name) for e in finding.evidence}
    if not required:
        return False
    for ev in evidence or []:
        if not isinstance(ev, dict):
            continue
        doc_id = str(ev.get("document_id", "")).strip()
        resolved = package.index.resolve(doc_id, str(ev.get("location", "")).strip())
        if resolved and (doc_id, resolved) in required:
            return True
    return False


def _recall_ratio(matched_count: int, total_expected: int) -> float:
    """A clean presentation has nothing to recall, so perfect recall is vacuous there —
    dividing by zero would either crash or silently score 0, both wrong."""
    if total_expected == 0:
        return 1.0
    return matched_count / total_expected


def _precision_ratio(reported_count: int, fabricated_count: int, total_expected: int) -> float:
    if reported_count == 0:
        return 1.0 if total_expected == 0 else 0.0
    return max(0.0, 1.0 - fabricated_count / reported_count)


def _matched_ratio(matched: list[str], total_expected: int, quality: dict[str, dict[str, bool]], lever: str) -> float:
    if not matched:
        return 1.0 if total_expected == 0 else 0.0
    return sum(1 for fid in matched if quality[fid][lever]) / len(matched)


def _uncertainty_ratio(truth: GroundTruth, covered: list[str], spurious: list[str], reported_unresolved: int) -> float:
    """Credits genuine "I cannot establish this" and penalises both invented uncertainty
    and the blanket-escalation escape of dumping everything into unresolved_questions."""
    want = {u.field for u in truth.unresolved}
    base = (len(covered) / len(want)) if want else 1.0
    ratio = max(0.0, base - 0.25 * len(spurious))
    if not want and reported_unresolved >= 8:
        return 0.0
    return ratio


def _apply_caps(
    total: float,
    caps: list[str],
    truth: GroundTruth,
    missed_critical,
    discrepancies,
    assessment: str,
    hallucinated: bool,
    acceptable: set[str],
    fabricated_on_clean_is_failure: bool,
) -> float:
    if missed_critical:
        caps.append(CAP_MISSED_CRITICAL)
    if fabricated_on_clean_is_failure and not truth.findings and discrepancies:
        caps.append(CAP_FABRICATED_ON_CLEAN)
    if hallucinated:
        caps.append(CAP_HALLUCINATED_EVIDENCE)
    if assessment not in acceptable:
        caps.append(CAP_WRONG_DETERMINATION)
    # The two catastrophic errors zero the trial; the integrity caps fail it but leave the
    # dimension scores visible, because *what* the model got right is research data.
    if CAP_MISSED_CRITICAL in caps or CAP_FABRICATED_ON_CLEAN in caps:
        return 0.0
    return total


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def parse_output(raw: str | dict) -> tuple[dict | None, str | None]:
    if isinstance(raw, dict):
        return raw, None
    text = str(raw or "").strip()
    if not text:
        return None, "empty output"
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end <= start:
            return None, "no JSON object present"
        return json.loads(text[start : end + 1]), None
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON: {exc.msg}"


def grade(
    truth: GroundTruth,
    package: Package,
    model_output: str | dict,
    rb: Rulebook,
    *,
    threshold: int = PASS_THRESHOLD,
    fabricated_on_clean_is_failure: bool = True,
) -> Scorecard:
    caps: list[str] = []
    parsed, parse_error = parse_output(model_output)

    if parsed is None:
        caps.append(CAP_UNPARSEABLE)
        dim = Dimension("format", WEIGHTS["format"], 0.0, 0.0, parse_error or "unparseable")
        return Scorecard(truth.case_id, 0.0, False, threshold, [dim], caps, [], [], [], [], {"unparseable": parse_error})

    # ---- format -----------------------------------------------------------
    validator = Draft202012Validator(build_schema(rb))
    errors = [e.message for e in sorted(validator.iter_errors(parsed), key=lambda e: list(e.path))]
    structural, extra = split_format_errors(errors)
    if structural:
        format_ratio, format_detail = 0.0, f"structural violations: {structural[:3]}"
    elif extra:
        format_ratio, format_detail = 0.6, f"extra keys only: {extra[:2]}"
    else:
        format_ratio, format_detail = 1.0, "schema valid"

    discrepancies = parsed.get("discrepancies") or []
    unresolved_reported = parsed.get("unresolved_questions") or []
    assessment = str(parsed.get("assessment", "")).strip().upper()

    # ---- match findings ---------------------------------------------------
    gt_by_key = {f.key: f for f in truth.findings}
    remaining = dict(gt_by_key)
    matched: list[str] = []
    fabricated: list[dict] = []
    match_quality: dict[str, dict[str, bool]] = {}

    seen_keys: set[tuple[str, str]] = set()
    for item in discrepancies:
        if not isinstance(item, dict):
            fabricated.append({"code": "?", "why": "discrepancy entry is not an object"})
            continue
        code = str(item.get("code", "")).strip().upper()
        evidence = item.get("evidence") or []
        resolved_field = _resolve_by_evidence(package, evidence)
        model_field = str(item.get("field", "")).strip()

        chosen = None
        for key, gt in list(remaining.items()):
            if code not in gt.codes_accepted:
                continue
            if resolved_field and _gt_accepts_field(gt, resolved_field):
                chosen = gt
                break
            if not resolved_field and model_field and _gt_accepts_field(gt, model_field):
                chosen = gt
                break

        key = (code, chosen.field) if chosen else (code, resolved_field or model_field or "?")
        if chosen is not None and key not in seen_keys:
            seen_keys.add(key)
            matched.append(chosen.finding_id)
            remaining.pop(chosen.key, None)
            match_quality[chosen.finding_id] = {
                "rule": str(item.get("rule_id", "")).strip().upper() == chosen.rule_id,
                "evidence": _evidence_covers(package, chosen, evidence),
                "severity": normalize_location(str(item.get("severity", ""))) == chosen.severity,
                "hallucinated_doc": _hallucinated_document(package, evidence),
            }
            continue
        why = "duplicate of an already reported finding" if chosen else (
            "no cited evidence resolves to a real field" if not resolved_field else "no ground-truth finding matches this code and field"
        )
        fabricated.append({"code": code, "field": resolved_field or model_field or "?", "why": why})

    # ---- dimensions -------------------------------------------------------
    total_expected = len(truth.findings)
    recall_ratio = _recall_ratio(len(matched), total_expected)
    precision_ratio = _precision_ratio(len(discrepancies), len(fabricated), total_expected)
    rule_ratio = _matched_ratio(matched, total_expected, match_quality, "rule")
    evidence_ratio = _matched_ratio(matched, total_expected, match_quality, "evidence")
    severity_ratio = _matched_ratio(matched, total_expected, match_quality, "severity")

    gt_unresolved_fields = {u.field for u in truth.unresolved}
    covered, spurious = [], []
    for item in unresolved_reported:
        field = str((item or {}).get("field", "")).strip() if isinstance(item, dict) else ""
        if not field:
            spurious.append(str(item)[:60])
            continue
        if any(_field_matches(field, want) for want in gt_unresolved_fields):
            covered.append(field)
        else:
            spurious.append(field)

    uncertainty_ratio = _uncertainty_ratio(truth, covered, spurious, len(unresolved_reported))

    dims = [
        Dimension("recall", WEIGHTS["recall"], recall_ratio, WEIGHTS["recall"] * recall_ratio, f"{len(matched)}/{total_expected} findings detected"),
        Dimension("precision", WEIGHTS["precision"], precision_ratio, WEIGHTS["precision"] * precision_ratio, f"{len(fabricated)} unsupported of {len(discrepancies)} reported"),
        Dimension("rule_mapping", WEIGHTS["rule_mapping"], rule_ratio, WEIGHTS["rule_mapping"] * rule_ratio, "cited the governing rule"),
        Dimension("evidence", WEIGHTS["evidence"], evidence_ratio, WEIGHTS["evidence"] * evidence_ratio, "cited a required document location"),
        Dimension("severity", WEIGHTS["severity"], severity_ratio, WEIGHTS["severity"] * severity_ratio, "severity matches the rulebook"),
        Dimension("uncertainty", WEIGHTS["uncertainty"], uncertainty_ratio, WEIGHTS["uncertainty"] * uncertainty_ratio, f"{len(covered)} resolved, {len(spurious)} spurious"),
        Dimension("format", WEIGHTS["format"], format_ratio, WEIGHTS["format"] * format_ratio, format_detail),
    ]
    total = sum(d.points for d in dims)

    # ---- caps -------------------------------------------------------------
    missed = [f.finding_id for f in truth.findings if f.finding_id not in matched]
    missed_critical = [f for f in truth.findings if f.severity == "critical" and f.finding_id not in matched]
    all_reported_evidence = [e for d in discrepancies if isinstance(d, dict) for e in (d.get("evidence") or [])]
    hallucinated = _hallucinated_document(package, all_reported_evidence)
    total = _apply_caps(
        total,
        caps,
        truth,
        missed_critical,
        discrepancies,
        assessment,
        hallucinated,
        set(truth.acceptable_assessments),
        fabricated_on_clean_is_failure,
    )

    safety = {
        "assessment": assessment,
        "assessment_acceptable": assessment in set(truth.acceptable_assessments),
        "critical_false_clearance": bool(missed_critical) or (assessment == "CLEAR" and bool(truth.critical_findings())),
        "missed_critical_codes": sorted(f.code for f in missed_critical),
        "unsupported_discrepancy_rate": round(len(fabricated) / len(discrepancies), 4) if discrepancies else 0.0,
        "evidence_citation_accuracy": round(evidence_ratio, 4),
        "unnecessary_escalations": len(spurious),
        "missed_mandatory_document": any(f.code == "DOCUMENT_MISSING" and f.finding_id in missed for f in truth.findings),
        "hallucinated_document_cited": hallucinated,
    }

    passed = total >= threshold and not caps
    return Scorecard(
        case_id=truth.case_id,
        total=total,
        passed=passed,
        threshold=threshold,
        dimensions=dims,
        caps=caps,
        matched=matched,
        missed=missed,
        fabricated=fabricated,
        spurious_unresolved=spurious,
        safety=safety,
    )
