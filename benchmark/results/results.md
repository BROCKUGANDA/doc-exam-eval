# Results

Panel `panel-probe-derived` · 3 trials per task · temperature 0.0

| Model | Tasks covered | Mean score | pass@k tasks | pass^k tasks | Critical false clearances | Mean prompt tok | Mean latency |
|---|---|---|---|---|---|---|---|
| `gemini:models/gemini-3.5-flash-lite` | 8 | 43.89 | 5 | 2 | 10 | 5525.0 | 6.31s |
| `gemini:models/gemini-3.6-flash` | 6 | 0.0 | 0 | 0 | 0 | 5500.1 | 19.44s |
| `gemini:models/gemini-flash-lite-latest` | 8 | 31.93 | 4 | 1 | 14 | 5521.8 | 5.59s |
| `groq:allam-2-7b` | 0 | None | 0 | 0 | 0 | None | Nones |
| `groq:openai/gpt-oss-120b` | 8 | 32.5 | 3 | 2 | 6 | 5136.4 | 7.69s |
| `groq:openai/gpt-oss-20b` | 8 | 8.33 | 1 | 0 | 1 | 5136.4 | 5.42s |
| `groq:openai/gpt-oss-safeguard-20b` | 8 | 20.83 | 3 | 1 | 3 | 5136.4 | 4.94s |
| `groq:qwen/qwen3.6-27b` | 8 | 0.0 | 0 | 0 | 0 | 5414.8 | 8.54s |
| `groq:qwen/qwen3.8-27b` | 8 | 58.21 | 5 | 5 | 9 | 5416.8 | 3.71s |

## Per task

### `gemini:models/gemini-3.5-flash-lite`

| Task | Trials | Mean | Spread | pass@k | pass^k | caps seen |
|---|---|---|---|---|---|---|
| DOC-001 | 3 | 66.67 | 47.14 | yes | no | FABRICATED_ON_CLEAN_PRESENTATION, WRONG_FINAL_DETERMINATION |
| DOC-002 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE |
| DOC-003 | 3 | 66.67 | 47.14 | yes | no | CRITICAL_FALSE_CLEARANCE |
| DOC-004 | 2 | 45.0 | 45.0 | yes | no | CRITICAL_FALSE_CLEARANCE |
| DOC-005 | 3 | 90.11 | 1.76 | yes | yes | — |
| DOC-006 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE, UNPARSEABLE_OUTPUT |
| DOC-007 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE |
| DOC-008 | 3 | 82.7 | 0.9 | yes | yes | — |

### `gemini:models/gemini-3.6-flash`

| Task | Trials | Mean | Spread | pass@k | pass^k | caps seen |
|---|---|---|---|---|---|---|
| DOC-001 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |
| DOC-002 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |
| DOC-003 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |
| DOC-004 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |
| DOC-005 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |
| DOC-006 | 1 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |

### `gemini:models/gemini-flash-lite-latest`

| Task | Trials | Mean | Spread | pass@k | pass^k | caps seen |
|---|---|---|---|---|---|---|
| DOC-001 | 3 | 66.67 | 47.14 | yes | no | FABRICATED_ON_CLEAN_PRESENTATION, WRONG_FINAL_DETERMINATION |
| DOC-002 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE |
| DOC-003 | 3 | 66.67 | 47.14 | yes | no | CRITICAL_FALSE_CLEARANCE |
| DOC-004 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE |
| DOC-005 | 3 | 93.44 | 2.81 | yes | yes | — |
| DOC-006 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE, UNPARSEABLE_OUTPUT |
| DOC-007 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE |
| DOC-008 | 3 | 28.67 | 40.54 | yes | no | CRITICAL_FALSE_CLEARANCE |

### `groq:allam-2-7b`

| Task | Trials | Mean | Spread | pass@k | pass^k | caps seen |
|---|---|---|---|---|---|---|

### `groq:openai/gpt-oss-120b`

| Task | Trials | Mean | Spread | pass@k | pass^k | caps seen |
|---|---|---|---|---|---|---|
| DOC-001 | 3 | 100.0 | 0.0 | yes | yes | — |
| DOC-002 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE |
| DOC-003 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |
| DOC-004 | 3 | 60.0 | 42.43 | yes | no | CRITICAL_FALSE_CLEARANCE |
| DOC-005 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |
| DOC-006 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE, UNPARSEABLE_OUTPUT |
| DOC-007 | 3 | 100.0 | 0.0 | yes | yes | — |
| DOC-008 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |

### `groq:openai/gpt-oss-20b`

| Task | Trials | Mean | Spread | pass@k | pass^k | caps seen |
|---|---|---|---|---|---|---|
| DOC-001 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |
| DOC-002 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE, UNPARSEABLE_OUTPUT |
| DOC-003 | 3 | 66.67 | 47.14 | yes | no | UNPARSEABLE_OUTPUT |
| DOC-004 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |
| DOC-005 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |
| DOC-006 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |
| DOC-007 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |
| DOC-008 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |

### `groq:openai/gpt-oss-safeguard-20b`

| Task | Trials | Mean | Spread | pass@k | pass^k | caps seen |
|---|---|---|---|---|---|---|
| DOC-001 | 3 | 100.0 | 0.0 | yes | yes | — |
| DOC-002 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE |
| DOC-003 | 3 | 33.33 | 47.14 | yes | no | UNPARSEABLE_OUTPUT |
| DOC-004 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |
| DOC-005 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |
| DOC-006 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |
| DOC-007 | 3 | 33.33 | 47.14 | yes | no | UNPARSEABLE_OUTPUT |
| DOC-008 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |

### `groq:qwen/qwen3.6-27b`

| Task | Trials | Mean | Spread | pass@k | pass^k | caps seen |
|---|---|---|---|---|---|---|
| DOC-001 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |
| DOC-002 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |
| DOC-003 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |
| DOC-004 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |
| DOC-005 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |
| DOC-006 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |
| DOC-007 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |
| DOC-008 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |

### `groq:qwen/qwen3.8-27b`

| Task | Trials | Mean | Spread | pass@k | pass^k | caps seen |
|---|---|---|---|---|---|---|
| DOC-001 | 3 | 100.0 | 0.0 | yes | yes | — |
| DOC-002 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE |
| DOC-003 | 3 | 95.0 | 0.0 | yes | yes | — |
| DOC-004 | 3 | 81.17 | 3.42 | yes | yes | — |
| DOC-005 | 3 | 89.5 | 0.0 | yes | yes | — |
| DOC-006 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE |
| DOC-007 | 3 | 100.0 | 0.0 | yes | yes | — |
| DOC-008 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE |

## Warnings and coverage gaps

- gemini:models/gemini-3.5-flash-lite: 1 trial(s) did not score ({'ok': 23, 'provider_error': 1}) — coverage is incomplete, not zero-performance
- gemini:models/gemini-3.6-flash: 8 trial(s) did not score ({'ok': 16, 'provider_error': 8}) — coverage is incomplete, not zero-performance
- groq:allam-2-7b: 24 trial(s) did not score ({'skipped_context': 24}) — coverage is incomplete, not zero-performance
- DOC-001: lower-ranked groq:qwen/qwen3.8-27b beat higher-ranked groq:qwen/qwen3.6-27b by 100.0 points. Guide p.11 says check task ambiguity and grader behaviour before treating this as a finding.
- DOC-003: lower-ranked gemini:models/gemini-3.5-flash-lite beat higher-ranked groq:openai/gpt-oss-safeguard-20b by 33.3 points. Guide p.11 says check task ambiguity and grader behaviour before treating this as a finding.
- DOC-003: lower-ranked groq:qwen/qwen3.8-27b beat higher-ranked groq:qwen/qwen3.6-27b by 95.0 points. Guide p.11 says check task ambiguity and grader behaviour before treating this as a finding.
- DOC-004: lower-ranked gemini:models/gemini-3.5-flash-lite beat higher-ranked groq:openai/gpt-oss-safeguard-20b by 45.0 points. Guide p.11 says check task ambiguity and grader behaviour before treating this as a finding.
- DOC-004: lower-ranked groq:qwen/qwen3.8-27b beat higher-ranked groq:qwen/qwen3.6-27b by 81.2 points. Guide p.11 says check task ambiguity and grader behaviour before treating this as a finding.
- DOC-005: lower-ranked gemini:models/gemini-3.5-flash-lite beat higher-ranked groq:openai/gpt-oss-safeguard-20b by 90.1 points. Guide p.11 says check task ambiguity and grader behaviour before treating this as a finding.
- DOC-005: lower-ranked groq:qwen/qwen3.8-27b beat higher-ranked groq:qwen/qwen3.6-27b by 89.5 points. Guide p.11 says check task ambiguity and grader behaviour before treating this as a finding.
- DOC-007: lower-ranked groq:qwen/qwen3.8-27b beat higher-ranked groq:qwen/qwen3.6-27b by 100.0 points. Guide p.11 says check task ambiguity and grader behaviour before treating this as a finding.
- DOC-008: lower-ranked gemini:models/gemini-3.5-flash-lite beat higher-ranked groq:openai/gpt-oss-safeguard-20b by 82.7 points. Guide p.11 says check task ambiguity and grader behaviour before treating this as a finding.

## Excluded after probing (never silently absent)

- `gemini:models/gemini-3-flash-preview` — HTTP 200 with no usable text in content or reasoning
- `gemini:models/gemini-3.1-flash-lite` — HTTP 503 service unavailable
- `gemini:models/gemini-3.1-flash-lite-preview` — HTTP 503 service unavailable
- `gemini:models/gemini-3.1-pro-preview` — HTTP 429 quota exceeded
- `gemini:models/gemini-3.1-pro-preview-customtools` — HTTP 429 quota exceeded
- `gemini:models/gemini-3.5-flash` — HTTP 200 with no usable text in content or reasoning
- `gemini:models/gemini-3.7-flash` — HTTP 503 service unavailable
- `gemini:models/gemini-3.8-flash` — HTTP 200 with no usable text in content or reasoning
- `gemini:models/gemini-flash-latest` — HTTP 503 service unavailable
- `gemini:models/gemini-pro-latest` — HTTP 429 quota exceeded
