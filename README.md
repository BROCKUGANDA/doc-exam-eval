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

**Key finding.** Knowledge is not the bottleneck — coverage is. Once a model reports a
discrepancy it names the governing rule correctly 97.6% of the time and the severity correctly
97.6% of the time, but it finds only 79.4% of what is there and volunteers "I cannot establish
this" in 60.7% of the cases where something genuinely cannot be established. The two
most-missed findings after currency propagation are the *minor* ones — a variance the credit
never stipulated — which models either ignore or escalate, when the rule asks for a minor
finding. Full analysis in §6a.

**Video walkthrough.** 1:49, narrated, covering the platform end to end:
<https://github.com/BROCKUGANDA/doc-exam-eval/releases/tag/v1.0.0> — the file itself is at
<https://github.com/BROCKUGANDA/doc-exam-eval/releases/download/v1.0.0/doc-exam-walkthrough.mp4>.
Both open with no login and no access request, which is what the rules require; GitHub serves
release assets as a download rather than a stream, so the link hands the judge the file. It is
not inside this ZIP, per the instructions. How it was built is in §4a.

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

Five hard caps:

| Cap | Effect | Reason |
|---|---|---|
| `CRITICAL_FALSE_CLEARANCE` | total → 0 | Missing a critical discrepancy is the catastrophic professional error. |
| `FABRICATED_ON_CLEAN_PRESENTATION` | total → 0 | On a compliant package, any reported discrepancy fails the trial. Partial credit must not be earnable by hallucinating findings. |
| `HALLUCINATED_EVIDENCE` | trial fails, scores stay visible | A fabricated citation is an integrity breach; the itemised breakdown is kept as research data. |
| `WRONG_FINAL_DETERMINATION` | trial fails | The headline call is the outcome. Itemising correctly and concluding `CLEAR` is wrong. |
| `UNPARSEABLE_OUTPUT` | total → 0, only the format dimension is reported | An output that is not the required contract cannot be graded on content, and saying so is honest rather than quietly scoring the prose. |

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
2. **Mutation testing — 15 mutants.** Each grader lever is individually disabled (tolerance
   free, precision never penalised, evidence traceability free, each cap removed, structural
   schema errors treated as extra keys, prose accepted as output, matching reverted to two
   tiers, unknown credit counting repeats) and the detectors must go red. A green suite that
   cannot detect a broken grader would be worthless, so `tests/test_mutations.py` asserts
   detection *and* that everything is green again once the lever is restored. Detection is the
   fixture corpus **plus** the transcript-found regression tests, because two of the bugs below
   are relationships *within* one report that no per-fixture assertion can express. One lever
   was deleted rather than kept: after the matching fix, breaking exact field-name matching no
   longer changed any outcome, so advertising it would have claimed proof of something the suite
   could no longer demonstrate.
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
.venv/Scripts/python -m pytest tests -q          # 180 tests: domain, graders, mutations, properties, API, edge
.venv/Scripts/python scripts/write_readme_tables.py  # regenerate the §6 result tables from results.json
```

Docker is optional, and not required to reproduce anything:

```bash
docker compose build eval tests api web         # four images
docker compose run --rm eval                    # the whole proof, python:3.13-slim, no keys, read-only
docker compose run --rm tests                   # 170 of the 180 tests; see the scope note below
docker compose --profile platform --profile edge up -d    # api + console behind the hardened edge
curl -s -o /dev/null -w '%{http_code}\n' localhost:20080/results
```

**Verification status — what was actually run, and where it stopped.**

Verified in containers on this machine, 2026-11-05:

| Claim | How it was checked |
|---|---|
| `docx-eval` reproduces the proof from a clean build | `docker compose run --rm eval` → `PASS tasks=8 fixtures=117 rules_exercised=18/18`, read-only root, no keys, no network |
| `docx-tests` runs the suite | The 2026-11-05 container run passed 158 tests. The current suite has 180 cases: 170 belong to the container target, and `tests/test_submission.py` (10 tests) runs natively because it packs the working tree with `git ls-files`. A current container rerun was unavailable because the Docker daemon is not running. |
| `docx-api` serves the evidence | builds; runs read-only as uid 10001; `/healthz` 200, `/api/v1/results` 200, `/api/v1/tasks/DOC-001/reference` **404**, `/api/v1/trials` → `{"count": 0, "limit": 500, "offset": 0, "trials": []}` — absent, not invented; list pages cap at 500 rows |
| `docx-console` renders | builds; all seven pages return 200 through Caddy |
| The edge really is read-only | `POST` and `DELETE` on `/api/*` → **403 `READ_ONLY_HOST`** before reaching FastAPI; `GET` → 200; CSP, HSTS, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` present |
| The console's public surface | `/`, `/tasks`, `/tasks/DOC-005`, `/results`, `/transcript`, `/rulebook`, `/integrity` → 200; `/sitemap.xml` 200; `/robots.txt`, `/llms.txt`, `/og-image.png`, `/favicon-32x32.svg` → 200 with correct `Content-Type` |

That last row was false when it was first checked. `robots.txt`, `llms.txt` and the icons
returned the Next 404 page in the container while working perfectly under `next dev`, because
`frontend/Dockerfile` copied `.next/standalone` and `.next/static` but not `public/` — and
standalone output does **not** inline `public/`. A build that passes locally is not a deploy.

**Not verified, and it matters:** GitHub Actions cannot obtain a runner for this account.
Re-checked on every push through 2026-11-05: each job finishes in ~3 seconds with `"steps": 0`,
`conclusion: failure` and no log (`gh api .../actions/runs/<id>/jobs`), including a canary
workflow whose only step was `echo hello`. That is runner availability, not this repository's
configuration, and it means `.github/workflows/validate.yml` is **not** evidence of anything.
The table above is local container evidence, not CI evidence.

What *is* verified natively, on Python 3.13.9 with the pinned dependencies below:
`python run_eval.py --validate` (8 tasks, 117 grader fixtures, 18/18 producer rules exercised)
and `python -m pytest tests -q` (180 passing: 14 grader-lever mutants, one evidence-index mutant,
12 edge-configuration mutants, API path and pagination checks, and the cold-import and
README-freshness gates). Where a container
and the native run disagree, the container is the bug.

**Deployment state as of 2026-11-05.** The stack is running locally: `api`, `web` and `caddy`
up, reachable at `http://localhost:20080`, with the read-only policy enforced at the edge.
**There is no public URL yet, and the reason is one credential I do not have:** the Cloudflare
tunnel needs `CLOUDFLARE_TUNNEL_TOKEN` in `.env` (see `.env.example`), and `DEMO_HOSTNAME` /
`STUDIO_HOSTNAME` to point the ingress at. With those three values, `docker compose --profile
public up -d` publishes the evidence host through Cloudflare's WAF/CDN with no inbound port on
the origin. Until then the console exists only on this machine, and the submission link is the
video on the GitHub release rather than a hosted app.

The tunnel token was deliberately never committed, never written into `docker-compose.yml` and
never included in the ZIP: `scripts/make_submission.py` refuses on a JWT-shaped token wherever
it appears, and `scripts/check_edge.py` fails the repo if a literal credential shows up in any
edge file.

Four of the six container rows above were **false** when this section was first written, and
only running the stack found them: the api image could not build (a `COPY` of two requirement
files into one directory), the console image was built against a Windows-specific standalone
layout, the read-only boundary did not fire at all because Caddy sequences `respond` after
`handle` no matter where they are written in the file, and the console's `public/` assets were
never copied into the runner image so `robots.txt` and `llms.txt` 404ed in the container while
working under `next dev`.

Pinned versions: `requirements.txt` (runtime: pydantic 2.14.2, jsonschema 4.26.0, PyYAML 6.0.3,
httpx 0.28.1, fpdf2 2.9.0, tiktoken 0.14.0, python-dotenv 1.2.4) and `requirements-dev.txt`
(plus pytest 9.2.0, hypothesis 6.170.14).

Live trials (Phase B): copy `.env.example` to `.env`, add keys, then
`python run_eval.py --discover` to pin the model ids your keys can actually reach into
`benchmark/results/models.lock.json`. Model names are **never** hardcoded — an invented id
fails only at the provider, which is the worst place to discover it.

## 4a. The walkthrough video, and how to rebuild it

~1:50 at 1920×1080/30fps, narrated, covering the platform end to end. It is generated from
the same artifacts as everything else, so it cannot drift from the results it shows.

```bash
.venv/Scripts/python -m pip install -r requirements-video.txt   # edge-tts only
.venv/Scripts/python scripts/make_narration.py                  # 24 clips + measured durations
.venv/Scripts/python scripts/write_video_composition.py         # emits video/film/*.html
cd video/film && npx hyperframes check && npx hyperframes render
```

| Piece | Source of truth |
|---|---|
| Script | `video/beats.json` — 24 beats, one sentence each, ~19 words |
| Voice | edge-tts `en-US-AndrewMultilingualNeural` at `+0%` rate: no key, no account, and a normal-paced natural read rather than a chipmunk default |
| Timing | each beat's clip length is read from the mp3 frame headers, so the narration *is* the clock; the picture, the caption and the next scene all take their start from it |
| Captions | the sentence boundaries edge-tts reports, so the line changes when the voice does |
| Screens | real captures of the running stack, taken through the Caddy edge at `localhost:20080` |

Two things worth saying about it.

**The screenshots found a production bug.** Captured through the edge, every page rendered as
an empty dark canvas; captured from the origin directly, it rendered unstyled but present. The
cause was my own `Content-Security-Policy`: `script-src 'self'` blocks the inline flight
scripts Next 15 uses to mount the server-rendered page, so a strict browser saw nothing. The
policy now allows `'unsafe-inline'` for scripts and keeps `object-src 'none'`,
`frame-ancestors 'none'`, `base-uri 'self'` and `form-action 'self'` — the parts that do
protect a read-only evidence host. A hardened header that blanks the product is not hardening.

**No music.** There is no licensed music source available on this access (no paid account, and
the skill forbids synthesised tones), so the bed is silence under the narration. To add one:
drop a file at `video/film/assets/music.mp3`, add one `<audio>` clip to `index.html` spanning
the root duration at `data-volume="0.14"`, and re-render.

**What the render did not do, stated plainly.** The frame capture succeeded; the render's own
audio stage failed twice on this machine with `[FFmpeg] ffprobe deadline` while assembling, so
the shipped file was produced by the first (successful) render and then loudness-normalized
with `ffmpeg` rather than by a third re-render:

```bash
ffmpeg -i in.mp4 -c:v copy -af loudnorm=I=-16:TP=-1.5:LRA=11 -c:a aac -b:a 192k out.mp4
```

Measured with `hyperframes audio` before and after: **-17.8 → -16.1 LUFS integrated, true peak
-1.5 dBTP, zero clipped samples**, duration 109.1 s with the voice tail ending at 107.90 s,
which is the narration total in `video/manifest.json`. The composition carries the same gain
(`data-volume="1.38"`), so a clean re-render on a machine where the audio stage works produces
the same level rather than a quieter one.

**Where the file lives.** GitHub serves release assets as an attachment, so the link downloads
the MP4 instead of streaming it. If a streaming page is wanted, `docs/video/` on a `gh-pages`
branch with the same file and a `<video>` element is about three commands — not done here
because it changes repository settings, and the rule that matters (opens with no login and no
access request) is already met.

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
  results/                 results.json/md, probe.json, models.lock.json, runs/*.jsonl (evidence)
backend/                   FastAPI artifact store — no database, no ORM, reads the tree above
frontend/                  Next 15 console: tasks, results, transcript, rulebook, integrity
infra/caddy/Caddyfile      read-only judge host + separate studio host, hardened headers
infra/cloudflared/         tunnel ingress by hostname, no inbound ports, no token in the file
scripts/
  check_edge.py            the edge gate (snippet resolution, site-key defaults, credential scan)
  write_readme_tables.py   regenerates the §6 tables from results.json; `--check` pins them
  make_submission.py       builds the submission ZIP, refusing on secret-shaped strings
  make_narration.py        per-beat edge-tts clips + measured durations for the walkthrough
docs/expert-review.md      dated examiner sign-off record (generated)
tests/                     168 tests
```

Task shape follows the Terminal-Bench/Harbor layout the guide shows (instruction,
environment, solution, tests) but **does not depend on Harbor at runtime** — the guide states
Harbor is optional (p.7), and a judge reproducing this should not need it.

## 6. Models tested and results

**Panel `panel-02-probe-derived`, run 2026-11-04 → 2026-11-05 07:32 UTC.** Settings per trial:
`temperature=0.0`, `max_output_tokens=8000`, `reasoning_effort=low` for the gpt-oss family, one
prompt built per task and reused byte-identically across models (prompt SHA-256 is recorded per
trial). 3 trials per task per model. Provider: Groq and Google Gemini, OpenAI-compatible
endpoints, model ids as returned by `--discover` on the run date.

<!-- RESULTS:AUTOGEN start -->
Panel `panel-02-probe-derived`, temperature 0.0, 3 trials per task per model. These four tables are regenerated by `python scripts/write_readme_tables.py`; the prose around them is not.

### Models with scored trials

| Model | Scored trials | Mean /100 | pass@k tasks | pass^k tasks | Critical false clearances | Mean latency |
|---|---|---|---|---|---|---|
| `groq:openai/gpt-oss-20b` | 24 | **72.43** | 7/8 | 5/8 | 5 | 3.61s |
| `groq:qwen/qwen3.6-27b` | 24 | 70.52 | 6/8 | 6/8 | 3 | 15.62s |
| `groq:openai/gpt-oss-safeguard-20b` | 24 | 67.10 | 7/8 | 4/8 | 7 | 5.66s |
| `groq:openai/gpt-oss-120b` | 24 | 64.68 | 6/8 | 4/8 | 6 | 4.48s |
| `groq:qwen/qwen3.8-27b` | 24 | 58.16 | 5/8 | 5/8 | 9 | 3.95s |
| `gemini:models/gemini-3.5-flash-lite` | 24 | 43.27 | 4/8 | 3/8 | 12 | 5.12s |
| `gemini:models/gemini-flash-lite-latest` | 24 | 35.74 | 4/8 | 2/8 | 14 | 5.0s |

**168 scored trials, 104 passed (61.9%), mean 58.84/100.**

### Mean credit by dimension, across all scored trials

Credit is the mean of each dimension's ratio, so 100% means the models earned every point that dimension offers. Sorted worst first.

| Dimension | Mean credit |
|---|---|
| **uncertainty escalation** | **60.7%** |
| **recall (did they find it)** | **79.4%** |
| precision (no fabrication) | 90.5% |
| output format | 92.3% |
| evidence traceability | 94.5% |
| rule mapping | 97.6% |
| severity classification | 97.6% |

### Most-missed findings across the whole panel

| Most-missed code | Trials |
|---|---|
| `CURRENCY_MISMATCH` | 21 |
| `BENEFICIARY_ADDRESS_VARIANT` | 20 |
| `SHIPPING_MARKS_MISMATCH` | 19 |
| `INSURANCE_DATED_AFTER_SHIPMENT` | 12 |
| `AMOUNT_PRESENTATION_DEFECT` | 11 |
| `PRESENTATION_AFTER_EXPIRY` | 6 |

### Hard caps fired

| Cap | Trials |
|---|---|
| `CRITICAL_FALSE_CLEARANCE` | 56 |
| `UNPARSEABLE_OUTPUT` | 4 |
| `FABRICATED_ON_CLEAN_PRESENTATION` | 2 |
| `WRONG_FINAL_DETERMINATION` | 2 |
| `HALLUCINATED_EVIDENCE` | 2 |
<!-- RESULTS:AUTOGEN end -->

Not evaluated, with the reason rather than a silent gap: `groq:allam-2-7b` (24 trials
`skipped_context` — measured, it returns HTTP 400 on the ~5,000-token task prompt) and
`gemini:models/gemini-3.6-flash` (10 trials `provider_error`, HTTP 429 quota; abandoned by the
circuit breaker rather than padded with zeros).

Headroom at both ends is what p.11 requires before a limitation may be claimed: no model clears
all eight tasks on every trial, and no model scores near zero everywhere.

## 6a. Failure analysis

The ordering of the dimension table is the finding, and it is not the one the task design
anticipated.

**1. Knowledge is not the bottleneck; coverage is.** Once a model reports a discrepancy it is
almost always right about which rule governs it (97.6%) and about whether it is critical or
minor (97.6%). Those are the judgments an examiner is paid for, and the models perform them
reliably. What fails is noticing the thing in the first place (79.4% recall) and saying "I
cannot establish this" (60.7%). A model that has read the rulebook applies it correctly to what
it happens to have looked at. Five of the seven models score exactly 100% on both rule mapping
and severity, and the lowest model on either is 87.5% — those two dimensions do not separate the
panel at all. Recall and uncertainty separate it completely.

**2. The most-missed item is a currency propagation failure.** `CURRENCY_MISMATCH` was missed
21 times, the only critical code at the top of the ranking. In DOC-002 the invoice is USD and
the insurance certificate is EUR with no exchange rate supplied anywhere. Models check the
invoice against the credit, report the amount breach, and then assert in their own summary that
"currency complies" — having verified one document and generalised to the package.

**3. The second and third are the *minor* findings, and that is the interesting part.**
`BENEFICIARY_ADDRESS_VARIANT` (20) and `SHIPPING_MARKS_MISMATCH` (19) both come from
`RULE-DESC-002`: where the credit does **not** stipulate a field, documents that describe it
differently create an ambiguity, not a breach — report it as minor, never escalate it, never
refuse for it. Models are silent. The instinct is that a discrepancy list contains breaches, so
a non-stipulated variance is either ignored or inflated to critical, and the rule asks for the
one thing the models are least inclined to produce: a *minor* finding that exists precisely
because nothing was stipulated. This is also where the design was wrong: I built these tasks to
catch over-escalation and they are, in practice, mostly catching under-reporting.

**4. Uncertainty is the weakest dimension, it is bimodal, and that exposes a limit of my own
design.** Across the 168 scored trials the uncertainty ratio is never partial: 102 trials earned
1.0 and 62 earned 0.0. Six of the seven models land on exactly 62.5% mean credit, which is not
seven models independently converging — it is a dimension that can only be switched on or off.
The cause is in the task pack: only 4 of the 8 tasks contain a genuinely open field, and each
contains exactly one, so the ratio is `0/1`, `1/1`, or a vacuous 1.0 on the tasks with nothing
open. On the 83 trials that ran a task with one open unknown, **21 flagged it and 62 did not** —
54 escalated nothing at all and answered confidently about something the engine could not
compare, and 8 escalated something invented instead.

Read the strong version of that: models do not escalate *partially*. Either the open question
occurs to them or it does not. And read the weak version, which is mine: a benchmark dimension
that is binary across the panel cannot separate "sometimes knows when to stop" from "never
knows" — the fix is a task with several unknowns of differing kinds, which is the first change
I would make with more quota.

**5. Critical false clearances are frequent, not rare** — 56 of 168 scored trials (33%), 3 to 14
per model out of 24. Under the cap that forces a trial to 0, that is the difference between "this
model is usable with review" and "this model would have paid against a bad presentation."

### Three grader defects the transcripts exposed — and why that is a result, not an embarrassment

Each of these would have been published as a *model* limitation. All three were found by reading
raw outputs against scorecards, and each is now a mutation lever, so the fix is protected by
something that can fail.

| Defect | What it did | Evidence | Now proven by |
|---|---|---|---|
| Reasoning budget consuming the completion | with no `reasoning_effort` and a 3,000-token ceiling, the models wrote thinking and never wrote an answer. 31 of 183 panel-1 trials had an empty `content` field and the adapter had to read `reasoning` instead; 72 of 183 finished at the output ceiling; 134 scored 0. `gpt-oss-20b` averaged **8.33** and `qwen3.6-27b` **0.00** | `settings.content_field` and `completion_tokens_reported` per trial in `benchmark/results/runs/panel-probe-derived.jsonl` | panel 1 is retained but invalidated (`PANEL_VERSION=02`); `reasoning_effort=low` is recorded in each trial's settings, and all 168 panel-2 trials returned `content`. Same transcripts: 72.43 and 70.52 |
| Citation resolution requiring an exact label | a location quoted with its value (`Total amount: USD 105,000.00`) resolved to nothing, so correct findings scored zero traceability | a live `gpt-oss` transcript that had found the defect | `citation_resolution_reverted_to_exact_match` |
| Unknown credit counting repeated questions | one trial asked the same unanswerable question three times with different document pairs and was paid 30 points on a 10-point dimension: **total 102.5 / 100** | `gpt-oss-20b`, DOC-003, trial 1 | `uncertainty_credit_counts_repeats`, plus `test_repeating_one_unknown_earns_one_credit_not_three` and a `total <= 100` assertion on every reference |

The third is the reason the panel mean moved *down* when the grader was corrected: part of the
earlier numbers was my own arithmetic, not the models' performance.

A correction I owe the reader: an earlier draft of this section claimed `gpt-oss-safeguard-20b`
found `PARTIAL_SHIPMENT_NOT_PERMITTED` on DOC-005 and was marked as having missed it. Re-checking
the stored transcripts says otherwise — it reported that code in all three trials and it was
credited in all three. What it actually missed, twice, was `SHIPPING_MARKS_MISMATCH`, which it
never mentioned. The matcher was still loosened (the third matching tier, so a correct finding
with a weak citation earns recall and loses traceability rather than losing both) but that was a
design change, not the rescue of a wrongly-scored trial. `--regrade` reproduces every number here
from the transcripts without spending a token.

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

  So the panel is 2 vendors and 7 models with scored trials spanning 7B to 120B (9 recorded, 2
  of them without a single scored trial — see §6), with one closed family (Google)
  at its lightweight tier. The guide asks for frontier models; this is a real cross-family
  capability spread but not GPT-5/Claude-class, and the README will not pretend otherwise.
  Adding OpenRouter credits would change that immediately.

- **The uncertainty dimension is binary as shipped, which weakens the claim built on it.** Only
  4 of the 8 tasks contain a genuinely open field and each contains exactly one, so the
  dimension records "escalated or did not" rather than a calibrated degree of epistemic honesty.
  Six of the seven models land on the identical 62.5% mean credit — not seven independent
  convergent results, one structural ceiling. The fix is a task with several unknowns of
  different kinds (ambiguous date, uncomparable quantity, unreadable value) so partial
  escalation becomes measurable; it is the first change I would make with more quota, and §6a
  point 4 says so rather than leaving it to the reader to notice.

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
- **The examiner sign-off is still outstanding, and that is a human job, not mine.** The
  review sheet is generated with every rule, its declared severity, the codes it governs and
  the verdict columns left empty on purpose: `python run_eval.py --review-sheet` writes
  [`docs/expert-review.md`](docs/expert-review.md), and a qualified trade-finance reviewer
  fills in the severity verdicts and initials them with a date. Until those rows are filled,
  the severity ladder is *my* judgement, not an examiner's, and §6a reports it as such. The
  machine can prove the grading is deterministic and self-consistent; it cannot make the
  professional call.
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
- **Data:** entirely synthetic. Banks (Crescent Trading Bank, Deltamark Commercial Bank),
  companies (Meridian Export House, Meridian Trade Services, Northgate Industrial Holdings),
  carriers (Amber Wave Lines), credit and document numbers, amounts, dates and routes are
  invented. No confidential, client or personal data, and no credentials, appear anywhere.
- **The walkthrough video:** the narration text is written here, in `video/beats.json`, and the
  voice is edge-tts (Microsoft's public text-to-speech endpoint), which needs no account and
  no key. The screen images are captures of this repository's own running platform, with
  synthetic data only. The composition is generated from the measured length of each narration
  clip (§4a), so the film cannot assert a number the artifacts do not contain.

## 9. Security posture

`.env` is gitignored; `.env.example` carries names only. Providers are read from the
environment at run time and no key is ever written into results, transcripts or logs.
`--discover` records model ids and rate-limit metadata, not credentials.
