# DOC-EXAM — YouTube upload kit

## Video asset

Existing walkthrough: `doc-exam-walkthrough.mp4`  
Recorded duration: 109.1 seconds  
Format: 1920×1080, 30 fps  
Narration: 24 timed beats; synthetic benchmark data only.

Existing public release asset:
https://github.com/BROCKUGANDA/doc-exam-eval/releases/download/v1.0.0/doc-exam-walkthrough.mp4

## Suggested title

DOC-EXAM | Can AI Examine a Letter of Credit? — Evidence-First Benchmark

## Description

Can an AI model reliably examine a documentary-credit presentation — and know when the evidence is not enough?

DOC-EXAM is a reproducible AI evaluation benchmark for trade-finance document examination. It measures four capabilities together:

• Discrepancy detection across a package of documents  
• Evidence traceability to the source document and field  
• Correct application of a supplied rulebook and severity ladder  
• Uncertainty handling: refusing to invent facts when evidence is missing, ambiguous or unreadable

The benchmark includes eight synthetic scenarios, deterministic reference answers, a deterministic grader, adversarial fixtures, mutation testing and model comparison results.

Explore the project:
Source code: https://github.com/BROCKUGANDA/doc-exam-eval
Walkthrough download: https://github.com/BROCKUGANDA/doc-exam-eval/releases/download/v1.0.0/doc-exam-walkthrough.mp4
Benchmark console: [ADD VERIFIED PUBLIC DEMO URL]

Reproduce the benchmark:
python run_eval.py --validate

Important limitations: the recorded panel uses Groq and Google Gemini lightweight model routes; it is not a comprehensive frontier-model comparison. The severity ladder still requires qualified examiner sign-off. The current evaluation track uses normalized text and does not claim raw-PDF/OCR or multimodal document extraction. DOC-EXAM is a research benchmark, not a production bank payment-decision system.

Built for the micro1 Eval Hackathon 2026.

#AI #AIEvaluation #LLMEvaluation #TradeFinance #DocumentaryCredit #Benchmark #AIResearch

## Upload settings

- Visibility: Unlisted until reviewed; switch to Public when the hackathon submission is ready.
- Category: Science & Technology
- Audience: Not made for kids
- Language: English
- License: Standard YouTube License
- Embedding: Allow
- Comments: Hold potentially inappropriate comments for review
- Thumbnail: use the repository's Open Graph image after confirming the final visual and dimensions.
- Chapters: not necessary for a 1:49 walkthrough.

## Publication gate

The file is already available as a public GitHub release download, but it has not been uploaded to YouTube by this workflow. Publishing requires the owner's authenticated YouTube channel and an upload authorization. After upload, replace the demo placeholder above with the actual watch URL and verify playback in a signed-out/incognito browser.
