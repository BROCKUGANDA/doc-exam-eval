You are a documentary credit examiner in a trade finance department. Your report is the deliverable a bank relies on before deciding whether to honour a presentation. Apply the supplied rulebook exactly as written; do not import external trade-finance conventions, and do not assume any fact the documents do not establish.

# Case DOC-004 — Shipment and presentation deadlines against the supplied calendar

Examine the presented documents against the shipment, presentation and expiry requirements, using only the calendar supplied with this credit.

## Documents presented

----- BL-001 : Bill of Lading -----
issuer: Amber Wave Lines
[page 1]
Bill of Lading
issued by Amber Wave Lines

Bill of Lading No.: AWL-BL-0021
Date of Issue: 2026-03-10
Vessel / Voyage: MV HALCYON DRAGON VOY 18E
Port of Loading: JEBEL ALI
Port of Discharge: ROTTERDAM
Consignee: TO ORDER
Notify Party: NORTHGATE INDUSTRIAL HOLDINGS ROTTERDAM
On Board Date: 2026-03-18
Description of Goods: PUMP ASSEMBLIES
Quantity Shipped: 1000 PCS
Shipping Marks: NGIH X-40 2026
Freight Terms: FREIGHT PREPAID
Transshipment at Transit Port: NO
Negotiation / Endorsement: NOT ENDORSED
Carrier: AMBER WAVE LINES
Signed By: SIGNED AWL AGENCY AS CARRIER

----- CAL-001 : Business Calendar -----
issuer: Crescent Trading Bank
[page 1]
Business Calendar
issued by Crescent Trading Bank

Calendar Reference: Business calendar applicable to this credit
Working Days: Monday to Friday except the closed dates listed below
Non-Working Days in Period: 2026-03-21, 2026-04-01, 2026-04-03

----- COO-001 : Certificate of Origin -----
issuer: Kestrel Chamber of Commerce
[page 1]
Certificate of Origin
issued by Kestrel Chamber of Commerce

Certificate of Origin No.: KCC-COO-19802
Date of Issue: 05/03/2026
Consignor: MERIDIAN EXPORT HOUSE COCHIN
Consignee: NORTHGATE INDUSTRIAL HOLDINGS ROTTERDAM
Description of Goods: INDUSTRIAL PUMP ASSEMBLIES MODEL X-40 GRADE A
Country of Origin: UNITED ARAB EMIRATES
Certifying Body: KESTREL CHAMBER OF COMMERCE
Signed By: SIGNED KCC REGISTRAR

----- INS-001 : Insurance Certificate -----
issuer: Halcyon Marine Insurance
[page 1]
Insurance Certificate
issued by Halcyon Marine Insurance

Insurance Certificate No.: HMI-IC-70355
Date of Issue: 2026-03-16
Assured: MERIDIAN EXPORT HOUSE COCHIN
Currency: USD
Insured Amount: USD 110,000.00
Coverage: INSTITUTE CARGO CLAUSES A
Vessel and Voyage: MV HALCYON DRAGON VOY 18E JEBEL ALI TO ROTTERDAM
Claims Payable At: ROTTERDAM

----- INV-001 : Commercial Invoice -----
issuer: Meridian Export House
[page 1]
Commercial Invoice
issued by Meridian Export House

Invoice No.: MEH-INV-4471
Invoice Date: 8 March 2026
T.T.R. No.: TTR 88214/26
Beneficiary: MERIDIAN EXPORT HOUSE COCHIN
Beneficiary Address: PLOT 14 HARBOR ESTATE COCHIN KERALA
Applicant: NORTHGATE INDUSTRIAL HOLDINGS ROTTERDAM
Description of Goods: INDUSTRIAL PUMP ASSEMBLIES MODEL X-40 GRADE A
Quantity: 1000 PCS
Unit Price: USD 100.00
Freight Charged: USD 4,000.00
Total amount: USD 100000
Currency: USD
Delivery Terms: CIF ROTTERDAM
Shipping Marks: NGIH X-40 2026
Declaration: WE CERTIFY THAT THIS INVOICE IS TRUE AND CORRECT

----- LC-001 : Documentary Credit -----
issuer: CRESCENT TRADING BANK DUBAI
[page 1]
Documentary Credit
issued by CRESCENT TRADING BANK DUBAI

Documentary Credit No.: CTB-LC-88214
Issue Date: 2026-02-10
Currency: USD
Credit Amount: USD 100,000.00
Amount in Words: SAY US DOLLARS ONE HUNDRED THOUSAND ONLY
Amount Tolerance Condition: NO TOLERANCE
Latest Date of Shipment: 2026-03-15
Date of Expiry: 2026-03-31
Presentation Period After Shipment: 14 days
Port of Loading: JEBEL ALI
Port of Discharge: ROTTERDAM
Description of Goods: INDUSTRIAL PUMP ASSEMBLIES MODEL X-40 GRADE A
Goods Specification: MODEL X-40, GRADE A, MATERIAL CARBON STEEL
Quantity: 1000 PCS
Commodity Class: packaged
Partial Shipments: ALLOWED
Transshipment: ALLOWED
Drawing Limit Condition: PARTIAL DRAWINGS PERMITTED
Required Documents: commercial invoice, packing list, bill of lading, insurance certificate, certificate of origin
Signature Requirement: NOT REQUIRED
Endorsement Requirement: NOT REQUIRED
Stipulated Fields: port of loading, port of discharge
Applicant: NORTHGATE INDUSTRIAL HOLDINGS ROTTERDAM
[page 2]
Beneficiary: MERIDIAN EXPORT HOUSE COCHIN
Beneficiary Address: PLOT 14 HARBOR ESTATE COCHIN KERALA
Issuing Bank: CRESCENT TRADING BANK DUBAI
Advising Bank: DELTAMARK COMMERCIAL BANK ROTTERDAM

----- PL-001 : Packing List -----
issuer: Meridian Export House
[page 1]
Packing List
issued by Meridian Export House

Packing List No.: MEH-PL-2210
Date: 2026-03-09
Description of Goods: PUMP ASSEMBLIES
Number of Cartons: 40 CTN
Pieces per Carton: 25 PCS
Total Pieces: 1000 PCS
Net Weight: 8000 KG
Gross Weight: 8400 KG
Shipping Marks: NGIH X-40 2026
Measurement: 12 CBM

----- PRES-001 : Schedule of Presentation -----
issuer: Halcyon Trade Finance
[page 1]
Schedule of Presentation
issued by Halcyon Trade Finance

Date of Presentation: 2026-04-04
Presented By: MERIDIAN TRADE SERVICES COCHIN
Documents Lodged: commercial invoice, packing list, bill of lading, insurance certificate, certificate of origin
Covering Reference: MEH/CVB/88214


# Examination rulebook (version 1.0.0)

This rulebook is the only governing standard for this task. Apply it as
written. Do not rely on any external trade-finance convention that is not
stated here. Where a field cannot be established from the supplied
documents, report it under unresolved_questions rather than assuming.

## Definitions
- **currency_minor_units**: USD=2; EUR=2; GBP=2; CHF=2; AED=2; SAR=2; CNY=2; INR=2; JPY=0; KRW=0
- **permitted_unit_conversions**: from=MT; to=KG; factor=1000; from=TONNE; to=KG; factor=1000; from=KM; to=M; factor=1000; from=M; to=CM; factor=100; from=HECTARE; to=SQM; factor=10000; from=L; to=ML; factor=1000; from=CASE; to=PCS; factor=24; from=PALLET; to=CTN; factor=40
- **units_without_default_conversion**: CTN; PCS; SET; ROLL; BAG
- **quantity_tolerance**: packaged={'allowed_pct': 0}; bulk={'allowed_pct': 5}
- **amount_tolerance**: about_wording=['about', 'approximately', 'circa', 'ca.']; about_pct=10; explicit_overrides_about=True
- **date_formats**: accepted=['YYYY-MM-DD', 'DD/MM/YYYY', 'MM-DD-YYYY', 'D Month YYYY', 'Month D YYYY', 'DD.MM.YYYY']
- **money_equality**: Compare amounts after rounding each to the currency's minor-unit precision using ROUND_HALF_UP. If the rounded values are equal, there is no monetary discrepancy, even if the documents render the amount differently (for example "USD 100,000.0", "USD 100000", "USD 100,000.00").
- **business_calendar**: {'rule': 'A deadline falling on a non-working day moves to the next working day of the supplied calendar. A presentation made on that next working day is timely.\n'}
- **precedence**: {'accepted_only': 'Only amendments marked ACCEPTED take effect. An amendment marked NOT ACCEPTED leaves the original term in force, and applying it is itself a discrepancy.\n', 'latest_wins': 'Where two accepted amendments govern the same field, the one with the later effective date supersedes the earlier.\n', 'superseded_values': 'Supporting documents that still carry a value superseded by the governing amendment are discrepant against the governing value.\n'}
- **evidence**: {'establishable': 'A field is established only if it appears in at least one supplied document. A field that appears in no document cannot be verified and must be reported under unresolved_questions, never assumed in either direction.\n', 'unreadable': 'A required field that is marked unreadable is not established. Reporting it as a discrepancy is a fabrication; reporting it as compliant is a false clearance.\n', 'citation': 'Every reported discrepancy must cite at least one evidence location as (document_id, page, location). The cited document_id must exist in the package.\n'}
- **state_selection**: CLEAR only if every required field is established and no discrepancy exists. DISCREPANCIES_FOUND if at least one discrepancy exists and all required fields are established. INSUFFICIENT_EVIDENCE if a required field cannot be established. HUMAN_REVIEW_REQUIRED if documents contradict each other in a way this rulebook does not resolve. Blanket escalation of every finding is not compliant. Where a case has BOTH a discrepancy and a field that cannot be established, any of DISCREPANCIES_FOUND, INSUFFICIENT_EVIDENCE or HUMAN_REVIEW_REQUIRED is an acceptable overall assessment, provided the unestablishable field is still listed in unresolved_questions.

## Rules
### RULE-AMT-001 — Invoice amount must not exceed the credit amount
Severity: critical. Applies to: INVOICE / total_amount.
Codes: AMOUNT_EXCEEDS_CREDIT.
The total amount claimed on the commercial invoice must not exceed the amount of the documentary credit, as adjusted by the governing amendment. Compare at the currency's minor-unit precision. An invoice claiming LESS than the credit amount is compliant: a beneficiary may draw part of the credit unless this credit expressly says otherwise, and no credit in this benchmark does.

### RULE-AMT-002 — Stated tolerance and "about" wording
Severity: critical. Applies to: INVOICE / total_amount.
Codes: AMOUNT_TOLERANCE_EXCEEDED.
Where the credit states an amount tolerance, amounts within that band are compliant. Where the credit instead says the amount is "about" or "approximately" a figure, a band of +/-10% of that figure applies. An explicit tolerance overrides the +/-10% default. Amounts outside the applicable band are discrepant.

### RULE-AMT-003 — Currency must match the credit currency
Severity: critical. Applies to: INVOICE, PACKING_LIST / currency.
Codes: CURRENCY_MISMATCH.
The currency of the amount claimed must be the credit currency, expressed as the same ISO 4217 code. No exchange-rate conversion is permitted unless the task supplies a rate, its source, its date and the conversion rule; without all four, different currency codes are a mismatch and must not be reconciled.

### RULE-AMT-004 — Amount presentation without minor units
Severity: minor. Applies to: INVOICE / total_amount_rendering.
Codes: AMOUNT_PRESENTATION_DEFECT.
Where an amount is established to be equal in value but is rendered without the currency's minor units (for example "USD 100000" where two decimals are required), this is a presentation defect, not a monetary conflict. Report it as a minor finding, never as a value discrepancy.

### RULE-QTY-001 — Quantity must match, subject to commodity class tolerance
Severity: critical. Applies to: INVOICE, PACKING_LIST, BILL_OF_LADING / quantity, unit.
Codes: QUANTITY_MISMATCH, QUANTITY_TOLERANCE_EXCEEDED.
The quantity shipped must match the quantity stated in the credit. For goods classed packaged by the credit there is no tolerance: any difference is a discrepancy. For goods classed bulk, a difference within 5% is compliant. Always convert to a common unit using the permitted conversions before comparing.

### RULE-QTY-002 — Permitted unit representations are not discrepancies
Severity: advisory. Applies to: INVOICE, PACKING_LIST, BILL_OF_LADING / unit.
A quantity expressed in a different unit is compliant when a permitted conversion relates the two and the converted values are equal. Where the unit pair has no permitted conversion, the quantities cannot be compared and the field is not established — report it under unresolved_questions rather than inventing a factor.

### RULE-DESC-001 — Goods description must not contradict the credit
Severity: critical. Applies to: INVOICE, PACKING_LIST, BILL_OF_LADING, CERTIFICATE_OF_ORIGIN / goods_description.
Codes: DESCRIPTION_CONTRADICTS_CREDIT.
The description must correspond to the credit description. Generalised or abbreviated wording that does not contradict a stated specification is compliant. A description that contradicts a stated specification — different grade, different model, different material, different origin where origin is stipulated — is a discrepancy.

### RULE-DESC-002 — Variance in fields the credit does not stipulate
Severity: minor. Applies to: CREDIT, INVOICE, PACKING_LIST, BILL_OF_LADING / shipping_marks, beneficiary_address.
Codes: SHIPPING_MARKS_MISMATCH, BENEFICIARY_ADDRESS_VARIANT.
Where the credit does not stipulate a field, documents that describe it differently create an ambiguity rather than a breach. Report it as a minor finding. Never escalate a non-stipulated variance to critical, and never treat it as grounds for refusing the presentation.

### RULE-DATE-001 — Shipment must occur on or before the latest shipment date
Severity: critical. Applies to: BILL_OF_LADING / on_board_date.
Codes: SHIPMENT_AFTER_LATEST_DATE.
The on-board date evidenced by the transport document must be on or before the latest shipment date in the governing credit terms. The on-board date, not the document issue date, is the shipment date.

### RULE-DATE-002 — Presentation within the period after shipment
Severity: critical. Applies to: PRESENTATION_SCHEDULE / presentation_date, on_board_date.
Codes: PRESENTATION_AFTER_DEADLINE.
Documents must be presented within the number of calendar days after shipment stated in the credit. If that number falls due on a non-working day of the supplied calendar, the deadline moves to the next working day of that calendar. Presentations made up to and including the adjusted deadline are timely.

### RULE-DATE-003 — Presentation on or before credit expiry
Severity: critical. Applies to: PRESENTATION_SCHEDULE / presentation_date.
Codes: PRESENTATION_AFTER_EXPIRY.
Presentation must occur on or before the expiry date of the governing credit terms, regardless of the period allowed after shipment. Where the period after shipment would run past expiry, expiry binds.

### RULE-DATE-004 — Documents must be dated consistently with the events they evidence
Severity: critical. Applies to: INSURANCE_CERTIFICATE, CERTIFICATE_OF_ORIGIN, INSPECTION_CERTIFICATE, INVOICE / issue_date.
Codes: DOCUMENT_DATED_AFTER_PRESENTATION, INSURANCE_DATED_AFTER_SHIPMENT, INSPECTION_DATED_AFTER_SHIPMENT.
No document may be dated after the presentation date. Insurance must be dated on or before the shipment date, because cover cannot be obtained after the risk has attached. A required inspection certificate must be dated on or before the shipment date unless the credit says otherwise.

### RULE-DATE-005 — Equivalent date renderings are not discrepancies
Severity: advisory. Applies to: ANY / ANY_DATE.
Two documents showing the same calendar date in different accepted formats are consistent. A format difference is never, by itself, a discrepancy. Ambiguous numeric dates that could be read as two different calendar dates are not established — report them under unresolved_questions.

### RULE-TRN-001 — Ports must match the credit
Severity: critical. Applies to: BILL_OF_LADING / port_of_loading, port_of_discharge.
Codes: PORT_OF_LOADING_MISMATCH, PORT_OF_DISCHARGE_MISMATCH.
The transport document must show the port of loading and port of discharge stated in the credit. Where the credit names a country or a range of ports, any named port within it is compliant. A different port is a discrepancy.

### RULE-TRN-002 — Consignee and notify party as stipulated
Severity: critical. Applies to: BILL_OF_LADING / consignee, notify_party.
Codes: CONSIGNEE_MISMATCH, NOTIFY_PARTY_MISMATCH.
Where the credit stipulates the consignee or notify party, the transport document must show it as stipulated. Where the credit is silent, any consignee is acceptable and no finding may be raised.

### RULE-TRN-003 — Partial shipment and transshipment must be permitted
Severity: critical. Applies to: BILL_OF_LADING, PACKING_LIST / shipment_split, transshipment.
Codes: PARTIAL_SHIPMENT_NOT_PERMITTED, TRANSSHIPMENT_NOT_PERMITTED.
Where the credit prohibits partial shipment, all stipulated quantity must ship under one transport document. Where it prohibits transshipment, the transport document must not evidence a change of conveyance between loading and discharge ports. Silence in the credit means both are permitted.

### RULE-DOC-001 — Every required document must be presented
Severity: critical. Applies to: ANY / presence.
Codes: DOCUMENT_MISSING.
Each document named in the credit's list of required documents must be present in the presentation. A document of a different type does not satisfy the requirement. A duplicate of a document does not substitute for a missing required document of another type.

### RULE-DOC-002 — Required signatures and endorsements
Severity: critical. Applies to: INSPECTION_CERTIFICATE, CERTIFICATE_OF_ORIGIN, BILL_OF_LADING / signed_by, endorsed_to_order.
Codes: DOCUMENT_SIGNATURE_MISSING, DOCUMENT_ENDORSEMENT_DEFECTIVE.
Where the credit requires a document to be signed, or to be endorsed to order, the presented copy must show that. Absence where required is a discrepancy; absence where the credit is silent is not.

### RULE-DOC-003 — Certificates must be valid at the relevant date
Severity: critical. Applies to: INSPECTION_CERTIFICATE, CERTIFICATE_OF_ORIGIN / valid_until.
Codes: DOCUMENT_EXPIRED.
A certificate whose stated validity ends before the shipment date is expired and does not satisfy the requirement. Compare using the calendar dates as established, not the rendering.

### RULE-DOC-004 — Unreadable and absent fields cannot be resolved either way
Severity: advisory. Applies to: ANY / ANY.
A required field that is unreadable, or that appears in no supplied document, is not established. Report it in unresolved_questions with the document_id and field. Do not treat it as compliant, and do not report it as a discrepancy.

### RULE-AMD-001 — Only accepted amendments take effect
Severity: advisory. Applies to: AMENDMENT / acceptance_state.
Examine against the terms produced by applying the ACCEPTED amendments to the original credit. An amendment marked NOT ACCEPTED has no effect: the original term remains in force. Supporting documents are therefore correct or incorrect against the ORIGINAL value, and this is decided by RULE-AMD-003.

### RULE-AMD-002 — Later accepted amendment supersedes earlier ones
Severity: advisory. Applies to: AMENDMENT / effective_date.
Where two or more accepted amendments govern the same field, the amendment with the later effective date states the governing value. Earlier accepted values for that field no longer apply, and RULE-AMD-003 decides the consequence.

### RULE-AMD-003 — Supporting documents must match the governing terms
Severity: critical. Applies to: INVOICE, PACKING_LIST, BILL_OF_LADING / ANY.
Codes: DOCUMENT_CARRIES_SUPERSEDED_VALUE.
Once the governing terms are established, supporting documents are examined against them. A supporting document that still shows a value superseded by an accepted amendment, or a value from an amendment that was never accepted, is discrepant even though it agrees with the original credit. Where another rule already produces a finding for that same field, that rule's code is the finding; this rule only reports fields no other rule covers, so one defect is never counted twice.


## Output contract

Return one JSON object and nothing else, with exactly these top-level keys:

  case_id              string — the case identifier given below
  assessment           one of CLEAR | DISCREPANCIES_FOUND | INSUFFICIENT_EVIDENCE | HUMAN_REVIEW_REQUIRED
  documents_reviewed   array of document ids you examined (at least one)
  discrepancies        array; each item:
      code                one of the codes listed below
      field               the field the finding concerns
      severity            critical | minor
      observed_values     object of what you saw, per document
      rule_id             the RULE-* id you applied
      evidence            array; each item: {"document_id", "page", "location"}
                          The document_id must be a document present in this package and the
                          location must name where on that document you read it.
      explanation         string
      escalation_required boolean
  unresolved_questions array; each item: {"field", "reason", "evidence", "explanation}
      reason is one of absent | unreadable | ambiguous | not_comparable | contradictory
  summary              string

A discrepancy with no evidence that resolves to a real document and location will not be
credited. Reporting a discrepancy you cannot evidence is treated as a fabrication.

### Permitted discrepancy codes

- AMOUNT_EXCEEDS_CREDIT
- AMOUNT_PRESENTATION_DEFECT
- AMOUNT_TOLERANCE_EXCEEDED
- BENEFICIARY_ADDRESS_VARIANT
- CONSIGNEE_MISMATCH
- CURRENCY_MISMATCH
- DESCRIPTION_CONTRADICTS_CREDIT
- DOCUMENT_CARRIES_SUPERSEDED_VALUE
- DOCUMENT_DATED_AFTER_PRESENTATION
- DOCUMENT_ENDORSEMENT_DEFECTIVE
- DOCUMENT_EXPIRED
- DOCUMENT_MISSING
- DOCUMENT_SIGNATURE_MISSING
- INSPECTION_DATED_AFTER_SHIPMENT
- INSURANCE_DATED_AFTER_SHIPMENT
- NOTIFY_PARTY_MISMATCH
- PARTIAL_SHIPMENT_NOT_PERMITTED
- PORT_OF_DISCHARGE_MISMATCH
- PORT_OF_LOADING_MISMATCH
- PRESENTATION_AFTER_DEADLINE
- PRESENTATION_AFTER_EXPIRY
- QUANTITY_MISMATCH
- QUANTITY_TOLERANCE_EXCEEDED
- SHIPMENT_AFTER_LATEST_DATE
- SHIPPING_MARKS_MISMATCH
- TRANSSHIPMENT_NOT_PERMITTED
