"""Task packaging: what the model sees, kept strictly apart from the answer.

Layout follows the Terminal-Bench / Harbor task shape the Participant Guide shows (p.6) —
instruction, environment, solution, tests — but the benchmark does not depend on Harbor at
runtime, because p.7 says it is optional and a judge must reproduce this with one command.

The separation that matters: the prompt is assembled from the brief, the rendered documents
and the rulebook only. Scenario notes, computed ground truth and reference solutions are
never reachable from it, because a model that passed by reading the answer would tell us
nothing about the models (Guide p.12, "It can't be gamed").
"""

from __future__ import annotations

import json
from pathlib import Path

from benchmark.generator.build import Scenario
from benchmark.package import Package
from benchmark.paths import TASKS_DIR
from benchmark.rulebook.model import Rulebook
from benchmark.truth.engine import GroundTruth

# Prompt-visible framing. States the examination scope, never the answer.
BRIEFS: dict[str, str] = {
    "DOC-001": (
        "Examine the presented documents against the credit above and decide whether the "
        "presentation is compliant. Report only what the documents and the rulebook support."
    ),
    "DOC-002": (
        "Examine the presented documents, giving the monetary comparison the attention it "
        "requires. State every discrepancy you can evidence."
    ),
    "DOC-003": (
        "Examine the presented documents for quantity and goods-description consistency. "
        "Where two statements cannot be compared under the rulebook, say so rather than "
        "choosing an interpretation."
    ),
    "DOC-004": (
        "Examine the presented documents against the shipment, presentation and expiry "
        "requirements, using only the calendar supplied with this credit."
    ),
    "DOC-005": (
        "Verify the transport document against the credit across ports, parties and shipment "
        "conditions, and check the remaining documents for consistency with it."
    ),
    "DOC-006": (
        "Determine which required documents were presented, which are defective, and which "
        "points cannot be established at all from what was supplied."
    ),
    "DOC-007": (
        "Several amendments have been issued for this credit. Establish which terms actually "
        "govern the examination, then examine the presented documents against them."
    ),
    "DOC-008": (
        "Perform a complete examination of this presentation. Several issues may coexist; "
        "distinguish critical from minor findings and escalate anything the rulebook cannot "
        "resolve."
    ),
}

ROLE = (
    "You are a documentary credit examiner in a trade finance department. Your report is the "
    "deliverable a bank relies on before deciding whether to honour a presentation. Apply the "
    "supplied rulebook exactly as written; do not import external trade-finance conventions, "
    "and do not assume any fact the documents do not establish."
)

CONTRACT = """\
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

{codes}
"""


def prompt_for(scenario: Scenario, package: Package, rb: Rulebook) -> str:
    brief = BRIEFS.get(scenario.case_id)
    if brief is None:
        raise KeyError(f"no brief for {scenario.case_id}")
    codes = "\n".join(f"- {c}" for c in sorted(rb.codes))
    return "\n\n".join(
        [
            ROLE,
            f"# Case {scenario.case_id} — {scenario.title}\n\n{brief}",
            "## Documents presented\n\n" + package.text_block(),
            rb.markdown(),
            CONTRACT.replace("{codes}", codes),
        ]
    )


def task_toml(scenario: Scenario, truth: GroundTruth, rb: Rulebook, prompt_tokens: int) -> str:
    return "\n".join(
        [
            f"[task]",
            f'name        = "{scenario.case_id}"',
            f"title       = {json.dumps(scenario.title)}",
            f"seed        = {scenario.seed}",
            f"rulebook    = {json.dumps(rb.version)}",
            f"domain      = \"trade-finance/documentary-credit-examination\"",
            f"expected_findings = {len(truth.findings)}",
            f"expected_unresolved = {len(truth.unresolved)}",
            f"acceptable_assessments = {sorted(truth.acceptable_assessments)}",
            f"",
            f"[environment]",
            f"docker_image = \"not-required: text track A\"",
            f"prompt_tokens_estimate = {prompt_tokens}",
            f"",
            f"[grading]",
            f"grader      = \"benchmark.graders.scoring:grade\"",
            f"threshold   = 70",
        ]
    )


def write_tasks(cases: dict[str, tuple[Package, GroundTruth]], scenarios: dict[str, Scenario], rb: Rulebook, out_root: Path | None = None) -> list[Path]:
    """Materialise the on-disk task layout. Prompt files and reference files go to
    separate directories so the ZIP can be audited for leakage."""
    root = out_root or TASKS_DIR
    written: list[Path] = []
    for case_id, (package, truth) in sorted(cases.items()):
        scenario = scenarios[case_id]
        text = prompt_for(scenario, package, rb)
        case_dir = root / case_id
        (case_dir / "environment").mkdir(parents=True, exist_ok=True)
        (case_dir / "solution").mkdir(parents=True, exist_ok=True)
        (case_dir / "tests").mkdir(parents=True, exist_ok=True)

        _write(case_dir / "instruction.md", text)
        _write(case_dir / "task.toml", task_toml(scenario, truth, rb, len(text) // 4))
        _write(case_dir / "environment" / "documents.json", json.dumps(package.to_dict(), indent=2, sort_keys=True))
        _write(case_dir / "solution" / "reference.json", json.dumps(truth.to_dict(), indent=2, sort_keys=True))
        _write(
            case_dir / "tests" / "grader_config.json",
            json.dumps(
                {
                    "case_id": case_id,
                    "weights": {"recall": 25, "precision": 20, "rule_mapping": 15, "evidence": 15, "severity": 10, "uncertainty": 10, "format": 5},
                    "threshold": 70,
                    "hard_caps": ["CRITICAL_FALSE_CLEARANCE", "FABRICATED_ON_CLEAN_PRESENTATION", "HALLUCINATED_EVIDENCE", "WRONG_FINAL_DETERMINATION", "UNPARSEABLE_OUTPUT"],
                },
                indent=2,
                sort_keys=True,
            ),
        )
        written.append(case_dir)
    return written


def _write(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8", newline="\n")
