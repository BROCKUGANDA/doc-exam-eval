"""The truth engine: rendered document text + rulebook -> ground truth.

Integrity properties this module is responsible for:

1. Ground truth is *computed*. A scenario states an intent, and test_scenarios.py
   asserts the engine's computed answer against that intent. If they disagree the
   benchmark is broken and the test says so — an expected answer is never pasted in
   to make a test pass.
2. Values are parsed from the same rendered text a model sees. A rendering that
   changes meaning therefore shows up as a disagreement with intent, not as a quiet
   grading difference.
3. Anything that cannot be established becomes an unresolved item — never a finding,
   never a pass. "Know when not to decide" is only gradeable because not-knowing is a
   first-class result here.
4. One observable defect yields one finding. Category rules run first; RULE-AMD-003
   only adds a finding for a field no category rule covered, so a single wrong port
   cannot be counted twice and inflate recall.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from datetime import date, timedelta
from decimal import Decimal

from benchmark.domain import (
    DateResult,
    Money,
    NotEstablished,
    Quantity,
    convert_quantity,
    money_equal,
    money_within_pct,
    normalize_location,
    parse_date,
    parse_money,
    parse_quantity,
    quantity_within_pct,
    renders_with_minor_units,
)
from benchmark.generator.documents import LABELS
from benchmark.package import UNREADABLE, Document, GoverningTerms, EvidenceIndex
from benchmark.rulebook.model import Rule, Rulebook
from benchmark.truth.terms import CHANGEABLE, ACCEPTED, derive_governing_terms

MISSING = object()
REVISED_SUFFIX = "(revised)"

# Documents that frame the examination rather than being examined.
_META_TYPES = frozenset({"CREDIT", "AMENDMENT", "PRESENTATION_SCHEDULE", "BUSINESS_CALENDAR", "CORRESPONDENCE"})

# credit field name -> governing term name, used when an amendment revises a term
TERM_BY_CREDIT_FIELD = {
    "credit_amount": "amount",
    "latest_shipment_date": "latest_shipment",
    "expiry_date": "expiry",
    "presentation_period_days": "presentation_days",
    "port_of_loading": "port_of_loading",
    "port_of_discharge": "port_of_discharge",
    "quantity": "quantity",
    "goods_description": "goods_description",
    "currency": "currency",
}

CREDIT_LABEL_BY_FIELD = {name: label for name, (label, _s) in LABELS["CREDIT"].items()}
CREDIT_FIELD_BY_LABEL = {label: name for name, (label, _s) in LABELS["CREDIT"].items()}

DOC_NAME_TO_TYPE = {
    "commercial invoice": "INVOICE",
    "packing list": "PACKING_LIST",
    "bill of lading": "BILL_OF_LADING",
    "insurance certificate": "INSURANCE_CERTIFICATE",
    "certificate of origin": "CERTIFICATE_OF_ORIGIN",
    "inspection certificate": "INSPECTION_CERTIFICATE",
}


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class EvidenceRef:
    doc_id: str
    field_name: str
    label: str
    page: int

    def to_dict(self) -> dict:
        return {"document_id": self.doc_id, "field": self.field_name, "location": self.label, "page": self.page}


@dataclass
class GroundFinding:
    code: str
    rule_id: str
    severity: str
    field: str
    docs: tuple[str, ...]
    observed: dict[str, str]
    evidence: list[EvidenceRef]
    statement: str
    finding_id: str = ""
    alias_codes: set[str] = dc_field(default_factory=set)

    @property
    def key(self) -> tuple[str, str]:
        """Stable matching key: what is wrong, about which field."""
        return (self.code, self.field)

    @property
    def codes_accepted(self) -> set[str]:
        """Every code that honestly describes this one observable defect.

        Two examiners can look at a bill of lading showing a superseded discharge port and
        call it PORT_OF_DISCHARGE_MISMATCH or DOCUMENT_CARRIES_SUPERSEDED_VALUE. Both are
        right, so both must match — otherwise the dedupe that keeps one finding per defect
        would turn a correct alternative description into a fabricated one.
        """
        return {self.code} | self.alias_codes

    def to_dict(self) -> dict:
        return {
            "finding_id": self.finding_id,
            "code": self.code,
            "alias_codes": sorted(self.alias_codes),
            "rule_id": self.rule_id,
            "severity": self.severity,
            "field": self.field,
            "documents": list(self.docs),
            "observed_values": self.observed,
            "required_evidence": [e.to_dict() for e in self.evidence],
            "statement": self.statement,
        }


@dataclass
class GroundUnresolved:
    field: str
    reason: str
    docs: tuple[str, ...]
    note: str

    @property
    def key(self) -> tuple[str, str]:
        return (self.field, self.reason)

    def to_dict(self) -> dict:
        return {"field": self.field, "reason": self.reason, "documents": list(self.docs), "note": self.note}


@dataclass
class GroundTruth:
    case_id: str
    rulebook_version: str
    terms: GoverningTerms
    findings: list[GroundFinding]
    unresolved: list[GroundUnresolved]
    acceptable_assessments: frozenset[str]
    amendments_applied: tuple[str, ...]
    amendments_ignored: tuple[str, ...]

    def critical_findings(self) -> list[GroundFinding]:
        return [f for f in self.findings if f.severity == "critical"]

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "rulebook_version": self.rulebook_version,
            "governing_terms": _terms_to_dict(self.terms),
            "amendments_applied": list(self.amendments_applied),
            "amendments_ignored": list(self.amendments_ignored),
            "acceptable_assessments": sorted(self.acceptable_assessments),
            "findings": [f.to_dict() for f in self.findings],
            "unresolved_questions": [u.to_dict() for u in self.unresolved],
        }


def _terms_to_dict(terms: GoverningTerms) -> dict:
    out = {}
    for k, v in terms.__dict__.items():
        if isinstance(v, Decimal):
            out[k] = str(v)
        elif isinstance(v, date):
            out[k] = v.isoformat()
        elif isinstance(v, (tuple, frozenset, set)):
            out[k] = sorted(v)
        else:
            out[k] = v
    return out


# ---------------------------------------------------------------------------
# Calendar arithmetic — only the supplied calendar is ever consulted
# ---------------------------------------------------------------------------
def adjust_deadline(due: date | None, non_working: frozenset[date]) -> date | None:
    if due is None:
        return None
    guard = 0
    while due in non_working:
        due += timedelta(days=1)
        guard += 1
        if guard > 30:
            raise ValueError("deadline never lands on a working day within 30 days — calendar authoring bug")
    return due


# ---------------------------------------------------------------------------
# Parsing context
# ---------------------------------------------------------------------------
@dataclass
class _Ctx:
    documents: list[Document]
    rb: Rulebook
    case_id: str
    presentation_date: date | None = None
    shipment_date: date | None = None
    non_working: frozenset[date] = frozenset()
    terms: GoverningTerms | None = None
    unresolved: list[GroundUnresolved] = dc_field(default_factory=list)
    _seen: set = dc_field(default_factory=set)
    _by_type: dict[str, list[Document]] = dc_field(default_factory=dict)

    def __post_init__(self) -> None:
        for d in self.documents:
            self._by_type.setdefault(d.doc_type, []).append(d)

    def doc(self, doc_type: str) -> Document | None:
        docs = self._by_type.get(doc_type) or []
        return docs[0] if docs else None

    def docs(self, doc_type: str) -> list[Document]:
        return self._by_type.get(doc_type, [])

    def ids(self, *types: str) -> tuple[str, ...]:
        out = []
        for t in types:
            d = self.doc(t)
            if d:
                out.append(d.doc_id)
        return tuple(out)

    def governed(self, doc_type: str) -> bool:
        """Only documents the credit requires, or that frame the examination itself,
        may generate findings or unresolved items.

        Without this gate the engine would demand an inspection certificate's date on a
        credit that never asks for one, which makes a correct CLEAR answer ungradable —
        the false-fail the Participant Guide calls out on p.9.
        """
        if doc_type in _META_TYPES:
            return True
        terms = self.terms
        return terms is not None and doc_type in tuple(terms.required_docs)

    def evidence(self, *refs: tuple[str, str]) -> list[EvidenceRef]:
        out: list[EvidenceRef] = []
        for doc_type, name in refs:
            d = self.doc(doc_type)
            fv = d.get(name) if d else None
            if fv:
                out.append(EvidenceRef(d.doc_id, name, fv.label, fv.page))
        return out

    def raw(self, doc_type: str, name: str):
        d = self.doc(doc_type)
        if d is None:
            return MISSING
        fv = d.get(name)
        return MISSING if fv is None else fv.raw

    def mark_unresolved(self, field: str, reason: str, types: tuple[str, ...], note: str) -> None:
        if types and not any(self.governed(t) for t in types):
            return
        ids = self.ids(*types)
        # A document that was never presented is one finding — DOCUMENT_MISSING — not a
        # separate "cannot be established" item for every field inside it. Without this,
        # one missing certificate would demand a dozen escalations and false-fail any
        # model that reported the absence correctly.
        if not ids:
            return
        key = (field, reason, ids)
        if key in self._seen:
            return
        self._seen.add(key)
        self.unresolved.append(GroundUnresolved(field=field, reason=reason, docs=ids, note=note))

    # ---- typed accessors: every one of them routes failure to unresolved ----
    def money(self, doc_type: str, name: str, *, field_name: str | None = None, currency: str | None = None) -> Money | None:
        raw = self.raw(doc_type, name)
        label = field_name or name
        if raw is MISSING:
            self.mark_unresolved(label, "absent", (doc_type,), f"{name} absent from {doc_type}")
            return None
        if str(raw).strip() == UNREADABLE:
            self.mark_unresolved(label, "unreadable", (doc_type,), f"{name} is marked illegible")
            return None
        try:
            return parse_money(str(raw), default_currency=currency)
        except NotEstablished as exc:
            self.mark_unresolved(label, "unreadable", (doc_type,), str(exc))
            return None

    def qty(self, doc_type: str, name: str, *, field_name: str | None = None) -> Quantity | None:
        raw = self.raw(doc_type, name)
        label = field_name or name
        if raw is MISSING:
            self.mark_unresolved(label, "absent", (doc_type,), f"{name} absent from {doc_type}")
            return None
        if str(raw).strip() == UNREADABLE:
            self.mark_unresolved(label, "unreadable", (doc_type,), f"{name} is marked illegible")
            return None
        try:
            return parse_quantity(str(raw))
        except NotEstablished as exc:
            self.mark_unresolved(label, "unreadable", (doc_type,), str(exc))
            return None

    def day(self, doc_type: str, name: str, *, field_name: str | None = None) -> date | None:
        raw = self.raw(doc_type, name)
        label = field_name or name
        if raw is MISSING:
            self.mark_unresolved(label, "absent", (doc_type,), f"{name} absent from {doc_type}")
            return None
        if str(raw).strip() == UNREADABLE:
            self.mark_unresolved(label, "unreadable", (doc_type,), f"{name} is marked illegible")
            return None
        res: DateResult = parse_date(str(raw), self.rb)
        if res.ambiguous:
            self.mark_unresolved(label, "ambiguous", (doc_type,), f"{raw!r} reads as two different calendar dates")
            return None
        if res.value is None:
            self.mark_unresolved(label, "unreadable", (doc_type,), f"{raw!r} is not a recognised date rendering")
            return None
        return res.value

    def text(self, doc_type: str, name: str, *, field_name: str | None = None) -> str | None:
        raw = self.raw(doc_type, name)
        label = field_name or name
        if raw is MISSING:
            return None
        if str(raw).strip() == UNREADABLE:
            self.mark_unresolved(label, "unreadable", (doc_type,), f"{name} is marked illegible")
            return None
        return str(raw)


# ---------------------------------------------------------------------------
# Credit and amendment parsing
# ---------------------------------------------------------------------------
def _split_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [p.strip() for p in str(raw).replace(";", ",").split(",") if p.strip()]


def _normalize(text: str) -> str:
    return normalize_location(str(text))


def _days(raw: str | None) -> str | None:
    """Credit text reads '14 days' or '21 DAYS AFTER DATE OF SHIPMENT'. The number is
    what matters; the surrounding prose is rendering."""
    if raw is None:
        return None
    m = re.search(r"\d+", str(raw))
    if not m:
        return None
    return m.group(0)


def _strict_date(raw: str | None, context: str) -> date | None:
    """Credit and amendment dates must resolve. An unreadable governing date is an
    authoring bug, not a grading outcome — if it were allowed through, the deadline
    rule would silently skip and the engine would compute a false CLEAR."""
    if raw is None or str(raw).strip() in ("", UNREADABLE):
        return None
    res = parse_date(str(raw))
    if not res.established:
        raise ValueError(f"governing date {context}={raw!r} is {res.ambiguous and 'ambiguous' or 'unparseable'}")
    return res.value


def _quantity_value(raw: str) -> str:
    return str(parse_quantity(raw).value)


def _quantity_unit(raw: str) -> str:
    return parse_quantity(raw).unit


def parse_credit(doc: Document) -> dict:
    """Read the rendered credit back into precedence-ready values."""
    if doc is None:
        raise ValueError("no CREDIT document in package")
    f = {name: fv.raw for name, fv in doc.fields.items()}

    def num(name: str) -> str:
        return str(parse_money(f[name], default_currency=f.get("currency")).amount)

    condition = normalize_location(f.get("amount_condition", ""))
    tolerance_pct = None
    about = False
    if "%" in condition:
        head = condition.split("%")[0].strip().split()[-1]
        tolerance_pct = head
    elif "about" in condition or "approximately" in condition or "circa" in condition:
        about = True

    return {
        "credit_no": f["credit_no"],
        "currency": f["currency"].strip().upper(),
        "amount": num("credit_amount"),
        "amount_tolerance_pct": tolerance_pct,
        "amount_about": about,
        "latest_shipment": _strict_date(f.get("latest_shipment_date"), "latest_shipment_date"),
        "expiry": _strict_date(f.get("expiry_date"), "expiry_date"),
        "presentation_days": _days(f.get("presentation_period_days")),
        "port_of_loading": f["port_of_loading"],
        "port_of_discharge": f["port_of_discharge"],
        "consignee": f.get("consignee_stipulated"),
        "notify_party": f.get("notify_party_stipulated"),
        "partial_shipment_allowed": str(f.get("partial_shipments", "ALLOWED")).upper() != "PROHIBITED",
        "transshipment_allowed": str(f.get("transshipment", "ALLOWED")).upper() != "PROHIBITED",
        "goods_description": f["goods_description"],
        "goods_spec": _split_list(f.get("goods_specification")),
        "commodity_class": normalize_location(f.get("commodity_class", "packaged")) or "packaged",
        "quantity": _quantity_value(f["quantity"]),
        "quantity_unit": _quantity_unit(f["quantity"]),
        "required_docs": [DOC_NAME_TO_TYPE[n] for n in (_normalize(n) for n in _split_list(f["required_documents"])) if n in DOC_NAME_TO_TYPE],
        "requires_signed_inspection": str(f.get("signature_requirement", "")).upper().startswith("SIGNED"),
        "requires_endorsed_bl": str(f.get("endorsement_requirement", "")).upper().startswith("ENDORSED"),
        "stipulated_fields": _split_list(f.get("stipulated_fields")),
    }


def parse_amendments(docs: list[Document]) -> list[dict]:
    out: list[dict] = []
    for doc in docs:
        f = {name: fv.raw for name, fv in doc.fields.items()}
        digits = re.search(r"\d+", normalize_location(f["amendment_id"]))
        entry = {
            "amendment_id": f["amendment_id"].strip(),
            "seq": int(digits.group(0)) if digits else len(out) + 1,
            "effective_date": f["effective_date"].strip(),
            "acceptance_state": f["acceptance_state"].strip().upper(),
            "changes": {},
        }
        for fv in doc.fields.values():
            if not fv.label.endswith(REVISED_SUFFIX):
                continue
            base_label = fv.label[: -len(REVISED_SUFFIX)].strip()
            credit_field = CREDIT_FIELD_BY_LABEL.get(base_label)
            if credit_field is None:
                raise ValueError(f"{entry['amendment_id']}: no credit term labelled {base_label!r}")
            term = TERM_BY_CREDIT_FIELD.get(credit_field)
            if term is None:
                raise ValueError(f"{entry['amendment_id']}: {credit_field} cannot be amended")
            entry["changes"][term] = _normalise_change(term, fv.raw, entry["amendment_id"])
        out.append(entry)
    return out


def _normalise_change(term: str, raw: str, amendment_id: str):
    try:
        if term == "amount":
            return str(parse_money(raw).amount)
        if term == "quantity":
            return _quantity_value(raw)
        if term in {"latest_shipment", "expiry"}:
            return _strict_date(raw, f"amendment {term}")
        if term == "presentation_days":
            return _days(raw)
        if term == "currency":
            return raw.strip().upper()
    except NotEstablished as exc:
        raise ValueError(f"{amendment_id}: cannot read amended {term} from {raw!r}") from exc
    return raw


def build_terms(rb: Rulebook, credit_doc: Document, amendment_docs: list[Document]):
    base = parse_credit(credit_doc)
    amendments = parse_amendments(amendment_docs)
    terms, applied, ignored = derive_governing_terms(base, amendments, rb)
    history = _supersession_history(base, amendments, applied, rb)
    return terms, applied, ignored, history


def _supersession_history(base: dict, amendments: list[dict], applied: list[str], rb: Rulebook) -> dict[str, list[str]]:
    """term -> every value that used to govern it and no longer does.

    This is what lets RULE-AMD-003 recognise a document that still carries an old
    value, instead of only noticing that it differs from the governing one.
    """
    history: dict[str, list[str]] = {}
    current = {k: v for k, v in base.items() if k in CHANGEABLE}
    accepted = sorted(
        [a for a in amendments if a["acceptance_state"] == ACCEPTED],
        key=lambda a: (date.fromisoformat(a["effective_date"]), a["seq"]),
    )
    for amend in accepted:
        for term, value in amend["changes"].items():
            previous = current.get(term)
            if previous is not None and str(previous) != str(value):
                history.setdefault(term, []).append(str(previous))
            current[term] = value
    for amend in amendments:
        if amend["acceptance_state"] != ACCEPTED:
            for term, value in amend["changes"].items():
                history.setdefault(term, []).append(str(value))
    return {term: sorted(set(vals)) for term, vals in history.items()}
