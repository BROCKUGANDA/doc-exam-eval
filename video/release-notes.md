## DOC-EXAM walkthrough

~1:50 at 1920×1080/30fps: the evaluation laboratory for documentary-credit examination, end to
end.

- the eight expert tasks, and how the ground truth is **computed** rather than typed in
- the grader, its five hard caps, and the 117 fixtures and 15 mutation levers that prove the
  gate can actually fail
- the platform: artifact API, console, transcript view, and the read-only edge
- the completed panel: 168 scored trials, 61.9% passing — including the two defects that were
  in **my grading**, not in the models
- how to reproduce all of it from a clean clone with no API key

Everything in the film is generated from this repository's own artifacts (README §4a): the
narration is edge-tts, the screen images are captures of this platform running with synthetic
data, and every number on screen comes from `benchmark/results/results.json`, which
`python scripts/write_readme_tables.py` regenerates from the stored transcripts.

The MP4 is deliberately **not** inside the submission ZIP, per the instructions. This link is
the deliverable, and it opens without a login or an access request.
