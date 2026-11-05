"""Document package model and the evidence index.

The evidence index is what makes grading traceable rather than vibes-based: every
field in every generated document has a logical name, a rendered location, a page
and a line, and the index can resolve a citation a model produced back to the field
it actually points at.

Two consequences that matter for grader reliability:

1. A finding is matched by the field its *evidence* resolves to, not by the free-text
   `field` string the model typed. A model that cites correctly but names the field
   differently is not falsely failed, and a model that names a field but cites nothing
   real cannot be credited.
2. A citation to a document_id that does not exist in the package is a fabrication,
   which is detectable at all only because the package owns the vocabulary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from datetime import date
from decimal import Decimal

from benchmark.domain import location_matches, normalize_location

# Logical document types. The credit's required-documents list uses these names.
DOC_TYPES = (
    "CREDIT",
    "AMENDMENT",
    "INVOICE",
    "PACKING_LIST",
    "BILL_OF_LADING",
    "INSURANCE_CERTIFICATE",
    "CERTIFICATE_OF_ORIGIN",
    "INSPECTION_CERTIFICATE",
    "PRESENTATION_SCHEDULE",
    "BUSINESS_CALENDAR",
    "CORRESPONDENCE",
)

UNREADABLE = "[ILLEGIBLE]"


@dataclass(frozen=True)
class FieldValue:
    """One field as it appears on one document."""

    name: str                      # logical name, e.g. "total_amount"
    label: str                      # rendered label, e.g. "Total amount"
    raw: str                        # rendered value, e.g. "USD 100,000.00"
    synonyms: tuple[str, ...] = ()  # other citation labels the grader accepts
    unreadable: bool = False
    page: int = 1
    line: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "label": self.label,
            "raw": self.raw,
            "synonyms": list(self.synonyms),
            "unreadable": self.unreadable,
            "page": self.page,
            "line": self.line,
        }


@dataclass
class Document:
    doc_id: str
    doc_type: str
    title: str
    issuer: str
    fields: dict[str, FieldValue] = dc_field(default_factory=dict)
    pages: list[str] = dc_field(default_factory=list)

    def add(self, fv: FieldValue) -> None:
        self.fields[fv.name] = fv

    def get(self, name: str) -> FieldValue | None:
        return self.fields.get(name)

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "doc_type": self.doc_type,
            "title": self.title,
            "issuer": self.issuer,
            "page_count": len(self.pages),
            "fields": {k: v.to_dict() for k, v in sorted(self.fields.items())},
        }


@dataclass(frozen=True)
class GoverningTerms:
    """The credit terms after amendment precedence has been applied.

    Derived by the truth engine, never typed, so an examiner can audit which
    amendment produced which governing value.
    """

    credit_no: str
    currency: str
    amount: Decimal
    amount_tolerance_pct: Decimal | None
    amount_about: bool
    latest_shipment: date | None
    expiry: date | None
    presentation_days: int | None
    port_of_loading: str
    port_of_discharge: str
    consignee: str | None
    notify_party: str | None
    partial_shipment_allowed: bool
    transshipment_allowed: bool
    goods_description: str
    goods_spec: tuple[str, ...]
    commodity_class: str            # "packaged" | "bulk"
    quantity: Decimal
    quantity_unit: str
    required_docs: tuple[str, ...]
    requires_signed_inspection: bool
    requires_endorsed_bl: bool
    stipulated_fields: frozenset[str]
    amendments_applied: tuple[str, ...]
    amendments_ignored: tuple[str, ...]


@dataclass
class EvidenceIndex:
    """(doc_id, citation string) -> logical field name."""

    _by_doc: dict[str, dict[str, str]] = dc_field(default_factory=dict)

    def build(self, documents: list[Document]) -> None:
        for doc in documents:
            table = self._by_doc.setdefault(doc.doc_id, {})
            for fv in doc.fields.values():
                for cand in (fv.label, *fv.synonyms, fv.name.replace("_", " ")):
                    table[normalize_location(cand)] = fv.name

    def resolve(self, doc_id: str, location: str) -> str | None:
        """Return the logical field a citation points at, or None if it points at nothing.

        Real examiners quote a location *with its value* — "Total amount: USD 105,000.00" —
        so matching only the bare label would zero the traceability dimension for every model
        that cited correctly and helpfully. That is the guide's "checks so strict they reject
        correct answers" (p.10), and a live gpt-oss trial hit it.

        Steps run strictest to loosest, and the containment step takes the longest label first
        so "Credit Amount Tolerance Condition" cannot be misread as "Credit Amount".
        """
        table = self._by_doc.get(doc_id)
        if table is None:
            return None
        norm = normalize_location(location)
        if not norm:
            return None

        if norm in table:
            return table[norm]

        head = norm.split(":", 1)[0].strip()
        if head and head in table:
            return table[head]

        squash = "".join(ch for ch in norm if ch.isalnum())
        for key, name in table.items():
            if "".join(ch for ch in key if ch.isalnum()) == squash:
                return name

        for key, name in sorted(table.items(), key=lambda kv: -len(kv[0])):
            if len(key) >= 5 and (_contains_words(key, norm) or location_matches(key, norm)):
                return name
        return None


def _contains_words(label: str, text: str) -> bool:
    """Whole-word containment, not substring containment.

    Without the boundaries, the label "marks" (a synonym for shipping marks) matched the
    invented location "Remarks" and handed that finding free traceability. A citation must
    name the label as words, not merely contain its letters.
    """
    pattern = r"\b" + re.escape(label).replace(r"\ ", r"\s+") + r"\b"
    return re.search(pattern, text) is not None

    def documents(self) -> list[str]:
        return sorted(self._by_doc)


@dataclass
class Package:
    """One examination case: the documents, the derived governing terms and the
    index that ties citations to fields."""

    case_id: str
    seed: int
    documents: list[Document]
    terms: GoverningTerms
    calendar: list[date]
    non_working_days: list[date]
    presentation_date: date | None
    shipment_date: date | None
    index: EvidenceIndex = dc_field(default_factory=EvidenceIndex)
    scenario_note: str = ""

    def __post_init__(self) -> None:
        self.index.build(self.documents)

    def docs_of(self, doc_type: str) -> list[Document]:
        return [d for d in self.documents if d.doc_type == doc_type]

    def doc(self, doc_type: str) -> Document | None:
        docs = self.docs_of(doc_type)
        return docs[0] if docs else None

    def doc_by_id(self, doc_id: str) -> Document | None:
        for d in self.documents:
            if d.doc_id == doc_id:
                return d
        return None

    def value(self, doc_type: str, name: str) -> FieldValue | None:
        d = self.doc(doc_type)
        return d.get(name) if d else None

    def document_ids(self) -> list[str]:
        return [d.doc_id for d in self.documents]

    def presented_types(self) -> set[str]:
        return {d.doc_type for d in self.documents if d.doc_type not in ("CREDIT", "AMENDMENT", "BUSINESS_CALENDAR", "CORRESPONDENCE")}

    def text_block(self) -> str:
        """The exact document text handed to the model. Deterministic ordering so a
        prompt is frozen and a rerun cannot differ because of dict order."""
        out: list[str] = []
        for doc in sorted(self.documents, key=lambda d: d.doc_id):
            out.append(f"----- {doc.doc_id} : {doc.title} -----")
            out.append(f"issuer: {doc.issuer}")
            for page_no, page in enumerate(doc.pages, start=1):
                out.append(f"[page {page_no}]")
                out.append(page.rstrip())
            out.append("")
        return "\n".join(out)

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "seed": self.seed,
            "documents": [d.to_dict() for d in sorted(self.documents, key=lambda d: d.doc_id)],
            "governing_terms": {
                k: (str(v) if isinstance(v, (Decimal, date)) else sorted(v) if isinstance(v, (tuple, frozenset, set)) else v)
                for k, v in self.terms.__dict__.items()
            },
            "presentation_date": self.presentation_date.isoformat() if self.presentation_date else None,
            "shipment_date": self.shipment_date.isoformat() if self.shipment_date else None,
            "non_working_days": [d.isoformat() for d in self.non_working_days],
        }
