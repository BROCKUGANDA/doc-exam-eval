"""Task linter: the checks that make the benchmark defensible before any model runs.

Enforced mechanically rather than hoped for, because the rubric pays 20 points for task
design and 20 for grader reliability, and the guide's list of how submissions fail (p.13)
is mostly items that a CI check could have caught:

- everything graded is stated in the task;
- reference solutions exist and pass;
- the answer is not visible to the model;
- two experts would agree, i.e. severities come from the rulebook, not from taste;
- the suite has headroom, rather than being all-zero or all-hundred.
"""

from __future__ import annotations

from benchmark.generator.build import Scenario
from benchmark.package import Package
from benchmark.rulebook.model import PRODUCER_KINDS, Rulebook
from benchmark.tasks import BRIEFS, prompt_for
from benchmark.truth.engine import GroundTruth
from benchmark.truth.rules_eval import EVALUATORS


def lint(scenario: Scenario, package: Package, truth: GroundTruth, rb: Rulebook) -> list[str]:
    problems: list[str] = []
    prompt = prompt_for(scenario, package, rb)

    # 1. The engine cannot invent vocabulary.
    for f in truth.findings:
        if f.code not in rb.codes:
            problems.append(f"{f.finding_id}: code {f.code} is not declared by any rule")
        if f.rule_id not in rb.by_id:
            problems.append(f"{f.finding_id}: rule_id {f.rule_id} does not exist")
        elif rb.severity_of_rule(f.rule_id) != f.severity:
            problems.append(
                f"{f.finding_id}: severity {f.severity} but {f.rule_id} declares "
                f"{rb.severity_of_rule(f.rule_id)} — severity must come from the rulebook"
            )
        for alias in f.alias_codes:
            if alias not in rb.codes:
                problems.append(f"{f.finding_id}: alias code {alias} is undeclared")
        if not f.evidence:
            problems.append(f"{f.finding_id}: no evidence refs, so nothing can be cited for it")
        for ev in f.evidence:
            if package.doc_by_id(ev.doc_id) is None:
                problems.append(f"{f.finding_id}: evidence cites absent document {ev.doc_id}")

    for u in truth.unresolved:
        for doc_id in u.docs:
            if package.doc_by_id(doc_id) is None:
                problems.append(f"unresolved {u.field} cites absent document {doc_id}")

    # 2. Everything graded must be visible to the model.
    if rb.markdown() not in prompt:
        problems.append("prompt omits the rulebook the grader applies")
    if package.text_block().strip() not in prompt:
        problems.append("prompt omits part of the document package")
    for code in {f.code for f in truth.findings}:
        if f"- {code}" not in prompt:
            problems.append(f"code {code} is graded but never offered to the model")
    for key in ("assessment", "discrepancies", "unresolved_questions", "evidence", "severity", "rule_id"):
        if key not in prompt:
            problems.append(f"contract does not mention required key {key}")

    # 3. The answer must not be reachable from the prompt.
    brief = BRIEFS.get(scenario.case_id, "")
    for token in sorted({f.code for f in truth.findings} | {f.field for f in truth.findings}):
        if token and token.lower() in brief.lower():
            problems.append(f"brief leaks graded token {token!r}")
    if scenario.note and scenario.note.strip() and scenario.note.strip() in prompt:
        problems.append("prompt contains the author-only note")
    if "reference.json" in prompt or "solution/" in prompt:
        problems.append("prompt references the solution file")

    # 4. Headroom and spread (Guide p.11: all-zero and all-hundred are both warnings).
    if len(truth.findings) > 8:
        problems.append(f"{len(truth.findings)} findings in one task invites partial-credit noise over signal")

    # 5. Referenced amendments must exist in the package.
    applied = set(truth.amendments_applied) | set(truth.amendments_ignored)
    presented = {doc.doc_id for doc in package.documents if doc.doc_type == "AMENDMENT"}
    if applied and not presented:
        problems.append("terms claim amendments were applied or ignored but no amendment document exists")

    return problems


def suite_report(cases: dict[str, tuple[Package, GroundTruth]], rb: Rulebook) -> dict:
    """Aggregate coverage: which rules the suite actually exercises.

    A rule nothing tests is a rule nobody verified, so this is reported rather than buried.
    """
    exercised: set[str] = set()
    exercised_codes: set[str] = set()
    for _, (_, truth) in cases.items():
        for f in truth.findings:
            exercised.add(f.rule_id)
            exercised_codes.add(f.code)
            for alias in f.alias_codes:
                exercised_codes.add(alias)
                # A rule that supplied an accepted description of a real defect did work,
                # even where a category rule got the primary code.
                exercised.update(rb.code_to_rules.get(alias, []))

    producer_ids = {r.id for r in rb.rules if r.kind in PRODUCER_KINDS}
    unexercised_rules = sorted(producer_ids - exercised)
    unexercised_codes = sorted(rb.codes - exercised_codes)
    kinds_without_evaluator = sorted(
        r.kind for r in rb.rules if r.kind in PRODUCER_KINDS and r.kind not in EVALUATORS
    )
    declared_but_absent = sorted(
        kind for kind in EVALUATORS if kind not in {r.kind for r in rb.rules}
    )

    total_findings = sum(len(t.findings) for _, t in cases.values())
    return {
        "tasks": len(cases),
        "total_ground_truth_findings": total_findings,
        "clean_tasks": sum(1 for _, truth in cases.values() if not truth.findings and not truth.unresolved),
        "rules_declared": len(rb.rules),
        "producer_rules": len(producer_ids),
        "rules_exercised": len(producer_ids & exercised),
        "rules_never_exercised": unexercised_rules,
        "codes_declared": len(rb.codes),
        "codes_never_exercised": unexercised_codes,
        "kinds_without_evaluator": kinds_without_evaluator,
        "evaluators_for_undeclared_kinds": declared_but_absent,
    }
