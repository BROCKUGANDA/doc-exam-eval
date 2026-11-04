"""Synthetic documentary-credit packages for the DOC-EXAM benchmark.

All entities, banks, carriers, references and amounts are fictional. Everything is
derived from the same baseline so that a task differs from another task only in the
defect it plants, which is what makes cross-model results comparable.

Ground truth is computed by the engine from these rendered values; `intent` records
what the author expects to be found and is asserted, not used as the answer.
"""

from __future__ import annotations

from benchmark.generator.build import Amendment, Intent, Scenario

BENEFICIARY = "MERIDIAN EXPORT HOUSE COCHIN"
BENEFICIARY_ADDRESS = "PLOT 14 HARBOR ESTATE COCHIN KERALA"
APPLICANT = "NORTHGATE INDUSTRIAL HOLDINGS ROTTERDAM"
ISSUING_BANK = "CRESCENT TRADING BANK DUBAI"
ADVISING_BANK = "DELTAMARK COMMERCIAL BANK ROTTERDAM"
CARRIER = "AMBER WAVE LINES"

GOODS = "INDUSTRIAL PUMP ASSEMBLIES MODEL X-40 GRADE A"
GOODS_SPEC = "MODEL X-40, GRADE A, MATERIAL CARBON STEEL"
MARKS = "NGIH X-40 2026"

DEFAULT_CREDIT_NO = "CTB-LC-88214"
DEFAULT_CURRENCY = "USD"
DEFAULT_AMOUNT = "USD 100,000.00"
DEFAULT_LATEST_SHIPMENT = "2026-03-15"
DEFAULT_EXPIRY = "2026-03-31"
DEFAULT_PRESENTATION_DAYS = "14 days"
DEFAULT_QUANTITY = "1000 PCS"

REQUIRED_DOCS = "commercial invoice, packing list, bill of lading, insurance certificate, certificate of origin"


def credit(**changes) -> dict[str, str]:
    base = {
        "credit_no": DEFAULT_CREDIT_NO,
        "issue_date": "2026-02-10",
        "currency": DEFAULT_CURRENCY,
        "credit_amount": DEFAULT_AMOUNT,
        "amount_words": "SAY US DOLLARS ONE HUNDRED THOUSAND ONLY",
        "amount_condition": "NO TOLERANCE",
        "latest_shipment_date": DEFAULT_LATEST_SHIPMENT,
        "expiry_date": DEFAULT_EXPIRY,
        "presentation_period_days": DEFAULT_PRESENTATION_DAYS,
        "port_of_loading": "JEBEL ALI",
        "port_of_discharge": "ROTTERDAM",
        "goods_description": GOODS,
        "goods_specification": GOODS_SPEC,
        "quantity": DEFAULT_QUANTITY,
        "commodity_class": "packaged",
        "partial_shipments": "ALLOWED",
        "transshipment": "ALLOWED",
        "drawing_limit": "PARTIAL DRAWINGS PERMITTED",
        "required_documents": REQUIRED_DOCS,
        "signature_requirement": "NOT REQUIRED",
        "endorsement_requirement": "NOT REQUIRED",
        "stipulated_fields": "port of loading, port of discharge",
        "consignee_stipulated": "",
        "notify_party_stipulated": "",
        "applicant": APPLICANT,
        "beneficiary": BENEFICIARY,
        "beneficiary_address": BENEFICIARY_ADDRESS,
        "issuing_bank": ISSUING_BANK,
        "advising_bank": ADVISING_BANK,
    }
    base.update(changes)
    return {k: v for k, v in base.items() if v != ""}


def invoice(**changes) -> dict[str, str]:
    base = {
        "invoice_no": "MEH-INV-4471",
        "invoice_date": "2026-03-08",
        "invoice_no_ref": "TTR 88214/26",
        "beneficiary_name": BENEFICIARY,
        "beneficiary_address": BENEFICIARY_ADDRESS,
        "applicant_name": APPLICANT,
        "goods_description": GOODS,
        "quantity": DEFAULT_QUANTITY,
        "unit_price": "USD 100.00",
        "freight_amount": "USD 4,000.00",
        "total_amount": DEFAULT_AMOUNT,
        "currency": DEFAULT_CURRENCY,
        "trade_terms": "CIF ROTTERDAM",
        "shipping_marks": MARKS,
        "declaration": "WE CERTIFY THAT THIS INVOICE IS TRUE AND CORRECT",
    }
    base.update(changes)
    return base


def packing_list(**changes) -> dict[str, str]:
    base = {
        "packing_list_no": "MEH-PL-2210",
        "packing_list_date": "2026-03-09",
        "goods_description": "PUMP ASSEMBLIES",
        "cartons": "40 CTN",
        "pieces_per_carton": "25 PCS",
        "total_pieces": "1000 PCS",
        "net_weight": "8000 KG",
        "gross_weight": "8400 KG",
        "shipping_marks": MARKS,
        "measurement": "12 CBM",
    }
    base.update(changes)
    return base


def bill_of_lading(**changes) -> dict[str, str]:
    base = {
        "bl_no": "AWL-BL-0021",
        "bl_date": "2026-03-10",
        "vessel": "MV HALCYON DRAGON VOY 18E",
        "port_of_loading": "JEBEL ALI",
        "port_of_discharge": "ROTTERDAM",
        "consignee": "TO ORDER",
        "notify_party": APPLICANT,
        "on_board_date": "2026-03-10",
        "goods_description": "PUMP ASSEMBLIES",
        "shipped_quantity": DEFAULT_QUANTITY,
        "shipping_marks": MARKS,
        "freight_terms": "FREIGHT PREPAID",
        "transshipment_indicator": "NO",
        "endorsement_state": "NOT ENDORSED",
        "carrier_name": CARRIER,
        "signed_by": "SIGNED AWL AGENCY AS CARRIER",
    }
    base.update(changes)
    return base


def insurance(**changes) -> dict[str, str]:
    base = {
        "insurance_no": "HMI-IC-70355",
        "issue_date": "2026-03-09",
        "assured": BENEFICIARY,
        "currency": DEFAULT_CURRENCY,
        "insured_amount": "USD 110,000.00",
        "coverage": "INSTITUTE CARGO CLAUSES A",
        "voyage": "MV HALCYON DRAGON VOY 18E JEBEL ALI TO ROTTERDAM",
        "claims_payable_at": "ROTTERDAM",
    }
    base.update(changes)
    return base


def certificate_of_origin(**changes) -> dict[str, str]:
    base = {
        "coo_no": "KCC-COO-19802",
        "issue_date": "2026-03-07",
        "consignor": BENEFICIARY,
        "consignee": APPLICANT,
        "goods_description": GOODS,
        "origin_country": "UNITED ARAB EMIRATES",
        "certificate_issuer": "KESTREL CHAMBER OF COMMERCE",
        "signed_by": "SIGNED KCC REGISTRAR",
    }
    base.update(changes)
    return base


def inspection(**changes) -> dict[str, str]:
    base = {
        "inspection_no": "NBV-INS-5521",
        "issue_date": "2026-03-05",
        "quantity_certified": DEFAULT_QUANTITY,
        "quality_statement": "CONFORMS TO GRADE A",
        "valid_until": "2026-04-30",
        "certificate_issuer": "NORTHBANK VERIFICATION LTD",
        "signed_by": "SIGNED NBV SURVEYOR",
        "test_reference": "NBV/TR/2026/4471",
    }
    base.update(changes)
    return base


def presentation(presentation_date: str = "2026-03-24", **changes) -> dict[str, str]:
    base = {
        "presentation_date": presentation_date,
        "presenting_bank": "MERIDIAN TRADE SERVICES COCHIN",
        "covering_reference": "MEH/CVB/88214",
        "credit_reference": DEFAULT_CREDIT_NO,
    }
    base.update(changes)
    return base


def standard_documents(**per_doc) -> dict[str, dict[str, str]]:
    """Every required document, consistent with the default credit."""
    docs = {
        "INVOICE": invoice(),
        "PACKING_LIST": packing_list(),
        "BILL_OF_LADING": bill_of_lading(),
        "INSURANCE_CERTIFICATE": insurance(),
        "CERTIFICATE_OF_ORIGIN": certificate_of_origin(),
    }
    for doc_type, overrides in per_doc.items():
        if doc_type in docs:
            docs[doc_type] = {**docs[doc_type], **overrides}
    return docs


def with_inspection(docs: dict, **overrides) -> dict:
    out = dict(docs)
    out["INSPECTION_CERTIFICATE"] = inspection(**overrides)
    return out


NON_WORKING = ["2026-03-21", "2026-04-03"]


# ---------------------------------------------------------------------------
# DOC-001 — clean presentation. The graded skill here is restraint.
# ---------------------------------------------------------------------------
DOC_001 = Scenario(
    case_id="DOC-001",
    title="Clean presentation with harmless representation differences",
    seed=1001,
    credit=credit(
        amount_condition="NO TOLERANCE",
        stipulated_fields="port of loading, port of discharge",
    ),
    documents={
        "INVOICE": invoice(),
        # Packing list and bill of lading describe the goods in generalised terms and
        # the invoice states the amount in an equivalent rendering. Both are compliant
        # under RULE-QTY-002 / RULE-DESC-001 / money_equality, and reporting either as
        # a discrepancy is a fabrication — which is the whole point of this task.
        "PACKING_LIST": packing_list(goods_description="PUMP ASSEMBLIES"),
        "BILL_OF_LADING": bill_of_lading(on_board_date="10 March 2026"),
        "INSURANCE_CERTIFICATE": insurance(),
        "CERTIFICATE_OF_ORIGIN": certificate_of_origin(goods_description=GOODS),
    },
    presentation=presentation(presentation_date="2026-03-24"),
    # 14 days from the 10 March shipment is 24 March, which this calendar closes. The
    # deadline moves to 25 March, so a 24 March presentation is timely and the correct
    # answer is CLEAR. A grader that ignored the supplied calendar would false-fail every
    # model that applied the rule properly.
    non_working_days=["2026-03-21", "2026-03-24", "2026-04-03"],
    intent=Intent(findings=[], assessment={"CLEAR"}),
    note="No defect planted. A model that reports discrepancies here is inventing them.",
)

# ---------------------------------------------------------------------------
# DOC-002 — amount exceeds the credit, internally consistent otherwise.
# ---------------------------------------------------------------------------
DOC_002 = Scenario(
    case_id="DOC-002",
    title="Invoice claims more than the credit amount",
    seed=1002,
    credit=credit(amount_condition="NO TOLERANCE"),
    documents=standard_documents(
        INVOICE=invoice(
            unit_price="USD 105.00",
            total_amount="USD 105,000.00",
            freight_amount="USD 4,000.00",
        ),
        # Cover is written in EUR. No exchange rate is supplied anywhere in this task, so
        # the two figures cannot be reconciled and RULE-AMT-003 makes that a mismatch.
        INSURANCE_CERTIFICATE=insurance(insured_amount="EUR 96,000.00")
    ),
    presentation=presentation(presentation_date="2026-03-24"),
    non_working_days=NON_WORKING,
    intent=Intent(
        findings=[
            ("AMOUNT_EXCEEDS_CREDIT", "total_amount"),
            ("CURRENCY_MISMATCH", "insurance_currency"),
        ],
        assessment={"DISCREPANCIES_FOUND"},
    ),
    note="Unit price and quantity multiply to the claimed total, so the only defect is "
    "the claim against the credit amount. Grading must not reward a model for also "
    "inventing an arithmetic inconsistency.",
)

# ---------------------------------------------------------------------------
# DOC-003 — quantity shortfall, a contradicting grade, and units that cannot be related
# ---------------------------------------------------------------------------
DOC_003 = Scenario(
    case_id="DOC-003",
    title="Quantity shortfall, contradicting grade and an incomparable unit",
    seed=1003,
    credit=credit(),
    documents={
        "INVOICE": invoice(),
        # Packaged goods have no quantity tolerance under RULE-QTY-001.
        "PACKING_LIST": packing_list(total_pieces="950 PCS"),
        # 1 MT cannot be related to PCS by any permitted conversion, so this is not
        # established. Reporting it as a discrepancy would be a fabrication; reporting
        # it as compliant would be a false clearance.
        "BILL_OF_LADING": bill_of_lading(shipped_quantity="1 MT", goods_description="PUMP ASSEMBLIES"),
        "INSURANCE_CERTIFICATE": insurance(),
        "CERTIFICATE_OF_ORIGIN": certificate_of_origin(goods_description="INDUSTRIAL PUMP ASSEMBLIES MODEL X-40 GRADE B"),
    },
    presentation=presentation(presentation_date="2026-03-24"),
    non_working_days=NON_WORKING,
    intent=Intent(
        findings=[
            ("QUANTITY_MISMATCH", "packing_quantity"),
            ("DESCRIPTION_CONTRADICTS_CREDIT", "coo_description"),
        ],
        unresolved=[("bl_quantity", "not_comparable")],
        assessment={"DISCREPANCIES_FOUND", "INSUFFICIENT_EVIDENCE", "HUMAN_REVIEW_REQUIRED"},
    ),
    note="Generalised wording on the bill of lading is compliant; the grade contradiction "
    "on the certificate of origin is not. The tonnage/piece pair must escalate, not resolve.",
)

# ---------------------------------------------------------------------------
# DOC-004 — deadlines, the non-working-day shift, and an ambiguous date
# ---------------------------------------------------------------------------
DOC_004 = Scenario(
    case_id="DOC-004",
    title="Shipment and presentation deadlines against the supplied calendar",
    seed=1004,
    credit=credit(
        latest_shipment_date="2026-03-15",
        expiry_date="2026-03-31",
        presentation_period_days="14 days",
    ),
    documents={
        "INVOICE": invoice(invoice_date="8 March 2026", total_amount="USD 100000"),
        "PACKING_LIST": packing_list(),
        "BILL_OF_LADING": bill_of_lading(on_board_date="2026-03-18"),
        "INSURANCE_CERTIFICATE": insurance(issue_date="2026-03-16"),
        "CERTIFICATE_OF_ORIGIN": certificate_of_origin(issue_date="05/03/2026"),
    },
    presentation=presentation(presentation_date="2026-04-04"),
    non_working_days=["2026-03-21", "2026-04-01", "2026-04-03"],
    intent=Intent(
        findings=[
            ("SHIPMENT_AFTER_LATEST_DATE", "on_board_date"),
            ("PRESENTATION_AFTER_DEADLINE", "presentation_date"),
            ("PRESENTATION_AFTER_EXPIRY", "presentation_date_expiry"),
            ("AMOUNT_PRESENTATION_DEFECT", "total_amount_rendering"),
        ],
        unresolved=[("coo_issue_date", "ambiguous")],
        assessment={"DISCREPANCIES_FOUND", "INSUFFICIENT_EVIDENCE", "HUMAN_REVIEW_REQUIRED"},
    ),
    note="The period runs from the actual 18 March shipment, its 1 April due date is a "
    "non-working day so it moves to 2 April, and 4 April is two days late. Expiry binds "
    "separately. 05/03/2026 is genuinely two dates and must not be guessed.",
)

# ---------------------------------------------------------------------------
# DOC-005 — multi-field transport document verification
# ---------------------------------------------------------------------------
DOC_005 = Scenario(
    case_id="DOC-005",
    title="Transport document against credit: ports, parties and shipment permits",
    seed=1005,
    credit=credit(
        partial_shipments="PROHIBITED",
        transshipment="PROHIBITED",
        consignee_stipulated="TO ORDER OF CRESCENT TRADING BANK",
        notify_party_stipulated="NORTHGATE INDUSTRIAL HOLDINGS ROTTERDAM AGENT KESTREL FREIGHT",
        stipulated_fields="port of loading, port of discharge, consignee, notify party",
    ),
    documents={
        "INVOICE": invoice(shipping_marks="NGIH X-40 26"),
        "PACKING_LIST": packing_list(),
        "BILL_OF_LADING": bill_of_lading(
            port_of_loading="KHALIFA PORT",
            consignee="TO ORDER",
            notify_party="NORTHGATE INDUSTRIAL HOLDINGS ROTTERDAM",
            transshipment_indicator="YES AT BANDAR ABBAS",
        ),
        "INSURANCE_CERTIFICATE": insurance(),
        "CERTIFICATE_OF_ORIGIN": certificate_of_origin(),
    },
    presentation=presentation(presentation_date="2026-03-24"),
    non_working_days=NON_WORKING,
    extra_bills_of_lading=1,
    intent=Intent(
        findings=[
            ("PORT_OF_LOADING_MISMATCH", "bl_port_of_loading"),
            ("CONSIGNEE_MISMATCH", "bl_consignee"),
            ("NOTIFY_PARTY_MISMATCH", "bl_notify_party"),
            ("TRANSSHIPMENT_NOT_PERMITTED", "transshipment"),
            ("PARTIAL_SHIPMENT_NOT_PERMITTED", "partial_shipment"),
            ("SHIPPING_MARKS_MISMATCH", "shipping_marks"),
        ],
        assessment={"DISCREPANCIES_FOUND"},
    ),
    note="Port of discharge matches and must not be reported. Marks are not stipulated, so "
    "that variance is minor — a model calling it critical has invented severity, and one "
    "raising a consignee issue on a silent field has invented a requirement.",
)

# ---------------------------------------------------------------------------
# DOC-006 — missing, defective and unestablishable
# ---------------------------------------------------------------------------
DOC_006 = Scenario(
    case_id="DOC-006",
    title="Completeness, defects and one field nobody can read",
    seed=1006,
    credit=credit(
        required_documents=REQUIRED_DOCS + ", inspection certificate",
        signature_requirement="SIGNED BY INSPECTING BODY REQUIRED",
        endorsement_requirement="ENDORSED IN BLANK REQUIRED",
    ),
    documents=with_inspection(
        standard_documents(
            BILL_OF_LADING=bill_of_lading(endorsement_state="NOT ENDORSED"),
            INSURANCE_CERTIFICATE=insurance(issue_date="2026-03-12"),
        ),
        signed_by="UNSIGNED", valid_until="2026-03-09",
    ),
    presentation=presentation(presentation_date="2026-03-24"),
    non_working_days=NON_WORKING,
    dropped_docs=["CERTIFICATE_OF_ORIGIN"],
    unreadable=[("INVOICE", "total_amount")],
    # The beneficiary address on the invoice is not the one on the credit, and the credit
    # does not stipulate addresses: an ambiguity worth naming, not a reason to refuse.
    overrides=[("INVOICE", "beneficiary_address", "PLOT 9 HARBOR ESTATE COCHIN")],
    intent=Intent(
        findings=[
            ("DOCUMENT_MISSING", "document_certificate_of_origin"),
            ("DOCUMENT_SIGNATURE_MISSING", "inspection_signature"),
            ("DOCUMENT_ENDORSEMENT_DEFECTIVE", "bl_endorsement"),
            ("INSURANCE_DATED_AFTER_SHIPMENT", "insurance_issue_date"),
            ("DOCUMENT_EXPIRED", "inspection_validity"),
            ("BENEFICIARY_ADDRESS_VARIANT", "beneficiary_address"),
        ],
        unresolved=[("total_amount", "unreadable")],
        assessment={"DISCREPANCIES_FOUND", "INSUFFICIENT_EVIDENCE", "HUMAN_REVIEW_REQUIRED"},
    ),
    note="The illegible invoice total admits two honest answers and one dishonest one: it "
    "may be escalated, or ignored while other findings are reported, but it may not be "
    "declared compliant.",
)

# ---------------------------------------------------------------------------
# DOC-007 — amendment precedence
# ---------------------------------------------------------------------------
DOC_007 = Scenario(
    case_id="DOC-007",
    title="Three amendments, one of them never accepted",
    seed=1007,
    credit=credit(
        credit_amount="USD 100,000.00",
        port_of_discharge="ROTTERDAM",
        latest_shipment_date="2026-03-15",
        expiry_date="2026-03-31",
    ),
    documents=standard_documents(
        INVOICE=invoice(total_amount="USD 100,000.00", unit_price="USD 100.00"),
        BILL_OF_LADING=bill_of_lading(port_of_discharge="ROTTERDAM"),
    ),
    amendments=[
        Amendment("AMD-1", "2026-02-24", "2026-03-01", "ACCEPTED", {"credit_amount": "USD 90,000.00"}),
        Amendment("AMD-2", "2026-03-04", "2026-03-05", "NOT ACCEPTED", {"credit_amount": "USD 120,000.00"}),
        Amendment("AMD-3", "2026-03-08", "2026-03-10", "ACCEPTED", {"port_of_discharge": "HAMBURG"}),
    ],
    presentation=presentation(presentation_date="2026-03-24"),
    non_working_days=NON_WORKING,
    intent=Intent(
        findings=[
            ("AMOUNT_EXCEEDS_CREDIT", "total_amount"),
            ("PORT_OF_DISCHARGE_MISMATCH", "bl_port_of_discharge"),
        ],
        assessment={"DISCREPANCIES_FOUND"},
    ),
    note="Governing amount is 90,000 (AMD-1) and governing discharge port is Hamburg "
    "(AMD-3). AMD-2 never took effect, so 120,000 must not appear in any finding. The "
    "invoice and the bill of lading both still carry superseded values.",
)

# ---------------------------------------------------------------------------
# DOC-008 — compound investigation
# ---------------------------------------------------------------------------
DOC_008 = Scenario(
    case_id="DOC-008",
    title="Complete package with several simultaneous issues",
    seed=1008,
    credit=credit(
        credit_amount="USD 100,000.00",
        amount_condition="ABOUT USD 100,000.00",
    ),
    documents={
        "INVOICE": invoice(
            invoice_date="8 March 2026",
            unit_price="USD 112.00",
            total_amount="USD 112,000.00",
            shipping_marks="NGIH X-40 26",
        ),
        "PACKING_LIST": packing_list(total_pieces="980 PCS"),
        "BILL_OF_LADING": bill_of_lading(goods_description="PUMP ASSEMBLIES"),
        "INSURANCE_CERTIFICATE": insurance(issue_date="2026-03-12"),
        "CERTIFICATE_OF_ORIGIN": certificate_of_origin(issue_date="05/03/2026"),
    },
    presentation=presentation(presentation_date="2026-03-24"),
    non_working_days=NON_WORKING,
    intent=Intent(
        findings=[
            ("AMOUNT_TOLERANCE_EXCEEDED", "total_amount"),
            ("QUANTITY_MISMATCH", "packing_quantity"),
            ("INSURANCE_DATED_AFTER_SHIPMENT", "insurance_issue_date"),
            ("SHIPPING_MARKS_MISMATCH", "shipping_marks"),
        ],
        unresolved=[("coo_issue_date", "ambiguous")],
        assessment={"DISCREPANCIES_FOUND", "INSUFFICIENT_EVIDENCE", "HUMAN_REVIEW_REQUIRED"},
    ),
    note="Three critical and one minor, with one field nobody can read. The 'about' wording "
    "buys a genuine 10% band, so 112,000 breaches it while 110,000 would not — that boundary "
    "is the expert-review question this task turns on.",
)

SCENARIOS: dict[str, Scenario] = {s.case_id: s for s in (DOC_001, DOC_002, DOC_003, DOC_004, DOC_005, DOC_006, DOC_007, DOC_008)}
