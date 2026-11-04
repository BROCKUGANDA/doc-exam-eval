"""The model output contract, generated from the rulebook.

The code enum is *derived* from the rulebook rather than retyped, so a rule added to
the rulebook cannot be gradeable in one place and unmentionable in another. States come
from the rulebook's assessment_states definition for the same reason.

Strictness policy, which decides 5 points and can silently cost 20 more if wrong:

- Unparseable JSON, or output that is not an object, is a hard failure (score 0).
- A structural violation (missing required key, wrong type, a state outside the
  vocabulary) zeroes the format dimension, because the deliverable is unusable.
- An *extra* key only costs part of the format dimension. A model that answers
  correctly and adds a "confidence" field must not be told it failed the task.
"""

from __future__ import annotations

from benchmark.rulebook.model import Rulebook

REQUIRED_TOP_LEVEL = ("case_id", "assessment", "documents_reviewed", "discrepancies", "unresolved_questions", "summary")

DISCREPANCY_KEYS = ("code", "field", "severity", "observed_values", "rule_id", "evidence", "explanation", "escalation_required")
EVIDENCE_KEYS = ("document_id", "page", "location")
UNRESOLVED_KEYS = ("field", "reason", "evidence", "explanation")
UNRESOLVED_REASONS = ("absent", "unreadable", "ambiguous", "not_comparable", "contradictory")

EXTRA_KEY_PREFIX = "Additional properties are not allowed"


def build_schema(rb: Rulebook) -> dict:
    """jsonschema for the examination report, with the rulebook's live vocabulary."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": True,
        "required": list(REQUIRED_TOP_LEVEL),
        "properties": {
            "case_id": {"type": "string", "minLength": 1},
            "assessment": {"enum": sorted(rb.definitions["assessment_states"])},
            "documents_reviewed": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "discrepancies": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["code", "severity", "rule_id", "evidence", "explanation"],
                    "properties": {
                        "code": {"enum": sorted(rb.codes)},
                        "field": {"type": "string"},
                        "severity": {"enum": ["critical", "minor"]},
                        "observed_values": {"type": "object"},
                        "rule_id": {"type": "string", "minLength": 1},
                        "evidence": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "additionalProperties": True,
                                "required": ["document_id", "location"],
                                "properties": {
                                    "document_id": {"type": "string", "minLength": 1},
                                    "page": {"type": ["integer", "string"]},
                                    "location": {"type": "string", "minLength": 1},
                                },
                            },
                        },
                        "explanation": {"type": "string", "minLength": 1},
                        "escalation_required": {"type": "boolean"},
                    },
                },
            },
            "unresolved_questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["field", "reason"],
                    "properties": {
                        "field": {"type": "string", "minLength": 1},
                        "reason": {"enum": list(UNRESOLVED_REASONS)},
                        "evidence": {"type": "array", "items": {"type": "object"}},
                        "explanation": {"type": "string"},
                    },
                },
            },
            "summary": {"type": "string", "minLength": 1},
        },
    }


def split_format_errors(errors: list[str]) -> tuple[list[str], list[str]]:
    """(structural, extra-key) — the distinction that keeps a correct answer from
    being zeroed for adding an unrequested field."""
    structural, extra = [], []
    for e in errors:
        (extra if e.startswith(EXTRA_KEY_PREFIX) else structural).append(e)
    return structural, extra
