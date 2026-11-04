"""Amendment precedence — implemented exactly once.

Both the document generator and the truth engine call this, so the terms a clean
presentation is built *from* and the terms a model is graded *against* cannot drift
apart. That shared origin is what makes RULE-AMD-* auditable rather than assumed.

Policy from RULE-AMD-001: only ACCEPTED amendments take effect.
Policy from RULE-AMD-002: for one field, the later accepted effective date wins.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from benchmark.package import GoverningTerms
from benchmark.rulebook.model import Rulebook

ACCEPTED = "ACCEPTED"
NOT_ACCEPTED = "NOT ACCEPTED"

# An amendment may only change one of these. Anything else is a authoring bug and
# raises, rather than silently becoming a governing value nothing checks.
CHANGEABLE = frozenset(
    {
        "amount",
        "amount_tolerance_pct",
        "amount_about",
        "latest_shipment",
        "expiry",
        "presentation_days",
        "port_of_loading",
        "port_of_discharge",
        "consignee",
        "notify_party",
        "partial_shipment_allowed",
        "transshipment_allowed",
        "goods_description",
        "goods_spec",
        "quantity",
        "quantity_unit",
        "required_docs",
        "requires_signed_inspection",
        "requires_endorsed_bl",
        "stipulated_fields",
        "commodity_class",
        "currency",
    }
)


def _coerce(key: str, value):
    if key in {"amount", "amount_tolerance_pct", "quantity"}:
        return Decimal(str(value)) if value is not None else None
    if key in {"latest_shipment", "expiry"}:
        return date.fromisoformat(value) if isinstance(value, str) else value
    if key in {"goods_spec", "required_docs", "stipulated_fields"}:
        return tuple(value) if key != "stipulated_fields" else frozenset(value)
    if key in {"presentation_days"}:
        return int(value)
    if key in {"partial_shipment_allowed", "transshipment_allowed", "requires_signed_inspection",
               "requires_endorsed_bl", "amount_about"}:
        return bool(value)
    return value


def derive_governing_terms(lc: dict, amendments: list[dict], rb: Rulebook) -> tuple[GoverningTerms, tuple[str, ...], tuple[str, ...]]:
    """Return (governing terms, accepted amendment ids applied, ignored amendment ids)."""
    working = dict(lc)
    for amend in amendments:
        bad = set(amend["changes"]) - CHANGEABLE
        if bad:
            raise ValueError(f"{amend['amendment_id']}: cannot change unknown term(s) {sorted(bad)}")

    accepted = [a for a in amendments if a["acceptance_state"] == ACCEPTED]
    ignored = tuple(a["amendment_id"] for a in amendments if a["acceptance_state"] != ACCEPTED)

    # RULE-AMD-002: later effective date wins per field, so apply in ascending order.
    accepted.sort(key=lambda a: (date.fromisoformat(a["effective_date"]), a["seq"]))
    applied_ids: list[str] = []
    for amend in accepted:
        for key, value in amend["changes"].items():
            working[key] = _coerce(key, value)
        applied_ids.append(amend["amendment_id"])

    about_default = Decimal(str(rb.definitions["amount_tolerance"]["about_pct"]))
    explicit = working.get("amount_tolerance_pct")
    tolerance = None
    if explicit is not None:
        tolerance = Decimal(str(explicit))
    elif working.get("amount_about"):
        tolerance = about_default

    terms = GoverningTerms(
        credit_no=working["credit_no"],
        currency=working["currency"],
        amount=_coerce("amount", working["amount"]),
        amount_tolerance_pct=tolerance,
        amount_about=bool(working.get("amount_about", False)),
        latest_shipment=_coerce("latest_shipment", working.get("latest_shipment")),
        expiry=_coerce("expiry", working.get("expiry")),
        presentation_days=int(working["presentation_days"]) if working.get("presentation_days") is not None else None,
        port_of_loading=working["port_of_loading"],
        port_of_discharge=working["port_of_discharge"],
        consignee=working.get("consignee"),
        notify_party=working.get("notify_party"),
        partial_shipment_allowed=bool(working.get("partial_shipment_allowed", True)),
        transshipment_allowed=bool(working.get("transshipment_allowed", True)),
        goods_description=working["goods_description"],
        goods_spec=tuple(working.get("goods_spec", ())),
        commodity_class=working.get("commodity_class", "packaged"),
        quantity=_coerce("quantity", working["quantity"]),
        quantity_unit=working["quantity_unit"],
        required_docs=tuple(working["required_docs"]),
        requires_signed_inspection=bool(working.get("requires_signed_inspection", False)),
        requires_endorsed_bl=bool(working.get("requires_endorsed_bl", False)),
        stipulated_fields=frozenset(working.get("stipulated_fields", ())),
        amendments_applied=tuple(applied_ids),
        amendments_ignored=ignored,
    )
    return terms, applied_ids, ignored
