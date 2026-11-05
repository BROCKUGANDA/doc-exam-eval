# DOC-EXAM — Can frontier models examine a documentary credit?

An AI evaluation benchmark for **trade-finance document examination**: it tests whether
frontier and open-weight models can look at a letter-of-credit presentation, find every
material discrepancy, apply the supplied rules, cite the document that proves each finding,
and refuse to decide what the evidence does not establish.

The capability being measured is not "understands financial language". It is four things a
bank's payment decision depends on at once: **detect the discrepancy, identify its source,
apply the correct rule, and know when not to make a decision.**

```
python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt   # see "How to run"
python run_eval.py --validate
```

That single command regenerates every document from seeds, recomputes every reference answer,
proves each reference passes its grader, and proves each deliberately wrong answer is rejected.
It needs **no API key, no database, no Docker and no web server**.

---

## 0. Short description

**Domain.** Trade finance — specifically documentary credit (letter of credit) examination,
the compliance check a bank performs before paying an exporter.

**The gap I found.** Models are fluent in the vocabulary of this work and unreliable in its
*economics of evidence*: they will explain what a bill of lading is, then fail a two-line
money comparison across four documents under a stated tolerance, miss that an amendment was
never accepted, treat a harmless abbreviation as a discrepancy, or declare a field compliant
when the document that would prove it is illegible. The professional skill is not
comprehension; it is **detecting the discrepancy, naming its source, applying the correct
rule, and declining to decide what the evidence cannot establish.**

**Key finding.** *To be written from the transcripts once the live panel has run — see §6.*
It is left empty on purpose. The rules state that fabricated results are grounds for
disqualification, and a finding invented before the data exists is exactly that.

**Video walkthrough.** *Not yet recorded; the link will appear here and in the submission
field.* It is not inside this ZIP, per the instructions.

## 0.1 Domain and expertise

This eval draws on documentary-credit examination practice: the discrepancy categories, the
material-versus-harmless distinction, amendment acceptance, deadline adjustment for
non-working days, and the tolerance conventions are the ones a confirming or issuing bank
applies. The rulebook is written from that domain knowledge rather than from a model's
summary of it, and every severity classification in it is subject to a named human examiner's
sign-off, recorded with dates in [`docs/expert-review.md`](docs/expert-review.md) and
regenerated from the same artefacts that do the grading.

## 1. Who relies on this work, and what a failure costs

Documentary credit is the payment mechanism behind a large share of physical trade. An
examining bank has a fixed number of banking days to decide whether documents conform, and
the decision is binary in consequence: pay, or issue a refusal notice.

- A **missed discrepancy** that the bank then pays against loses the applicant's protection
  and, more often than not, the right to be reimbursed by the issuing bank. The loss is the
  full drawn amount — here, six figures per presentation.
- A **fabricated discrepancy** wastes the deadline, damages the seller's credit line, and
  invites a dispute. Banks are criticised for exactly this: refusing on grounds that do not
  exist.
- An examiner who **guesses at an unreadable field** instead of escalating is the reason
  discrepancy checklists exist.

The interesting hypothesis is that models are fluent in the *vocabulary* of this work while
being unreliable at its *arithmetic of evidence*: cross-document money comparison under a
tolerance, deadline arithmetic against a supplied non-standard calendar, amendment
precedence, and the restraint required to return "CLEAR" on a package full of harmless
differences.

## 2. Tasks

Eight tasks. Each ships with a document package, a self-contained rulebook, a computed
reference answer, and a grader.

| Task | What it examines | Why it is hard for a model |
|---|---|---|
| DOC-001 | A fully compliant presentation | Nothing is wrong. Generalised goods wording, `USD 100000` vs `USD 100,000.00`, `10 March 2026` vs `2026-03-10`, and a deadline that moves because the due date is a closed day. The skill is **restraint**: any reported discrepancy is fabricated. |
| DOC-002 | Money and currency | Invoice exceeds the governing credit amount; cover is written in a second currency with **no exchange rate supplied anywhere**, so it must not be reconciled. |
| DOC-003 | Quantity and description | Packaged goods have **zero** quantity tolerance; a grade contradiction on one certificate; and a `MT` vs `PCS` pair the rulebook gives no conversion factor for, so the honest answer is "cannot be compared". |
| DOC-004 | Deadlines | Shipment after latest date; period-after-shipment calculated from the **actual** shipment date; the due date lands on a closed day and must move; expiry binds separately; one certificate date is `05/03/2026` and is genuinely two different dates. |
| DOC-005 | Transport document | Ports, stipulated consignee, stipulated notify party, prohibited transshipment, prohibited partial shipment, plus marks that differ but are **not stipulated** — a minor finding, not a critical one. |
| DOC-006 | Completeness and defects | A required certificate absent; a signature missing where required; an endorsement defective; a certificate expired before shipment; an invoice amount nobody can read. Four named defects, one honest escalation, and no room for inventing a fifth. |
| DOC-007 | Amendment precedence | Three amendments, one **never accepted**, one superseding another. Governing terms must be derived before anything is examined; documents still carry superseded values. |
| DOC-008 | Compound investigation | An `about`-worded credit buys a real ±10% band, and the invoice sits just outside it, alongside a quantity shortfall, a document dated after the risk attached, a minor marks variance and one unestablishable field. |

**Reference solutions are computed, not asserted.** `benchmark/truth/engine.py` parses the
same rendered document text a model receives and interprets the rulebook against it. Each
scenario declares what its author *intended* to plant; `--validate` fails if the engine
disagrees. During construction this caught seven real benchmark defects — double-counting a
missing document as a dozen unresolved fields, `"NOT ENDORSED"` satisfying an endorsement
requirement, a clean task being made ungradable by inspecting a certificate the credit never
asked for, and prose like `14 days` reaching an `int()` call.

## 3. Grading

Deterministic only. No LLM judge is used or required, per the guide's preference for graders
that are fast, cheap, objective and reproducible by a stranger (p.10).

Per trial, out of 100: recall 25 · precision 20 · rule mapping 15 · evidence traceability 15 ·
severity 10 · uncertainty escalation 10 · output format 5. Pass = total ≥ 70 **and** no cap.

Two structural choices make the numbers mean something:

- **Findings are matched on (code, field), where the field is resolved from the model's own
  citation** through an evidence index built from the rendered documents. A model that cites
  `INV-001 / "Total amount"` is credited whatever words it types in `field`. A model that
  names a field but cites nothing reachable is counted as unsupported. Inventing a
  `document_id` that is not in the package is caught, because the package owns the vocabulary.
- **Severity is a rulebook lookup, not a model opinion**, so the severity dimension measures
  whether the model applied the declared ladder.

Four hard caps:

| Cap | Effect | Reason |
|---|---|---|
| `CRITICAL_FALSE_CLEARANCE` | total → 0 | Missing a critical discrepancy is the catastrophic professional error. |
| `FABRICATED_ON_CLEAN_PRESENTATION` | total → 0 | On a compliant package, any reported discrepancy fails the trial. Partial credit must not be earnable by hallucinating findings. |
| `HALLUCINATED_EVIDENCE` | trial fails, scores stay visible | A fabricated citation is an integrity breach; the itemised breakdown is kept as research data. |
| `WRONG_FINAL_DETERMINATION` | trial fails | The headline call is the outcome. Itemising correctly and concluding `CLEAR` is wrong. |

Partial credit is real, and one observable produces exactly one finding — RULE-AMD-003 runs
last and adds an *alias* code rather than a second finding, so a model that describes a
superseded discharge port as `DOCUMENT_CARRIES_SUPERSEDED_VALUE` instead of
`PORT_OF_DISCHARGE_MISMATCH` is matched, not punished.

### How the grader itself was validated

This is the part the rubric pays 20 points for, so it is machine-checked three ways:

1. **Fixture corpus — 117 checks across the 8 tasks.** Per task: the reference (must pass);
   an alternative valid representation with reordered findings, paraphrased labels, extra
   correct evidence and an unrequested key (must still pass); a missed critical (must zero);
   a missed minor (must cost points but not the trial); a fabricated finding; a hallucinated
   document; a wrong `rule_id`; a flipped severity; evidence that cites the wrong location;
   malformed JSON; a structurally invalid report; blanket escalation of 10 invented fields;
   the guide's named gaming attack — reporting **all 26 declared codes** and hoping; and a wrong final
   determination with every finding otherwise correct.
2. **Mutation testing — 13 mutants.** Each grader lever is individually disabled (tolerance
   free, precision never penalised, evidence traceability free, each cap removed, structural
   schema errors treated as extra keys, prose accepted as output, field matching requiring an
   exact name) and the corpus must go red. A green suite that cannot detect a broken grader
   would be worthless, so `tests/test_mutations.py` asserts detection *and* that the corpus is
   green again once the lever is restored.
3. **Property tests (Hypothesis).** Score stays in [0, 100]; permuting the finding list never
   changes the score; adding fabricated findings never raises it; adding extra *correct*
   evidence never lowers it.

Task hygiene is also enforced, not assumed: `benchmark/validation/lint_tasks.py` fails if any
graded code is not declared by a rule, if any finding's severity differs from its rule's, if
the prompt omits the rulebook or any document, if a graded code was never offered to the
model, or if a brief or author note leaks an answer. It currently reports **18/18 producer
rules exercised** and pins the three codes no task exercises (see §7).

## 4. How to run

Python 3.13 (3.11+ should do). Windows console: output is ASCII-safe.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt   # linux/mac: .venv/bin/pip
.venv/Scripts/python run_eval.py --validate      # the whole proof, no keys, ~seconds
.venv/Scripts/python run_eval.py --write-tasks   # materialise benchmark/tasks/DOC-00N/
.venv/Scripts/python run_eval.py --review-sheet  # regenerate docs/expert-review.md
.venv/Scripts/python run_eval.py --list-rules    # rulebook with severities and codes
.venv/Scripts/python -m pytest tests -q          # 99 tests: domain, graders, mutations, properties
```

Docker (optional, and not required to reproduce anything):

```bash
docker compose run --rm eval     # full proof inside python:3.13-slim, no keys, read-only
docker compose run --rm tests    # the 99-test suite
```

**Verification status — read this before trusting any CI badge.** The image definition is
committed but **unverified**, for two independent reasons:

1. Docker Desktop's daemon was not running on the authoring machine, so `docker compose build`
   never executed here.
2. GitHub Actions cannot currently obtain a runner for this account. This was isolated with a
   canary workflow whose only step was `echo hello`: it also failed in ~2 seconds with zero
   steps, on every job. So the failure is account/runner availability, not this repository's
   configuration — and the `.github/workflows/validate.yml` results below are **not** evidence
   of anything until a runner is available.

What *is* verified is the native path, on Python 3.13.9 with the pinned dependencies below:
`python run_eval.py --validate` (8 tasks, 117 grader fixtures, 18/18 producer rules exercised)
and `python -m pytest tests -q` (109 passing, including 13 grader-lever mutations and 7
edge-configuration mutations that must each be detected). Where the container and CI disagree
with the native run, the native run is authoritative and the container is the bug.

Pinned versions: `requirements.txt` (runtime: pydantic 2.14.2, jsonschema 4.26.0, PyYAML 6.0.3,
httpx 0.28.1, fpdf2 2.9.0, tiktoken 0.14.0, python-dotenv 1.2.4) and `requirements-dev.txt`
(plus pytest 9.2.0, hypothesis 6.170.14).

Live trials (Phase B): copy `.env.example` to `.env`, add keys, then
`python run_eval.py --discover` to pin the model ids your keys can actually reach into
`benchmark/results/models.lock.json`. Model names are **never** hardcoded — an invented id
fails only at the provider, which is the worst place to discover it.

## 5. Layout

```
run_eval.py                the harness entry point
benchmark/
  rulebook/rulebook.yaml   23 authored rules, severities, tolerances, precedence
  generator/               seeded synthetic documents (fpdf2 available for PDF track B)
  truth/                   rulebook interpreter: documents + rules -> ground truth
  graders/                 output contract + deterministic scoring
  validation/              fixture corpus, mutation suite, task linter
  harness/                 provider registry + context-budget gate
  tasks/                   instruction.md | task.toml | environment/ | solution/ | tests/
docs/expert-review.md      dated examiner sign-off record (generated)
tests/                     99 tests
```

Task shape follows the Terminal-Bench/Harbor layout the guide shows (instruction,
environment, solution, tests) but **does not depend on Harbor at runtime** — the guide states
Harbor is optional (p.7), and a judge reproducing this should not need it.

## 6. Models tested and results

**Run date 2026-11-04, panel `panel-02-probe-derived`.** Settings per trial: `temperature=0.0`,
`max_output_tokens=8000`, `reasoning_effort=low` for the gpt-oss family, one prompt built per
task and reused byte-identically across models (prompt SHA-256 is recorded per trial).
3 trials per task per model. Provider: Groq and Google Gemini, OpenAI-compatible endpoints,
model ids as returned by `--discover` on the run date.

| Model | Scored trials | Mean /100 | pass^k tasks | Critical false clearances | Mean latency |
|---|---|---|---|---|---|
| `groq:openai/gpt-oss-20b` | 24 | **73.26** | 5/8 | 5 | — |
| `groq:qwen/qwen3.8-27b` | 8 (quota) | 65.00 | 2/3 | 3 | — |
| `groq:openai/gpt-oss-120b` | 24 | 64.68 | 4/8 | 6 | — |
| `groq:openai/gpt-oss-safeguard-20b` | 24 | 63.37 | 3/8 | 8 | — |
| `groq:qwen/qwen3.6-27b` | 24 | 63.02 | 5/8 | 5 | — |
| `gemini:models/gemini-3.5-flash-lite` | 24 | 43.27 | 3/8 | 12 | — |
| `gemini:models/gemini-flash-lite-latest` | 24 | 35.74 | 2/8 | 14 | — |

**158 scored trials, 97 passed (61%).** No model clears all eight tasks on every trial, and no
model scores near zero everywhere — the eval has headroom at both ends, which is what p.11
requires before a limitation can be claimed.

Not evaluated, with the reason rather than a silent gap: `groq:allam-2-7b` (24 trials
`skipped_context` — measured, it returns HTTP 400 on the ~5,000-token task prompt) and
`gemini:models/gemini-3.6-flash` (10 trials `provider_error`, HTTP 429 quota; abandoned by the
circuit breaker rather than padded with zeros).

### Mean score by dimension, across all 158 scored trials

| Dimension | Mean credit |
|---|---|
| severity classification | 99.4% |
| rule mapping | 99.4% |
| evidence traceability | 96.7% |
| output format | 92.4% |
| precision (no fabrication) | 90.8% |
| **recall (did they find it)** | **80.2%** |
| **uncertainty escalation** | **64.9%** |

## 6a. Failure analysis

The ordering of that table is the finding, and it is not the one the task design
anticipated.

**1. Knowledge is not the bottleneck; coverage is.** Once a model reports a discrepancy it is
almost always right about which rule governs it (99.4%) and about whether it is critical or
minor (99.4%). Those are the judgments an examiner is paid for, and the models perform them
reliably. What fails is noticing the thing in the first place (80.2% recall) and saying "I
cannot establish this" (64.9%). A model that has read the rulebook will apply it correctly to
what it happens to have looked at.

**2. The dominant single failure is currency propagation across documents.**
`CURRENCY_MISMATCH` was the most-missed critical code, 21 times. In DOC-002 the invoice is USD
and the insurance certificate is EUR with no exchange rate supplied anywhere. Models check the
invoice against the credit, report the amount breach, and in their own summary assert that
"currency complies" — having verified it on one document and generalised to the package.
Missed codes ranked: `CURRENCY_MISMATCH` 21, `INSURANCE_DATED_AFTER_SHIPMENT` 9, then
`PRESENTATION_AFTER_EXPIRY`, `AMOUNT_EXCEEDS_CREDIT`, `DOCUMENT_MISSING` and
`PRESENTATION_AFTER_DEADLINE` at 6 each.

**3. Uncertainty is the weakest dimension, and it fails in both directions.** Some trials
escalate nothing and answer confidently about an illegible field; others dump every field into
`unresolved_questions`, which the grader treats as blanket escalation and penalises. This is
the dimension the professional outcome depends on most and the one models handle worst.

**4. Critical false clearances are frequent, not rare** — 5 to 14 per model out of 24 trials.
Under the cap that forces a trial to 0, these are the difference between "this model is
usable with review" and "this model would have paid against a bad presentation".

### Open question I am not resolving by assertion

On DOC-005 trial 3, `gpt-oss-safeguard-20b` reported `PARTIAL_SHIPMENT_NOT_PERMITTED` — the
correct code — and was still marked as having missed it, because its citation pointed at
`Quantity Shipped` while the ground truth's required evidence is the two bill-of-lading numbers.
That may be a model that got the finding but justified it with the wrong evidence, or it may be
my matcher being over-strict about which location counts, and the second reading would mean the
recall figure above is pessimistic. It is the same class of bug as the citation-resolution defect
already fixed once, so it is being investigated before the recall number is treated as final.
Until then this number should be read as an upper bound on the model's error.

## 7. Limitations, stated plainly

- **No closed frontier model is reachable on the access available, and that is now measured
  rather than assumed.** Probed on 2026-11-04 with real requests (`run_eval.py --probe`,
  evidence in `benchmark/results/probe.json`):

  | Route | Result |
  |---|---|
  | OpenRouter | HTTP **402 — account never purchased credits**. It advertises 452 models
    including Claude and GPT families, but listing is not entitlement, so none are callable. |
  | Gemini | **4 callable**: `gemini-3.5-flash-lite`, `gemini-flash-lite-latest` (both ~20 s
    latency). Pro tier returns **429 quota exceeded**; `gemini-3.1-flash-lite*`, `3.7-flash`,
    `gemini-flash-latest` return **503**; `gemini-3-flash-preview`, `3.5-flash`, `3.8-flash`
    return **HTTP 200 with no usable text**. |
  | Groq | **5 callable**: `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`,
    `qwen/qwen3.6-27b`, `allam-2-7b` (capability floor). Note `llama-3.3-70b-versatile` and
    `llama-3.1-8b-instant` are **not** on this key, contrary to the published models page. |
  | Ollama local | daemon not running; no models pulled. |

  So the panel is 2 vendors and ~6 models spanning 7B to 120B, with one closed family (Google)
  at its lightweight tier. The guide asks for frontier models; this is a real cross-family
  capability spread but not GPT-5/Claude-class, and the README will not pretend otherwise.
  Adding OpenRouter credits would change that immediately.

- **Reasoning-model output budgets are a result-integrity hazard, found by probing.** With
  `max_output_tokens=64`, Groq's `gpt-oss` spends the entire budget on its reasoning trace and
  returns HTTP 200 with an **empty `content`**. Graded as-is, that is a 0 score recorded as a
  model failure when it is a transport artifact — exactly the false-fail the guide warns about
  (p.9, p.11). Two defences now exist in `benchmark/harness/client.py`: it falls back through
  `content` → `reasoning` → `reasoning_content` and records which field it read, and it
  **raises rather than returning** if no field carries text, so an empty completion can never
  reach the grader. At a 200-token budget `gpt-oss-120b` returns `{"ok": true, "n": 2}`
  correctly. Separately, `qwen3.6-27b` emits literal `<think>` tags inside `content`, which
  the Phase B extraction layer must strip before JSON parsing — otherwise a correct answer is
  graded as unparseable.
- **Three declared codes are exercised by no task**: `DOCUMENT_DATED_AFTER_PRESENTATION`,
  `INSPECTION_DATED_AFTER_SHIPMENT`, `QUANTITY_TOLERANCE_EXCEEDED`. They are pinned in
  `tests/test_task_packaging.py` so the list cannot grow silently. They are *rules the
  rulebook states* that no scenario plants, so results should not be read as validating them.
- **Severity is a declared ladder, not an ICC ruling.** It mirrors standard examination
  practice but is authored for this benchmark. Its expert review status is tracked in
  `docs/expert-review.md`; if the ladder changes, every affected severity grade changes with
  it, which is the point of making it a lookup.
- **Track A only.** Grading runs on normalised document text with page/line anchors. Raw-PDF,
  OCR and multimodal input is a separate track and is not built, so extraction failure cannot
  be confused with reasoning failure — and equally, no claim about visual document handling is
  made.
- **The rulebook is original text.** No UCP 600 or ISBP 745 wording is reproduced, so this
  measures rule application under a supplied standard rather than recall of licensed material.
- **A local Ollama track exists by design, not as a headline result.** CPU-only hardware makes
  small local models a calibration engine and the free capability floor, not a frontier proxy.

## 8. Provenance and AI use

- **Existed before the challenge window:** nothing in this repository. It is a fresh, isolated
  project at `Desktop/micro1` with its own git history. Concepts reused from my own earlier
  hackathon project (a tender-compliance system) are its *evaluation shape* — weighted
  multi-dimensional grading with numeric tolerance and coarse status buckets, ground-truth case
  JSON, an isolated deterministic evaluation mode. No code, task, document or rule was copied;
  that project is not part of this submission.
- **Built during the window:** everything here.
- **No benchmark is adapted.** Task *shapes* are informed by the published examples the guide
  itself cites (Terminal-Bench task layout, τ-bench's end-state grading and pass^k, GDPval's
  professional-deliverable framing). No task, prompt or answer is copied from any existing
  benchmark.
- **AI assistance:** the architecture discussion, this README's first draft, the grader and the
  engine were produced with an AI coding agent. Every **task defect, ground truth, severity and
  grading rule is machine-derived from an authored rulebook and is subject to human examiner
  sign-off in `docs/expert-review.md`**, which is the reviewer's own judgement, not the agent's.
  The agent's design proposals were audited against the Participant Guide before adoption, and
  two of its recommendations were rejected: an LLM-as-judge primary grader, and a distributed
  platform stack as the critical path.
- **Data:** entirely synthetic. Banks (Crescent Trading Bank, Deltamark Commercial Bank,
  Halcyon Trade Finance), companies (Meridian Export House, Northgate Industrial Holdings),
  carriers (Amber Wave Lines), credit and document numbers, amounts, dates and routes are
  invented. No confidential, client or personal data, and no credentials, appear anywhere.

## 9. Security posture

`.env` is gitignored; `.env.example` carries names only. Providers are read from the
environment at run time and no key is ever written into results, transcripts or logs.
`--discover` records model ids and rate-limit metadata, not credentials.
