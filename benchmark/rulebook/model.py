"""Rulebook loader: schema-validated, indexed, and fingerprinted.

Two properties matter for the rubric and are enforced here:

1. A rule whose `kind` has no evaluator in the truth engine cannot produce ground
   truth, so loading fails loudly instead of silently grading nothing.
2. Every graded discrepancy code must come from a rule, so the task linter can
   prove nothing is graded that the supplied rulebook does not state.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from benchmark.paths import RULEBOOK_FILE

Severity = Literal["critical", "minor", "none", "escalation"]

# Kinds the truth engine knows how to evaluate. Keep in sync with
# benchmark/truth/engine.py; test_rulebook_engine_coverage.py asserts it.
PRODUCER_KINDS = frozenset(
    {
        "amount_not_exceed_credit",
        "amount_tolerance_band",
        "currency_exact_match",
        "money_presentation_format",
        "quantity_within_tolerance",
        "description_contradiction",
        "non_governing_field_variance",
        "shipment_on_or_before_latest",
        "presentation_within_period",
        "presentation_on_or_before_expiry",
        "document_dating_order",
        "port_match",
        "party_match",
        "shipment_permits",
        "required_documents_present",
        "signature_and_endorsement",
        "validity_at_relevant_date",
        "documents_match_governing_terms",
    }
)

# Advisory rules that never emit a finding of their own but change how other
# evaluators decide — they are what stops a format difference being scored as a
# discrepancy, and what decides which version of the credit governs.
POLICY_KINDS = frozenset(
    {
        "unit_representation_equivalence",
        "date_format_equivalence",
        "accepted_amendment_only",
        "latest_accepted_supersedes",
        "field_establishable",
    }
)


class AppliesTo(BaseModel):
    docs: list[str]
    fields: list[str]

    @field_validator("docs", "fields")
    @classmethod
    def _non_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("applies_to lists must not be empty")
        return v


class Rule(BaseModel):
    id: str
    kind: str
    title: str
    severity: Severity
    codes: list[str] = Field(default_factory=list)
    applies_to: AppliesTo
    params: dict[str, Any] = Field(default_factory=dict)
    statement: str

    @model_validator(mode="after")
    def _kind_is_implemented(self) -> "Rule":
        if self.kind not in PRODUCER_KINDS | POLICY_KINDS:
            raise ValueError(f"{self.id}: kind {self.kind!r} has no evaluator in the truth engine")
        if self.severity in ("critical", "minor", "escalation") and not self.codes:
            raise ValueError(f"{self.id}: severity {self.severity!r} but no codes declared")
        if self.kind in POLICY_KINDS and self.codes:
            raise ValueError(f"{self.id}: policy kinds must not declare codes")
        return self


class Rulebook(BaseModel):
    version: str
    id: str
    definitions: dict[str, Any]
    rules: list[Rule]

    @model_validator(mode="after")
    def _ids_unique(self) -> "Rulebook":
        seen: set[str] = set()
        for r in self.rules:
            if r.id in seen:
                raise ValueError(f"duplicate rule id {r.id}")
            seen.add(r.id)
        return self

    # ---- indexes ----------------------------------------------------------
    @property
    def by_id(self) -> dict[str, Rule]:
        return {r.id: r for r in self.rules}

    @property
    def producer_rules(self) -> list[Rule]:
        return [r for r in self.rules if r.kind in PRODUCER_KINDS]

    @property
    def codes(self) -> frozenset[str]:
        """Closed vocabulary of reportable discrepancy codes."""
        return frozenset(c for r in self.rules for c in r.codes)

    @property
    def code_to_rules(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for r in self.rules:
            for c in r.codes:
                out.setdefault(c, []).append(r.id)
        return out

    def severity_of_rule(self, rule_id: str) -> str:
        return self.by_id[rule_id].severity

    def critical_codes(self) -> frozenset[str]:
        return frozenset(c for r in self.rules if r.severity == "critical" for c in r.codes)

    # ---- money / unit helpers used by both truth engine and graders -------
    def minor_units(self, iso4217: str) -> int:
        table = self.definitions["currency_minor_units"]
        if iso4217 not in table:
            raise KeyError(f"currency {iso4217!r} not declared in rulebook definitions")
        return int(table[iso4217])

    def unit_conversion_factor(self, frm: str, to: str) -> float | None:
        for row in self.definitions["permitted_unit_conversions"]:
            if row["from"] == frm and row["to"] == to:
                return float(row["factor"])
            if row["from"] == to and row["to"] == frm:
                return 1.0 / float(row["factor"])
        return None

    # ---- rendering --------------------------------------------------------
    def markdown(self) -> str:
        """The exact text handed to every model. Deterministic, so prompts are frozen."""
        lines = [
            "# Examination rulebook (version %s)" % self.version,
            "",
            "This rulebook is the only governing standard for this task. Apply it as",
            "written. Do not rely on any external trade-finance convention that is not",
            "stated here. Where a field cannot be established from the supplied",
            "documents, report it under unresolved_questions rather than assuming.",
            "",
            "## Definitions",
        ]
        defs = self.definitions
        for name in (
            "currency_minor_units",
            "permitted_unit_conversions",
            "units_without_default_conversion",
            "quantity_tolerance",
            "amount_tolerance",
            "date_formats",
        ):
            lines.append(f"- **{name}**: {_render(defs[name])}")
        for name in ("money_equality", "business_calendar", "precedence", "evidence", "state_selection"):
            lines.append(f"- **{name}**: {str(defs[name]).strip()}")
        lines += ["", "## Rules"]
        for r in self.rules:
            sev = r.severity if r.severity != "none" else "advisory"
            lines.append(f"### {r.id} — {r.title}")
            lines.append(f"Severity: {sev}. Applies to: {', '.join(r.applies_to.docs)} / {', '.join(r.applies_to.fields)}.")
            if r.codes:
                lines.append(f"Codes: {', '.join(r.codes)}.")
            lines.append(str(r.statement).strip())
            lines.append("")
        return "\n".join(lines)

    def fingerprint(self) -> str:
        return hashlib.sha256(RULEBOOK_FILE.read_bytes()).hexdigest()[:16]


def _render(value: Any) -> str:
    if isinstance(value, dict):
        return "; ".join(f"{k}={v}" for k, v in value.items())
    if isinstance(value, list):
        return "; ".join(_render(v) if isinstance(v, (dict, list)) else str(v) for v in value)
    return str(value)


def load_rulebook(path: Any = None) -> Rulebook:
    raw = yaml.safe_load((path or RULEBOOK_FILE).read_text(encoding="utf-8"))
    return Rulebook.model_validate(raw)


@lru_cache(maxsize=1)
def rulebook() -> Rulebook:
    return load_rulebook()
