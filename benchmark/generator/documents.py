"""Deterministic rendering of synthetic trade documents.

A document is a list of labelled lines chunked into pages. Page and line numbers are
read back out of the rendered text rather than declared by the caller, so the evidence
index cannot claim a field is on page 2 when the rendered document puts it on page 1 —
which is precisely the kind of grader-reliability bug that would let a correct citation
fail or an invented one pass.
"""

from __future__ import annotations

from dataclasses import dataclass

from benchmark.package import UNREADABLE, Document, FieldValue

# field_name -> (rendered label, extra citation labels the grader accepts)
LAYOUTS: dict[str, list[tuple[str, str, tuple[str, ...]]]] = {
    "CREDIT": [
        ("credit_no", "Documentary Credit No.", ("LC No", "L/C Number", "Credit Number")),
        ("issue_date", "Issue Date", ("Date of Issue")),
        ("currency", "Currency", ("CCY",)),
        ("credit_amount", "Credit Amount", ("Amount", "Amount of Credit")),
        ("amount_words", "Amount in Words", ()),
        ("amount_condition", "Amount Tolerance Condition", ("Tolerance",)),
        ("latest_shipment_date", "Latest Date of Shipment", ("Last Shipment Date", "Latest Shipment")),
        ("expiry_date", "Date of Expiry", ("Expiry Date", "Validity of Credit")),
        ("presentation_period_days", "Presentation Period After Shipment", ("Presentation Days",)),
        ("port_of_loading", "Port of Loading", ("Loading Port",)),
        ("port_of_discharge", "Port of Discharge", ("Discharge Port", "Destination Port")),
        ("goods_description", "Description of Goods", ("Goods", "Description")),
        ("goods_specification", "Goods Specification", ("Specification",)),
        ("quantity", "Quantity", ("Quantity of Goods",)),
        ("commodity_class", "Commodity Class", ("Goods Class",)),
        ("partial_shipments", "Partial Shipments", ("Partial Shipment",)),
        ("transshipment", "Transshipment", ("Transhipment",)),
        ("drawing_limit", "Drawing Limit Condition", ("Partial Drawing",)),
        ("required_documents", "Required Documents", ("Documents Required",)),
        ("signature_requirement", "Signature Requirement", ("Signing",)),
        ("endorsement_requirement", "Endorsement Requirement", ("Endorsement",)),
        ("stipulated_fields", "Stipulated Fields", ("Fields Stipulated by this Credit",)),
        ("consignee_stipulated", "Consignee Stipulated", ("Stipulated Consignee",)),
        ("notify_party_stipulated", "Notify Party Stipulated", ("Stipulated Notify Party",)),
        ("applicant", "Applicant", ("Buyer",)),
        ("beneficiary", "Beneficiary", ("Seller",)),
        ("beneficiary_address", "Beneficiary Address", ("Seller Address",)),
        ("issuing_bank", "Issuing Bank", ()),
        ("advising_bank", "Advising Bank", ()),
    ],
    "AMENDMENT": [
        ("amendment_id", "Amendment No.", ("Amendment Number", "Amd No")),
        ("amendment_date", "Date of Amendment", ("Issued Date",)),
        ("effective_date", "Effective Date", ("Date Effective",)),
        ("acceptance_state", "Acceptance State", ("Accepted", "Status")),
        ("changed_terms", "Terms Changed", ("Changes",)),
        ("acknowledgement", "Acknowledgement", ()),
    ],
    "INVOICE": [
        ("invoice_no", "Invoice No.", ("Commercial Invoice Number", "Inv No")),
        ("invoice_date", "Invoice Date", ("Date",)),
        ("invoice_no_ref", "T.T.R. No.", ("Trade Reference", "TTR No", "Transaction Reference")),
        ("beneficiary_name", "Beneficiary", ("Seller", "Exporter")),
        ("beneficiary_address", "Beneficiary Address", ("Seller Address",)),
        ("applicant_name", "Applicant", ("Buyer", "Consignee Company")),
        ("goods_description", "Description of Goods", ("Goods", "Description")),
        ("quantity", "Quantity", ("Quantity Shipped",)),
        ("unit_price", "Unit Price", ("Rate",)),
        ("freight_amount", "Freight Charged", ("Freight",)),
        ("total_amount", "Total amount", ("Invoice Total", "Amount Claimed", "Total")),
        ("currency", "Currency", ("CCY",)),
        ("trade_terms", "Delivery Terms", ("Incoterms", "Term of Delivery")),
        ("shipping_marks", "Shipping Marks", ("Marks",)),
        ("declaration", "Declaration", ()),
    ],
    "PACKING_LIST": [
        ("packing_list_no", "Packing List No.", ("P/L No",)),
        ("packing_list_date", "Date", ("Packing List Date",)),
        ("goods_description", "Description of Goods", ("Goods",)),
        ("cartons", "Number of Cartons", ("Cartons", "Packages")),
        ("pieces_per_carton", "Pieces per Carton", ("Pcs/Ctn",)),
        ("total_pieces", "Total Pieces", ("Total Quantity", "Pieces")),
        ("net_weight", "Net Weight", ("N.W.", "Net Wt")),
        ("gross_weight", "Gross Weight", ("G.W.", "Gross Wt")),
        ("shipping_marks", "Shipping Marks", ("Marks and Numbers",)),
        ("measurement", "Measurement", ("Volume",)),
    ],
    "BILL_OF_LADING": [
        ("bl_no", "Bill of Lading No.", ("B/L No", "BL Number")),
        ("bl_date", "Date of Issue", ("Issue Date",)),
        ("vessel", "Vessel / Voyage", ("Vessel", "Ship")),
        ("port_of_loading", "Port of Loading", ("Loading Port", "Port of Receipt")),
        ("port_of_discharge", "Port of Discharge", ("Discharge Port", "Port of Delivery")),
        ("consignee", "Consignee", ("To Order of",)),
        ("notify_party", "Notify Party", ("Notify",)),
        ("on_board_date", "On Board Date", ("Date On Board", "Shipment Date")),
        ("goods_description", "Description of Goods", ("Particulars Furnished by Shipper",)),
        ("shipped_quantity", "Quantity Shipped", ("Quantity",)),
        ("shipping_marks", "Shipping Marks", ("Marks and Numbers",)),
        ("freight_terms", "Freight Terms", ("Freight",)),
        ("transshipment_indicator", "Transshipment at Transit Port", ("Transhipment",)),
        ("endorsement_state", "Negotiation / Endorsement", ("Endorsement",)),
        ("carrier_name", "Carrier", ("Issued by",)),
        ("signed_by", "Signed By", ("Signature", "Signed")),
    ],
    "INSURANCE_CERTIFICATE": [
        ("insurance_no", "Insurance Certificate No.", ("Policy No", "Certificate No")),
        ("issue_date", "Date of Issue", ("Issue Date",)),
        ("assured", "Assured", ("Insured Party",)),
        ("currency", "Currency", ("CCY",)),
        ("insured_amount", "Insured Amount", ("Sum Insured", "Amount Insured")),
        ("coverage", "Coverage", ("Conditions", "Risk Covered")),
        ("voyage", "Vessel and Voyage", ("Vessel",)),
        ("claims_payable_at", "Claims Payable At", ("Claims Payable",)),
    ],
    "CERTIFICATE_OF_ORIGIN": [
        ("coo_no", "Certificate of Origin No.", ("C of O No",)),
        ("issue_date", "Date of Issue", ("Issue Date",)),
        ("consignor", "Consignor", ("Exporter",)),
        ("consignee", "Consignee", ("To",)),
        ("goods_description", "Description of Goods", ("Goods",)),
        ("origin_country", "Country of Origin", ("Origin",)),
        ("certificate_issuer", "Certifying Body", ("Issued By",)),
        ("signed_by", "Signed By", ("Signature",)),
    ],
    "INSPECTION_CERTIFICATE": [
        ("inspection_no", "Inspection Certificate No.", ("Certificate No",)),
        ("issue_date", "Date of Issue", ("Issue Date",)),
        ("quantity_certified", "Quantity Certified", ("Quantity",)),
        ("quality_statement", "Quality Finding", ("Quality", "Result")),
        ("valid_until", "Valid Until", ("Expiry of Certificate", "Validity")),
        ("certificate_issuer", "Inspecting Body", ("Issued By",)),
        ("signed_by", "Signed By", ("Signature", "Signed by")),
        ("test_reference", "Test Reference No.", ("Reference",)),
    ],
    "PRESENTATION_SCHEDULE": [
        ("presentation_date", "Date of Presentation", ("Presented On",)),
        ("presenting_bank", "Presented By", ("Negotiating Bank",)),
        ("documents_lodged", "Documents Lodged", ("Enclosures", "List of Documents")),
        ("covering_reference", "Covering Reference", ("Our Ref",)),
        ("credit_no", "Credit Reference", ("LC No",)),
    ],
    "BUSINESS_CALENDAR": [
        ("calendar_title", "Calendar Reference", ("Business Calendar",)),
        ("working_days_note", "Working Days", ("Business Days",)),
        ("non_working_days", "Non-Working Days in Period", ("Holidays", "Closed Dates")),
    ],
    "CORRESPONDENCE": [
        ("message_date", "Date", ("Message Date",)),
        ("subject", "Subject", ("Re",)),
        ("from_party", "From", ()),
        ("message_body", "Message", ("Body", "Text")),
    ],
}

LABELS: dict[str, dict[str, tuple[str, tuple[str, ...]]]] = {
    doc_type: {name: (label, syn) for name, label, syn in rows}
    for doc_type, rows in LAYOUTS.items()
}


@dataclass
class RenderedField:
    name: str
    raw: str
    unreadable: bool


def render_document(
    doc_id: str,
    doc_type: str,
    title: str,
    issuer: str,
    values: dict[str, object],
    *,
    lines_per_page: int = 26,
    footer: tuple[str, ...] = (),
    extra_layout: tuple[tuple[str, str, tuple[str, ...]], ...] = (),
) -> Document:
    """Render `values` into pages and derive each field's page/line from the result.

    A field absent from `values` is absent from the document — that is how the engine
    later distinguishes "not established" from "established as something else".

    `extra_layout` carries per-instance fields that are not part of the static layout,
    which is how an amendment names whichever credit terms it revises.
    """
    layout = dict(LABELS.get(doc_type) or {})
    if not layout:
        raise KeyError(f"no layout for doc_type {doc_type!r}")
    order = [name for name, _label, _syn in LAYOUTS[doc_type]]
    for name, label, synonyms in extra_layout:
        layout[name] = (label, synonyms)
        order.append(name)

    lines: list[str] = [f"{title}", f"issued by {issuer}", ""]
    placements: dict[str, int] = {}

    for name in order:
        if name not in values:
            continue
        label, synonyms = layout[name]
        text = str(values[name])
        lines.append(f"{label}: {text}")
        placements[name] = len(lines) - 1

    for extra in footer:
        lines.append(extra)

    pages: list[str] = []
    for start in range(0, len(lines), lines_per_page):
        pages.append("\n".join(lines[start : start + lines_per_page]))

    doc = Document(doc_id=doc_id, doc_type=doc_type, title=title, issuer=issuer, pages=pages)
    for name, line_index in placements.items():
        page_no = line_index // lines_per_page + 1
        line_no = line_index % lines_per_page + 1
        label, synonyms = layout[name]
        raw = values[name]
        doc.add(
            FieldValue(
                name=name,
                label=label,
                raw=str(raw),
                synonyms=synonyms,
                unreadable=str(raw).strip() == UNREADABLE,
                page=page_no,
                line=line_no,
            )
        )
    return doc


def page_of(document: Document, field_name: str) -> int:
    fv = document.get(field_name)
    if fv is None:
        raise KeyError(f"{document.doc_id} has no field {field_name}")
    return fv.page
