"""Scenario -> rendered package -> computed ground truth -> intent check.

The intent check is the load-bearing part of this file. A scenario declares what its
author expects to be found; the engine computes what is actually present; the two are
compared and any mismatch is a bug in the benchmark, not a test to be edited until it
passes. That is what keeps reference answers verified rather than asserted.

`seed` selects *renderings*, never *meanings*: the same case can be presented as
"USD 100,000.00" or "USD 100000.0", and as "2026-03-05" or "5 March 2026". A grader
that false-fails when only the rendering changed is exactly the failure the guide warns
about (p.10), so variation is generated deliberately and graded as equivalent.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from datetime import date
from decimal import Decimal

from benchmark.domain import parse_date
from benchmark.generator.documents import LABELS, render_document
from benchmark.package import UNREADABLE, Document, FieldValue, Package
from benchmark.rulebook.model import Rulebook
from benchmark.truth.rules_eval import compute_ground_truth

CREDIT_LABELS = {name: label for name, (label, _s) in LABELS["CREDIT"].items()}
REVISED = "(revised)"

DOC_META = {
    "INVOICE": ("Commercial Invoice", "Meridian Export House"),
    "PACKING_LIST": ("Packing List", "Meridian Export House"),
    "BILL_OF_LADING": ("Bill of Lading", "Amber Wave Lines"),
    "INSURANCE_CERTIFICATE": ("Insurance Certificate", "Halcyon Marine Insurance"),
    "CERTIFICATE_OF_ORIGIN": ("Certificate of Origin", "Kestrel Chamber of Commerce"),
    "INSPECTION_CERTIFICATE": ("Inspection Certificate", "Northbank Verification Ltd"),
}


@dataclass
class Amendment:
    amendment_id: str
    amendment_date: str
    effective_date: str
    acceptance_state: str          # ACCEPTED | NOT ACCEPTED
    revised: dict[str, str]        # credit field name -> rendered value
    acknowledgement: str = ""


@dataclass
class Intent:
    findings: list[tuple[str, str]] = dc_field(default_factory=list)      # (code, field)
    unresolved: list[tuple[str, str]] = dc_field(default_factory=list)    # (field, reason)
    assessment: set[str] = dc_field(default_factory=set)


@dataclass
class Scenario:
    case_id: str
    title: str
    seed: int
    credit: dict[str, str]
    documents: dict[str, dict[str, str]]
    presentation: dict[str, str]
    non_working_days: list[str] = dc_field(default_factory=list)
    amendments: list[Amendment] = dc_field(default_factory=list)
    overrides: list[tuple[str, str, str]] = dc_field(default_factory=list)
    unreadable: list[tuple[str, str]] = dc_field(default_factory=list)
    omitted: list[tuple[str, str]] = dc_field(default_factory=list)
    dropped_docs: list[str] = dc_field(default_factory=list)
    extra_bills_of_lading: int = 0
    intent: Intent = dc_field(default_factory=Intent)
    note: str = ""


@dataclass
class BuiltCase:
    package: Package
    truth: object
    intent_mismatches: list[str]

    @property
    def intent_ok(self) -> bool:
        return not self.intent_mismatches


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def _doc_id(doc_type: str, index: int = 1) -> str:
    prefix = {
        "INVOICE": "INV",
        "PACKING_LIST": "PL",
        "BILL_OF_LADING": "BL",
        "INSURANCE_CERTIFICATE": "INS",
        "CERTIFICATE_OF_ORIGIN": "COO",
        "INSPECTION_CERTIFICATE": "INSP",
        "PRESENTATION_SCHEDULE": "PRES",
        "BUSINESS_CALENDAR": "CAL",
        "CORRESPONDENCE": "MSG",
        "CREDIT": "LC",
        "AMENDMENT": "AMD",
    }[doc_type]
    return f"{prefix}-{index:03d}"


def build_case(scenario: Scenario, rb: Rulebook) -> BuiltCase:
    documents: list[Document] = []

    credit_values = dict(scenario.credit)
    credit_doc = render_document(_doc_id("CREDIT"), "CREDIT", "Documentary Credit", credit_values.get("issuing_bank", "Crescent Trading Bank"), credit_values)
    documents.append(credit_doc)

    for i, amend in enumerate(scenario.amendments, start=1):
        extra = tuple(
            (f"rev_{field}", f"{CREDIT_LABELS[field]} {REVISED}", ())
            for field in amend.revised
            if field in CREDIT_LABELS
        )
        values = {
            "amendment_id": amend.amendment_id,
            "amendment_date": amend.amendment_date,
            "effective_date": amend.effective_date,
            "acceptance_state": amend.acceptance_state,
            "acknowledgement": amend.acknowledgement or "advice received from the advising bank",
        }
        for field, rendered in amend.revised.items():
            values[f"rev_{field}"] = rendered
        documents.append(
            render_document(
                _doc_id("AMENDMENT", i), "AMENDMENT", "Amendment to Documentary Credit", "Crescent Trading Bank",
                values, extra_layout=extra,
            )
        )

    present_types: list[str] = []
    for doc_type, values in scenario.documents.items():
        if doc_type in scenario.dropped_docs:
            continue
        vals = dict(values)
        title, issuer = DOC_META[doc_type]
        docs_count = 2 if doc_type == "BILL_OF_LADING" and scenario.extra_bills_of_lading else 1
        for n in range(docs_count):
            body = dict(vals)
            if n == 1:
                body = _second_bill_of_lading(body)
            documents.append(render_document(_doc_id(doc_type, n + 1), doc_type, title, issuer, body))
        present_types.append(doc_type)

    presentation_values = dict(scenario.presentation)
    presentation_values.setdefault("documents_lodged", ", ".join(_friendly(t) for t in present_types))
    presentation_values.setdefault("credit_reference", scenario.credit["credit_no"])
    documents.append(render_document(_doc_id("PRESENTATION_SCHEDULE"), "PRESENTATION_SCHEDULE", "Schedule of Presentation", "Halcyon Trade Finance", presentation_values))

    cal_values = {
        "calendar_title": "Business calendar applicable to this credit",
        "working_days_note": "Monday to Friday except the closed dates listed below",
        "non_working_days": ", ".join(scenario.non_working_days) if scenario.non_working_days else "none",
    }
    documents.append(render_document(_doc_id("BUSINESS_CALENDAR"), "BUSINESS_CALENDAR", "Business Calendar", "Crescent Trading Bank", cal_values))

    _apply_deviations(documents, scenario)

    # Dates that the engine needs before it can grade.
    pres = next((d for d in documents if d.doc_type == "PRESENTATION_SCHEDULE"), None)
    presentation_date = None
    if pres and pres.get("presentation_date"):
        res = parse_date(pres.get("presentation_date").raw, rb)
        presentation_date = res.value
    non_working = frozenset(date.fromisoformat(d) for d in scenario.non_working_days)

    bl = next((d for d in documents if d.doc_type == "BILL_OF_LADING"), None)
    shipment_date = None
    if bl and bl.get("on_board_date"):
        shipment_date = parse_date(bl.get("on_board_date").raw, rb).value

    amendment_docs = [d for d in documents if d.doc_type == "AMENDMENT"]
    terms, truth = compute_ground_truth(
        documents=documents,
        credit_doc=credit_doc,
        amendment_docs=amendment_docs,
        rb=rb,
        case_id=scenario.case_id,
        presentation_date=presentation_date,
        non_working=non_working,
        shipment_date=shipment_date,
    )

    package = Package(
        case_id=scenario.case_id,
        seed=scenario.seed,
        documents=documents,
        terms=terms,
        calendar=[],
        non_working_days=[date.fromisoformat(d) for d in scenario.non_working_days],
        presentation_date=presentation_date,
        shipment_date=shipment_date,
        scenario_note=scenario.note,
    )
    return BuiltCase(package=package, truth=truth, intent_mismatches=_check_intent(scenario, truth))


def _second_bill_of_lading(body: dict[str, str]) -> dict[str, str]:
    """A split presentation: same voyage, half the quantity, second bill number."""
    from benchmark.domain import parse_quantity

    qty = parse_quantity(body.get("shipped_quantity", "1 PCS"))
    half = (qty.value / 2).quantize(Decimal("1"))
    out = dict(body)
    out["bl_no"] = "AWL-BL-0022"
    out["shipped_quantity"] = f"{half} {qty.unit}"
    return out


def _apply_deviations(documents: list[Document], scenario: Scenario) -> None:
    by_type: dict[str, list[Document]] = {}
    for d in documents:
        by_type.setdefault(d.doc_type, []).append(d)

    for doc_type, field, value in scenario.overrides:
        for d in by_type.get(doc_type, []):
            fv = d.get(field)
            if fv is None:
                raise KeyError(f"{scenario.case_id}: cannot override absent field {doc_type}.{field}")
            _set(d, FieldValue(fv.name, fv.label, value, fv.synonyms, value.strip() == UNREADABLE, fv.page, fv.line))

    for doc_type, field in scenario.unreadable:
        for d in by_type.get(doc_type, []):
            fv = d.get(field)
            if fv is None:
                continue
            _set(d, FieldValue(fv.name, fv.label, UNREADABLE, fv.synonyms, True, fv.page, fv.line))

    for doc_type, field in scenario.omitted:
        for d in by_type.get(doc_type, []):
            d.fields.pop(field, None)


def _set(doc: Document, fv) -> None:
    doc.fields[fv.name] = fv


def _friendly(doc_type: str) -> str:
    return {
        "INVOICE": "commercial invoice",
        "PACKING_LIST": "packing list",
        "BILL_OF_LADING": "bill of lading",
        "INSURANCE_CERTIFICATE": "insurance certificate",
        "CERTIFICATE_OF_ORIGIN": "certificate of origin",
        "INSPECTION_CERTIFICATE": "inspection certificate",
    }.get(doc_type, doc_type.lower())


def _check_intent(scenario: Scenario, truth) -> list[str]:
    """Author expectation vs engine output. Mismatch means the benchmark is wrong."""
    problems: list[str] = []
    computed = sorted({(f.code, f.field) for f in truth.findings})
    expected = sorted(set(scenario.intent.findings))
    for code, field in expected:
        if (code, field) not in computed:
            problems.append(f"intended finding {code} on {field} was not computed")
    for code, field in computed:
        if (code, field) not in expected:
            problems.append(f"engine computed unexpected finding {code} on {field}")

    got_unresolved = sorted({(u.field, u.reason) for u in truth.unresolved})
    want_unresolved = sorted(set(scenario.intent.unresolved))
    for pair in want_unresolved:
        if pair not in got_unresolved:
            problems.append(f"intended unresolved {pair} was not computed")
    for pair in got_unresolved:
        if pair not in want_unresolved:
            problems.append(f"engine computed unexpected unresolved {pair}")

    if scenario.intent.assessment:
        if not (scenario.intent.assessment & set(truth.acceptable_assessments)):
            problems.append(
                f"intended assessment {sorted(scenario.intent.assessment)} not among acceptable "
                f"{sorted(truth.acceptable_assessments)}"
            )
    return problems
