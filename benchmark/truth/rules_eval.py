"""Rule evaluators: one interpreter per producer kind declared in the rulebook.

test_rulebook_engine_coverage.py asserts that every PRODUCER_KINDS entry has an
evaluator here and that no evaluator exists for a kind the rulebook does not declare,
so the rulebook and the engine cannot drift apart silently.

Evaluation order is fixed and matters: category rules run first, and RULE-AMD-003 runs
last so a single physical defect produces exactly one finding rather than inflating
recall twice.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from decimal import Decimal

from benchmark.domain import (
    Money,
    Quantity,
    location_matches,
    normalize_location,
    money_equal,
    money_within_pct,
    quantity_within_pct,
    renders_with_minor_units,
    parse_money,
)
from benchmark.rulebook.model import Rule, Rulebook
from benchmark.truth.engine import (
    GroundFinding,
    GroundTruth,
    _Ctx,
    adjust_deadline,
    build_terms,
)

SPEC_KEYS = ("GRADE", "MODEL", "MATERIAL", "ORIGIN", "STANDARD", "SIZE")

Doc = str  # doc_type string


def _f(rule: Rule, code: str, field: str, ctx: _Ctx, observed: dict[str, str], evidence: list, statement: str) -> GroundFinding:
    return GroundFinding(
        code=code,
        rule_id=rule.id,
        severity=rule.severity,
        field=field,
        docs=tuple(sorted({e.doc_id for e in evidence})),
        observed=observed,
        evidence=list(evidence),
        statement=statement,
    )


def _terms(ctx: _Ctx):
    return ctx.terms


# ---------------------------------------------------------------------------
# Amount and currency
# ---------------------------------------------------------------------------
def _invoice_money(ctx: _Ctx) -> Money | None:
    t = _terms(ctx)
    return ctx.money("INVOICE", "total_amount", field_name="total_amount", currency=t.currency)


def eval_amount_not_exceed_credit(rule: Rule, ctx: _Ctx) -> list[GroundFinding]:
    t = _terms(ctx)
    if t.amount_tolerance_pct is not None:
        return []  # RULE-AMT-002 owns the banded case
    inv = _invoice_money(ctx)
    if inv is None or inv.currency != t.currency:
        return []
    base = Money(t.currency, t.amount)
    out: list[GroundFinding] = []
    ev = ctx.evidence(("INVOICE", "total_amount"), ("CREDIT", "credit_amount"))
    if not money_equal(base, inv, ctx.rb) and inv.amount > t.amount:
        out.append(_f(rule, "AMOUNT_EXCEEDS_CREDIT", "total_amount", ctx,
                      {"invoice_total": str(inv), "credit_amount": str(base)}, ev,
                      "Invoice total exceeds the governing credit amount."))
    return out


def eval_amount_tolerance_band(rule: Rule, ctx: _Ctx) -> list[GroundFinding]:
    t = _terms(ctx)
    if t.amount_tolerance_pct is None:
        return []
    inv = _invoice_money(ctx)
    if inv is None or inv.currency != t.currency:
        return []
    base = Money(t.currency, t.amount)
    if money_within_pct(base, inv, t.amount_tolerance_pct, ctx.rb):
        return []
    return [
        _f(rule, "AMOUNT_TOLERANCE_EXCEEDED", "total_amount", ctx,
           {"invoice_total": str(inv), "credit_amount": str(base), "tolerance_pct": str(t.amount_tolerance_pct)},
           ctx.evidence(("INVOICE", "total_amount"), ("CREDIT", "credit_amount"), ("CREDIT", "amount_condition")),
           "Invoice total falls outside the tolerance band stated in the credit.")
    ]


def eval_currency_exact_match(rule: Rule, ctx: _Ctx) -> list[GroundFinding]:
    t = _terms(ctx)
    out: list[GroundFinding] = []
    inv_raw = ctx.raw("INVOICE", "currency")
    if inv_raw not in (None, object()):
        code = normalize_location(str(inv_raw)).replace(" ", "")
        if code and code != t.currency.lower():
            out.append(_f(rule, "CURRENCY_MISMATCH", "invoice_currency", ctx,
                          {"invoice_currency": str(inv_raw).strip(), "credit_currency": t.currency},
                          ctx.evidence(("INVOICE", "currency"), ("CREDIT", "currency")),
                          "Invoice is claimed in a currency other than the credit currency."))
    ins = (
        ctx.money("INSURANCE_CERTIFICATE", "insured_amount", field_name="insurance_amount", currency=t.currency)
        if ctx.governed("INSURANCE_CERTIFICATE")
        else None
    )
    if ins is not None and ins.currency != t.currency:
        out.append(_f(rule, "CURRENCY_MISMATCH", "insurance_currency", ctx,
                      {"insurance_currency": ins.currency, "credit_currency": t.currency},
                      ctx.evidence(("INSURANCE_CERTIFICATE", "insured_amount"), ("CREDIT", "currency")),
                      "Insurance amount is stated in a currency other than the credit currency."))
    return out


def eval_money_presentation_format(rule: Rule, ctx: _Ctx) -> list[GroundFinding]:
    t = _terms(ctx)
    inv = _invoice_money(ctx)
    if inv is None or inv.currency != t.currency:
        return []
    if not money_equal(Money(t.currency, t.amount), inv, ctx.rb):
        return []  # a real value difference is not a presentation defect
    if renders_with_minor_units(inv, ctx.rb):
        return []
    return [
        _f(rule, "AMOUNT_PRESENTATION_DEFECT", "total_amount_rendering", ctx,
           {"rendering": inv.rendering, "required": f"{t.currency} with {ctx.rb.minor_units(t.currency)} decimal places"},
           ctx.evidence(("INVOICE", "total_amount")),
           "Amount value agrees with the credit but is rendered without minor units.")
    ]


# ---------------------------------------------------------------------------
# Quantity and description
# ---------------------------------------------------------------------------
def eval_quantity_within_tolerance(rule: Rule, ctx: _Ctx) -> list[GroundFinding]:
    t = _terms(ctx)
    base = Quantity(t.quantity, t.quantity_unit)
    pct = Decimal(0) if t.commodity_class == "packaged" else Decimal(str(ctx.rb.definitions["quantity_tolerance"]["bulk"]["allowed_pct"]))
    targets = [
        ("INVOICE", "quantity", "invoice_quantity", "Quantity"),
        ("PACKING_LIST", "total_pieces", "packing_quantity", "Total Pieces"),
        ("BILL_OF_LADING", "shipped_quantity", "bl_quantity", "Quantity Shipped"),
    ]
    out: list[GroundFinding] = []
    for doc_type, name, field, label in targets:
        if not ctx.governed(doc_type):
            continue
        q = ctx.qty(doc_type, name, field_name=field)
        if q is None:
            continue
        conv = base.value if q.unit == base.unit else None
        from benchmark.domain import convert_quantity

        conv = convert_quantity(q, base.unit, ctx.rb)
        if conv is None:
            ctx.mark_unresolved(field, "not_comparable", (doc_type,), f"{q.unit} cannot be related to {base.unit} by any permitted conversion")
            continue
        if quantity_within_pct(base, q, pct, ctx.rb):
            continue
        code = "QUANTITY_MISMATCH" if pct == 0 else "QUANTITY_TOLERANCE_EXCEEDED"
        out.append(_f(rule, code, field, ctx,
                      {label: str(q), "credit_quantity": str(base), "allowed_pct": str(pct)},
                      list(ctx.evidence((doc_type, name), ("CREDIT", "quantity"))),
                      "Stated quantity differs from the credit quantity."))
    return out


def _spec_attributes(spec: tuple[str, ...] | list[str]) -> dict[str, str]:
    """'GRADE A; MODEL X-40' -> {'GRADE': 'A', 'MODEL': 'X-40'}."""
    attrs: dict[str, str] = {}
    for item in spec:
        text = normalize_location(str(item)).upper()
        key = text.split(" ", 1)[0]
        if key in SPEC_KEYS and " " in text:
            attrs[key] = text.split(" ", 1)[1].strip()
    return attrs


def eval_description_contradiction(rule: Rule, ctx: _Ctx) -> list[GroundFinding]:
    t = _terms(ctx)
    attrs = _spec_attributes(t.goods_spec)
    if not attrs:
        return []
    out: list[GroundFinding] = []
    for doc_type, name, field in (
        ("INVOICE", "goods_description", "invoice_description"),
        ("PACKING_LIST", "goods_description", "packing_description"),
        ("BILL_OF_LADING", "goods_description", "bl_description"),
        ("CERTIFICATE_OF_ORIGIN", "goods_description", "coo_description"),
    ):
        if not ctx.governed(doc_type):
            continue
        text = ctx.text(doc_type, name, field_name=field)
        if text is None:
            continue
        upper = normalize_location(text).upper()
        for key, value in attrs.items():
            m = re.search(rf"\b{re.escape(key)}\s+([a-z0-9][a-z0-9.\- ]*)", upper, re.IGNORECASE)
            if not m:
                continue  # generalised wording is compliant per RULE-DESC-001
            observed = m.group(1).strip().split(" ")[0]
            expected = value.split(" ")[0]
            if observed != expected:
                out.append(_f(rule, "DESCRIPTION_CONTRADICTS_CREDIT", field, ctx,
                              {key: observed, "credit_" + key.lower(): expected},
                              list(ctx.evidence((doc_type, name), ("CREDIT", "goods_specification"))),
                              f"Document states {key} {observed} but the credit specification requires {key} {expected}."))
    return out


def eval_non_governing_field_variance(rule: Rule, ctx: _Ctx) -> list[GroundFinding]:
    stipulated = {normalize_location(s) for s in _terms(ctx).stipulated_fields}
    out: list[GroundFinding] = []

    if "shipping marks" not in stipulated:
        marks: dict[str, str] = {}
        for doc_type, name in (("INVOICE", "shipping_marks"), ("PACKING_LIST", "shipping_marks"), ("BILL_OF_LADING", "shipping_marks")):
            if not ctx.governed(doc_type):
                continue
            val = ctx.text(doc_type, name, field_name="shipping_marks")
            if val:
                marks[doc_type] = val
        distinct = {normalize_location(v) for v in marks.values()}
        if len(distinct) > 1:
            out.append(_f(rule, "SHIPPING_MARKS_MISMATCH", "shipping_marks", ctx,
                          {k: v for k, v in marks.items()},
                          [e for e in ctx.evidence(*[(d, "shipping_marks") for d in marks])],
                          "Shipping marks differ between documents; the credit does not stipulate marks."))

    if "beneficiary address" not in stipulated:
        credit_addr = ctx.text("CREDIT", "beneficiary_address", field_name="beneficiary_address")
        invoice_addr = ctx.text("INVOICE", "beneficiary_address", field_name="beneficiary_address")
        if credit_addr and invoice_addr and normalize_location(credit_addr) != normalize_location(invoice_addr):
            out.append(_f(rule, "BENEFICIARY_ADDRESS_VARIANT", "beneficiary_address", ctx,
                          {"credit": credit_addr, "invoice": invoice_addr},
                          list(ctx.evidence(("CREDIT", "beneficiary_address"), ("INVOICE", "beneficiary_address"))),
                          "Beneficiary address is rendered differently; the credit does not stipulate the address."))
    return out


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------
def eval_shipment_on_or_before_latest(rule: Rule, ctx: _Ctx) -> list[GroundFinding]:
    t = _terms(ctx)
    on_board = ctx.day("BILL_OF_LADING", "on_board_date", field_name="on_board_date")
    if on_board is None:
        return []
    ctx.shipment_date = ctx.shipment_date or on_board
    if t.latest_shipment is None or on_board <= t.latest_shipment:
        return []
    return [
        _f(rule, "SHIPMENT_AFTER_LATEST_DATE", "on_board_date", ctx,
           {"on_board_date": on_board.isoformat(), "latest_shipment_date": t.latest_shipment.isoformat()},
           list(ctx.evidence(("BILL_OF_LADING", "on_board_date"), ("CREDIT", "latest_shipment_date"))),
           "Goods shipped after the latest date of shipment in the governing terms.")
    ]


def eval_presentation_within_period(rule: Rule, ctx: _Ctx) -> list[GroundFinding]:
    t = _terms(ctx)
    if t.presentation_days is None or ctx.presentation_date is None or ctx.shipment_date is None:
        return []
    due = ctx.shipment_date + timedelta(days=int(t.presentation_days))
    adjusted = adjust_deadline(due, ctx.non_working)
    if ctx.presentation_date <= adjusted:
        return []
    return [
        _f(rule, "PRESENTATION_AFTER_DEADLINE", "presentation_date", ctx,
           {"presentation_date": ctx.presentation_date.isoformat(),
            "shipment_date": ctx.shipment_date.isoformat(),
            "days_allowed": str(t.presentation_days),
            "deadline_as_adjusted": adjusted.isoformat()},
           list(ctx.evidence(("PRESENTATION_SCHEDULE", "presentation_date"), ("BILL_OF_LADING", "on_board_date"),
                             ("CREDIT", "presentation_period_days"))),
           "Presentation made after the period allowed following shipment, calculated on the supplied calendar.")
    ]


def eval_presentation_on_or_before_expiry(rule: Rule, ctx: _Ctx) -> list[GroundFinding]:
    t = _terms(ctx)
    if t.expiry is None or ctx.presentation_date is None:
        return []
    adjusted = adjust_deadline(t.expiry, ctx.non_working)
    if ctx.presentation_date <= adjusted:
        return []
    return [
        _f(rule, "PRESENTATION_AFTER_EXPIRY", "presentation_date_expiry", ctx,
           {"presentation_date": ctx.presentation_date.isoformat(), "expiry_date": t.expiry.isoformat(),
            "expiry_as_adjusted": adjusted.isoformat()},
           list(ctx.evidence(("PRESENTATION_SCHEDULE", "presentation_date"), ("CREDIT", "expiry_date"))),
           "Presentation made after the credit expiry date.")
    ]


def eval_document_dating_order(rule: Rule, ctx: _Ctx) -> list[GroundFinding]:
    out: list[GroundFinding] = []
    presentation = ctx.presentation_date
    dated = [
        ("INVOICE", "invoice_date", "invoice_date"),
        ("PACKING_LIST", "packing_list_date", "packing_list_date"),
        ("BILL_OF_LADING", "bl_date", "bl_issue_date"),
        ("INSURANCE_CERTIFICATE", "issue_date", "insurance_issue_date"),
        ("CERTIFICATE_OF_ORIGIN", "issue_date", "coo_issue_date"),
        ("INSPECTION_CERTIFICATE", "issue_date", "inspection_issue_date"),
    ]
    for doc_type, name, field in dated:
        if not ctx.governed(doc_type):
            continue
        d = ctx.day(doc_type, name, field_name=field)
        if d is None:
            continue
        if presentation and d > presentation:
            out.append(_f(rule, "DOCUMENT_DATED_AFTER_PRESENTATION", field, ctx,
                          {"document_date": d.isoformat(), "presentation_date": presentation.isoformat()},
                          list(ctx.evidence((doc_type, name), ("PRESENTATION_SCHEDULE", "presentation_date"))),
                          "Document is dated after the date of presentation."))
        if doc_type == "INSURANCE_CERTIFICATE" and ctx.shipment_date and d > ctx.shipment_date:
            out.append(_f(rule, "INSURANCE_DATED_AFTER_SHIPMENT", "insurance_issue_date", ctx,
                          {"insurance_date": d.isoformat(), "shipment_date": ctx.shipment_date.isoformat()},
                          list(ctx.evidence(("INSURANCE_CERTIFICATE", "issue_date"), ("BILL_OF_LADING", "on_board_date"))),
                          "Cover dated after the risk attached."))
        if doc_type == "INSPECTION_CERTIFICATE" and ctx.shipment_date and d > ctx.shipment_date:
            out.append(_f(rule, "INSPECTION_DATED_AFTER_SHIPMENT", "inspection_issue_date", ctx,
                          {"inspection_date": d.isoformat(), "shipment_date": ctx.shipment_date.isoformat()},
                          list(ctx.evidence(("INSPECTION_CERTIFICATE", "issue_date"), ("BILL_OF_LADING", "on_board_date"))),
                          "Inspection certified after shipment while the credit requires pre-shipment inspection."))
    return out


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------
def _alternatives(raw: str) -> list[str]:
    parts = re.split(r"\bor\b|/|,", normalize_location(raw))
    return [p.strip() for p in parts if p.strip()]


def eval_port_match(rule: Rule, ctx: _Ctx) -> list[GroundFinding]:
    t = _terms(ctx)
    out: list[GroundFinding] = []
    for name, governing, code, field in (
        ("port_of_loading", t.port_of_loading, "PORT_OF_LOADING_MISMATCH", "bl_port_of_loading"),
        ("port_of_discharge", t.port_of_discharge, "PORT_OF_DISCHARGE_MISMATCH", "bl_port_of_discharge"),
    ):
        shown = ctx.text("BILL_OF_LADING", name, field_name=field)
        if shown is None:
            continue
        acceptable = {normalize_location(a) for a in _alternatives(governing)}
        if normalize_location(shown) in acceptable:
            continue
        out.append(_f(rule, code, field, ctx,
                      {"transport_document": shown, "credit": governing},
                      list(ctx.evidence(("BILL_OF_LADING", name), ("CREDIT", name))),
                      "Transport document shows a port the credit does not name."))
    return out


def eval_party_match(rule: Rule, ctx: _Ctx) -> list[GroundFinding]:
    t = _terms(ctx)
    out: list[GroundFinding] = []
    for governing, name, code, field in (
        (t.consignee, "consignee", "CONSIGNEE_MISMATCH", "bl_consignee"),
        (t.notify_party, "notify_party", "NOTIFY_PARTY_MISMATCH", "bl_notify_party"),
    ):
        if not governing:
            continue  # credit silent: no finding may be raised
        shown = ctx.text("BILL_OF_LADING", name, field_name=field)
        if shown is None:
            continue
        if normalize_location(shown) != normalize_location(governing):
            out.append(_f(rule, code, field, ctx,
                          {"transport_document": shown, "credit": governing},
                          list(ctx.evidence(("BILL_OF_LADING", name), ("CREDIT", name + "_stipulated"))),
                          "Party shown differs from the party stipulated by the credit."))
    return out


def eval_shipment_permits(rule: Rule, ctx: _Ctx) -> list[GroundFinding]:
    t = _terms(ctx)
    out: list[GroundFinding] = []
    bls = ctx.docs("BILL_OF_LADING")
    if not t.partial_shipment_allowed and len(bls) > 1:
        out.append(_f(rule, "PARTIAL_SHIPMENT_NOT_PERMITTED", "partial_shipment", ctx,
                      {"bills_of_lading": str(len(bls))},
                      [e for bl in bls for e in ctx.evidence(("BILL_OF_LADING", "bl_no"))] or [],
                      "More than one transport document presented while partial shipment is prohibited."))
    if not t.transshipment_allowed:
        indicator = ctx.text("BILL_OF_LADING", "transshipment_indicator", field_name="transshipment")
        if indicator and normalize_location(indicator).startswith(("yes", "with transshipment", "via")):
            out.append(_f(rule, "TRANSSHIPMENT_NOT_PERMITTED", "transshipment", ctx,
                          {"indicator": indicator},
                          list(ctx.evidence(("BILL_OF_LADING", "transshipment_indicator"), ("CREDIT", "transshipment"))),
                          "Transshipment evidenced while the credit prohibits it."))
    return out


# ---------------------------------------------------------------------------
# Completeness and defects
# ---------------------------------------------------------------------------
def eval_required_documents_present(rule: Rule, ctx: _Ctx) -> list[GroundFinding]:
    t = _terms(ctx)
    out: list[GroundFinding] = []
    for doc_type in t.required_docs:
        if ctx.docs(doc_type):
            continue
        out.append(_f(rule, "DOCUMENT_MISSING", f"document_{doc_type.lower()}", ctx,
                      {"required_document": doc_type, "present": "no"},
                      list(ctx.evidence(("CREDIT", "required_documents"))),
                      f"Required document {doc_type} was not presented."))
    return out


def eval_signature_and_endorsement(rule: Rule, ctx: _Ctx) -> list[GroundFinding]:
    t = _terms(ctx)
    out: list[GroundFinding] = []
    if t.requires_signed_inspection:
        signed = ctx.text("INSPECTION_CERTIFICATE", "signed_by", field_name="inspection_signature")
        absent = signed is None or normalize_location(signed) in {"", "unsigned", "not signed", "-", "none"}
        if absent and ctx.docs("INSPECTION_CERTIFICATE"):
            ev = list(ctx.evidence(("INSPECTION_CERTIFICATE", "signed_by"), ("CREDIT", "signature_requirement")))
            out.append(_f(rule, "DOCUMENT_SIGNATURE_MISSING", "inspection_signature", ctx,
                          {"signed_by": signed or "absent"}, ev,
                          "Credit requires a signed inspection certificate; the signature is absent."))
    if t.requires_endorsed_bl:
        endorsement = ctx.text("BILL_OF_LADING", "endorsement_state", field_name="bl_endorsement")
        norm = normalize_location(endorsement or "")
        satisfied = "endorsed" in norm and not norm.startswith("not ") and "unendorsed" not in norm
        if endorsement and not satisfied:
            out.append(_f(rule, "DOCUMENT_ENDORSEMENT_DEFECTIVE", "bl_endorsement", ctx,
                          {"endorsement": endorsement},
                          list(ctx.evidence(("BILL_OF_LADING", "endorsement_state"), ("CREDIT", "endorsement_requirement"))),
                          "Credit requires an endorsed bill of lading; the endorsement is defective."))
    return out


def eval_validity_at_relevant_date(rule: Rule, ctx: _Ctx) -> list[GroundFinding]:
    if not ctx.governed("INSPECTION_CERTIFICATE"):
        return []
    valid_until = ctx.day("INSPECTION_CERTIFICATE", "valid_until", field_name="inspection_validity")
    if valid_until is None or ctx.shipment_date is None:
        return []
    if valid_until >= ctx.shipment_date:
        return []
    return [
        _f(rule, "DOCUMENT_EXPIRED", "inspection_validity", ctx,
           {"valid_until": valid_until.isoformat(), "shipment_date": ctx.shipment_date.isoformat()},
           list(ctx.evidence(("INSPECTION_CERTIFICATE", "valid_until"), ("BILL_OF_LADING", "on_board_date"))),
           "Certificate expired before the shipment date, so it does not satisfy the requirement.")
    ]


def eval_field_establishable(rule: Rule, ctx: _Ctx) -> list[GroundFinding]:
    """Realised by the typed accessors on _Ctx, which convert an absent, illegible or
    ambiguous value into an unresolved item wherever a rule needed to read it."""
    return []


# ---------------------------------------------------------------------------
# Amendment precedence (runs last)
# ---------------------------------------------------------------------------
_SUPERSEDED_TARGETS = {
    "amount": ("INVOICE", "total_amount", "total_amount"),
    "port_of_loading": ("BILL_OF_LADING", "port_of_loading", "bl_port_of_loading"),
    "port_of_discharge": ("BILL_OF_LADING", "port_of_discharge", "bl_port_of_discharge"),
    "quantity": ("INVOICE", "quantity", "invoice_quantity"),
    "goods_description": ("INVOICE", "goods_description", "invoice_description"),
}


def eval_documents_match_governing_terms(rule: Rule, ctx: _Ctx, history: dict[str, list[str]] | None = None) -> list[GroundFinding]:
    history = history or {}
    out: list[GroundFinding] = []
    for term, superseded_values in history.items():
        target = _SUPERSEDED_TARGETS.get(term)
        if target is None:
            continue
        doc_type, name, field = target
        shown = ctx.text(doc_type, name, field_name=field)
        if shown is None:
            continue
        for old in superseded_values:
            if location_matches(shown, old) or normalize_location(shown) == normalize_location(old):
                out.append(_f(rule, "DOCUMENT_CARRIES_SUPERSEDED_VALUE", field, ctx,
                              {"document_value": shown, "superseded_value": old},
                              list(ctx.evidence((doc_type, name), ("CREDIT", term if term != "quantity" else "quantity"))),
                              "Document still carries a value that an amendment superseded."))
                break
    return out


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
EVALUATORS = {
    "amount_not_exceed_credit": eval_amount_not_exceed_credit,
    "amount_tolerance_band": eval_amount_tolerance_band,
    "currency_exact_match": eval_currency_exact_match,
    "money_presentation_format": eval_money_presentation_format,
    "quantity_within_tolerance": eval_quantity_within_tolerance,
    "description_contradiction": eval_description_contradiction,
    "non_governing_field_variance": eval_non_governing_field_variance,
    "shipment_on_or_before_latest": eval_shipment_on_or_before_latest,
    "presentation_within_period": eval_presentation_within_period,
    "presentation_on_or_before_expiry": eval_presentation_on_or_before_expiry,
    "document_dating_order": eval_document_dating_order,
    "port_match": eval_port_match,
    "party_match": eval_party_match,
    "shipment_permits": eval_shipment_permits,
    "required_documents_present": eval_required_documents_present,
    "signature_and_endorsement": eval_signature_and_endorsement,
    "validity_at_relevant_date": eval_validity_at_relevant_date,
    "field_establishable": eval_field_establishable,
    "documents_match_governing_terms": eval_documents_match_governing_terms,
}

# Fixed order: category rules first, precedence rule last.
EVALUATION_ORDER = [k for k in EVALUATORS if k != "documents_match_governing_terms"] + ["documents_match_governing_terms"]


def compute_ground_truth(
    documents,
    credit_doc,
    amendment_docs,
    rb: Rulebook,
    case_id: str,
    presentation_date: date | None,
    non_working: frozenset[date],
    shipment_date: date | None = None,
) -> tuple[object, GroundTruth]:
    """Return (governing terms, ground truth) for one rendered package."""
    terms, applied, ignored, history = build_terms(rb, credit_doc, amendment_docs)
    ctx = _Ctx(
        documents=documents,
        rb=rb,
        case_id=case_id,
        presentation_date=presentation_date,
        shipment_date=shipment_date,
        non_working=non_working,
        terms=terms,
    )

    by_id = rb.by_id
    findings: list[GroundFinding] = []
    for kind in EVALUATION_ORDER:
        rule = _rule_for_kind(by_id, kind)
        if rule is None:
            continue
        evaluator = EVALUATORS[kind]
        if kind == "documents_match_governing_terms":
            for cand in evaluator(rule, ctx, history):
                existing = next((f for f in findings if f.field == cand.field), None)
                if existing is None:
                    findings.append(cand)
                else:
                    # Same physical defect, equally honest description. Recording it as an
                    # alias keeps one finding per defect while refusing to punish a model
                    # that named it the other way.
                    existing.alias_codes.add(cand.code)
            continue
        findings.extend(evaluator(rule, ctx))

    # One observable, one finding.
    deduped: dict[tuple[str, str], GroundFinding] = {}
    for f in findings:
        deduped.setdefault(f.key, f)
    ordered = sorted(deduped.values(), key=lambda f: (f.code, f.field))

    unresolved = list(ctx.unresolved)
    for i, f in enumerate(ordered, start=1):
        f.finding_id = f"GT-{i:03d}"

    if ordered and unresolved:
        acceptable = frozenset({"DISCREPANCIES_FOUND", "INSUFFICIENT_EVIDENCE", "HUMAN_REVIEW_REQUIRED"})
    elif ordered:
        acceptable = frozenset({"DISCREPANCIES_FOUND"})
    elif unresolved:
        acceptable = frozenset({"INSUFFICIENT_EVIDENCE", "HUMAN_REVIEW_REQUIRED"})
    else:
        acceptable = frozenset({"CLEAR"})

    truth = GroundTruth(
        case_id=case_id,
        rulebook_version=rb.version,
        terms=terms,
        findings=ordered,
        unresolved=unresolved,
        acceptable_assessments=acceptable,
        amendments_applied=tuple(applied),
        amendments_ignored=ignored,
    )
    return terms, truth


def _rule_for_kind(by_id: dict[str, Rule], kind: str) -> Rule | None:
    for rule in by_id.values():
        if rule.kind == kind:
            return rule
    return None
