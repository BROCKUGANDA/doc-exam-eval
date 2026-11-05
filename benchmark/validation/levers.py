"""Inventory of the grader levers the mutation suite must break.

The names and what they represent live here; the lambdas live in
tests/test_mutations.py, which asserts its own key set matches this one. That split exists
so the platform can display the levers without duplicating them, and so a lever added or
dropped in the tests fails a check rather than quietly diverging from what the README and
the dashboard claim was proven.
"""

from __future__ import annotations

GRADER_LEVERS: dict[str, str] = {
    "recall_always_full": "Missing findings would no longer cost anything.",
    "precision_never_penalised": "Fabricated findings would be free.",
    "evidence_traceability_free": "Citations would not have to point anywhere real.",
    "rule_mapping_free": "Naming the wrong rule would score as correct.",
    "severity_free": "Severity would not have to match the rulebook ladder.",
    "uncertainty_free": "Invented or blanket escalation would be unrewarded-free.",
    "uncertainty_credit_counts_repeats": (
        "Asking the same unanswerable question three times would buy three times the credit. "
        "A live gpt-oss-20b trial did exactly that and scored 102.5 on a 100-point rubric."
    ),
    "missed_critical_not_capped": "The catastrophic professional error would stop being fatal.",
    "false_accusation_not_capped": "Hallucinating on a compliant presentation would earn partial credit.",
    "hallucinated_evidence_not_capped": "Citing a document that is not in the package would pass.",
    "wrong_determination_allowed": "A wrong headline verdict with a right itemisation would pass.",
    # Removed: "field_matching_requires_exact_name". Once the third matching tier existed,
    # breaking exact field-name matching no longer changed any outcome — the corpus could not
    # detect it. Keeping it would have advertised a lever that is not load-bearing.
    "structural_errors_treated_as_extra_keys": "An unusable report would keep its format marks.",
    "prose_accepted_as_output": "Non-JSON output would be scored instead of rejected.",
    "matching_reverted_to_two_tiers": (
        "Detection would be scored as if it required a perfect citation. The third "
        "matching tier exists so that finding the right defect with a weak citation "
        "earns recall and loses traceability, not loses both."
    ),
}

#: Levers that live in the evidence index rather than the grader. Each one reverts a bug that
#: a real model transcript exposed, which is why they are listed separately.
INDEX_LEVERS: dict[str, str] = {
    "citation_resolution_reverted_to_exact_match": (
        "A location quoted with its value ('Total amount: USD 105,000.00') would score zero "
        "traceability — the bug the first live gpt-oss trial exposed."
    ),
}
