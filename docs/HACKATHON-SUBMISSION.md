# DOC-EXAM — Hackathon judge pack

## What to evaluate

DOC-EXAM is a deterministic benchmark for documentary-credit examination. It tests whether a model can:

1. Detect material discrepancies across a synthetic letter-of-credit document package.
2. Cite the exact source document and field supporting each finding.
3. Apply the supplied rulebook and severity ladder.
4. Distinguish harmless variation from discrepancy.
5. Abstain or escalate when the supplied evidence cannot establish an answer.

## Judge path (5–7 minutes)

1. Run `python run_eval.py --validate` from the repository root (no API key, database, Docker or web server required). If a verified public console URL is supplied in the official submission entry, inspect its overview metrics as an additional step; otherwise do not assume a public deployment exists.
2. Open **Tasks** and inspect DOC-001 (the clean control) and DOC-008 (compound investigation).
3. Open **Results** and compare models by mean score, pass@k, pass^k, critical false clearances and latency.
4. Open a trial transcript and verify that findings cite evidence present in the package.
5. Open **Integrity** and inspect the fixture corpus, mutation testing and hard caps.
6. Reproduce the offline proof using the commands below. The console is supplementary; the offline proof is the required reproducible path.

## Reproduction

Python 3.11+ (3.13 recommended):

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\python -m pip install -r requirements-dev.txt
.venv\\Scripts\\python run_eval.py --validate
.venv\\Scripts\\python -m pytest tests -q
# macOS / Linux: replace .venv\\Scripts\\python with .venv/bin/python
```

The validation command is designed to run without provider credentials, a database, Docker or a web server. Live model trials are a separate, optional phase and require provider credentials.

## Evidence snapshot in the submitted README

- 8 task scenarios; 23 authored rules; 18/18 producer rules exercised.
- 117 deterministic grader fixtures and 15 mutation tests.
- 168 native tests reported passing in the verification record.
- 168 scored model trials across 7 callable model configurations.
- Mean panel score: 58.84/100; 104/168 trials passed (61.9%).
- Critical false clearances: 56/168 trials (33.3%).

These figures are historical evidence from the recorded panel run, not a claim that every model or provider is currently available. The dashboard reads the checked-in result artifacts; a new run must be separately dated and versioned.

## Important limitations to disclose

- The panel covers Groq and Google Gemini lightweight models, not a broad GPT/Claude frontier panel.
- The examiner severity sign-off remains outstanding. The rulebook severity ladder is authored benchmark policy, not an ICC ruling.
- Track A evaluates normalized text with page/line anchors. Raw PDF, OCR and multimodal extraction are not implemented.
- Three declared discrepancy codes are not exercised by the eight shipped tasks.
- Public deployment is not verified until the demo hostname and Cloudflare tunnel credentials are configured and tested.
- The benchmark is research software, not a bank's production payment decision system.

## Submission integrity

- Do not describe an unrun workflow as passing CI.
- Do not call a provider error a model failure.
- Do not imply examiner approval until a qualified reviewer signs the review sheet.
- Do not publish API keys, tunnel tokens, local environment files or private data.
- Keep the submitted video accessible without login or access requests.
