# Results

Panel `panel-02-probe-derived` · 3 trials per task · temperature 0.0

| Model | Scored trials | Tasks covered | Mean score | pass@k tasks | pass^k tasks | Critical false clearances | Mean prompt tok | Mean latency |
|---|---|---|---|---|---|---|---|---|
| `gemini:models/gemini-3.5-flash-lite` | 24 | 8 | 43.27 | 4 | 3 | 12 | 5521.8 | 5.12s |
| `gemini:models/gemini-3.6-flash` | 0 | 0 (no scored trials) | — | 0 | 0 | 0 | — | — |
| `gemini:models/gemini-flash-lite-latest` | 24 | 8 | 35.74 | 4 | 2 | 14 | 5521.8 | 5.0s |
| `groq:allam-2-7b` | 0 | 0 (no scored trials) | — | 0 | 0 | 0 | — | — |
| `groq:openai/gpt-oss-120b` | 24 | 8 | 64.68 | 6 | 4 | 6 | 5136.4 | 4.48s |
| `groq:openai/gpt-oss-20b` | 24 | 8 | 72.43 | 7 | 5 | 5 | 5136.4 | 3.61s |
| `groq:openai/gpt-oss-safeguard-20b` | 24 | 8 | 67.1 | 7 | 4 | 7 | 5136.4 | 5.66s |
| `groq:qwen/qwen3.6-27b` | 24 | 8 | 70.52 | 6 | 6 | 3 | 5414.8 | 15.62s |
| `groq:qwen/qwen3.8-27b` | 24 | 8 | 58.16 | 5 | 5 | 9 | 5416.8 | 3.95s |

## Panel-wide: 168 scored trials, 104 passed (61.9%), mean 58.84/100

| Dimension | Mean credit |
|---|---|
| uncertainty | 60.7% |
| recall | 79.4% |
| precision | 90.5% |
| format | 92.3% |
| evidence | 94.5% |
| rule_mapping | 97.6% |
| severity | 97.6% |

| Most-missed code | Trials |
|---|---|
| `CURRENCY_MISMATCH` | 21 |
| `BENEFICIARY_ADDRESS_VARIANT` | 20 |
| `SHIPPING_MARKS_MISMATCH` | 19 |
| `INSURANCE_DATED_AFTER_SHIPMENT` | 12 |
| `AMOUNT_PRESENTATION_DEFECT` | 11 |
| `PRESENTATION_AFTER_EXPIRY` | 6 |
| `AMOUNT_EXCEEDS_CREDIT` | 6 |
| `DOCUMENT_MISSING` | 6 |

| Cap fired | Trials |
|---|---|
| `CRITICAL_FALSE_CLEARANCE` | 56 |
| `UNPARSEABLE_OUTPUT` | 4 |
| `FABRICATED_ON_CLEAN_PRESENTATION` | 2 |
| `WRONG_FINAL_DETERMINATION` | 2 |
| `HALLUCINATED_EVIDENCE` | 2 |

## Per task

### `gemini:models/gemini-3.5-flash-lite`

| Task | Trials | Mean | Spread | pass@k | pass^k | caps seen |
|---|---|---|---|---|---|---|
| DOC-001 | 3 | 100.0 | 0.0 | yes | yes | — |
| DOC-002 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE |
| DOC-003 | 3 | 100.0 | 0.0 | yes | yes | — |
| DOC-004 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE |
| DOC-005 | 3 | 89.71 | 0.29 | yes | yes | — |
| DOC-006 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE, UNPARSEABLE_OUTPUT |
| DOC-007 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE |
| DOC-008 | 3 | 56.44 | 39.93 | yes | no | CRITICAL_FALSE_CLEARANCE |

### `gemini:models/gemini-3.6-flash`

| Task | Trials | Mean | Spread | pass@k | pass^k | caps seen |
|---|---|---|---|---|---|---|

### `gemini:models/gemini-flash-lite-latest`

| Task | Trials | Mean | Spread | pass@k | pass^k | caps seen |
|---|---|---|---|---|---|---|
| DOC-001 | 3 | 66.67 | 47.14 | yes | no | FABRICATED_ON_CLEAN_PRESENTATION, WRONG_FINAL_DETERMINATION |
| DOC-002 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE |
| DOC-003 | 3 | 100.0 | 0.0 | yes | yes | — |
| DOC-004 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE |
| DOC-005 | 3 | 90.61 | 1.57 | yes | yes | — |
| DOC-006 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE |
| DOC-007 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE |
| DOC-008 | 3 | 28.67 | 40.54 | yes | no | CRITICAL_FALSE_CLEARANCE |

### `groq:allam-2-7b`

| Task | Trials | Mean | Spread | pass@k | pass^k | caps seen |
|---|---|---|---|---|---|---|

### `groq:openai/gpt-oss-120b`

| Task | Trials | Mean | Spread | pass@k | pass^k | caps seen |
|---|---|---|---|---|---|---|
| DOC-001 | 3 | 66.67 | 47.14 | yes | no | FABRICATED_ON_CLEAN_PRESENTATION, WRONG_FINAL_DETERMINATION |
| DOC-002 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE |
| DOC-003 | 3 | 97.5 | 3.54 | yes | no | HALLUCINATED_EVIDENCE |
| DOC-004 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE |
| DOC-005 | 3 | 88.71 | 1.12 | yes | yes | — |
| DOC-006 | 3 | 85.83 | 0.0 | yes | yes | — |
| DOC-007 | 3 | 100.0 | 0.0 | yes | yes | — |
| DOC-008 | 3 | 78.75 | 0.0 | yes | yes | — |

### `groq:openai/gpt-oss-20b`

| Task | Trials | Mean | Spread | pass@k | pass^k | caps seen |
|---|---|---|---|---|---|---|
| DOC-001 | 3 | 100.0 | 0.0 | yes | yes | — |
| DOC-002 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE |
| DOC-003 | 3 | 94.17 | 8.25 | yes | yes | — |
| DOC-004 | 3 | 55.83 | 39.48 | yes | no | CRITICAL_FALSE_CLEARANCE |
| DOC-005 | 3 | 91.54 | 4.39 | yes | yes | — |
| DOC-006 | 3 | 51.89 | 36.69 | yes | no | CRITICAL_FALSE_CLEARANCE |
| DOC-007 | 3 | 100.0 | 0.0 | yes | yes | — |
| DOC-008 | 3 | 86.0 | 0.0 | yes | yes | — |

### `groq:openai/gpt-oss-safeguard-20b`

| Task | Trials | Mean | Spread | pass@k | pass^k | caps seen |
|---|---|---|---|---|---|---|
| DOC-001 | 3 | 100.0 | 0.0 | yes | yes | — |
| DOC-002 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE |
| DOC-003 | 3 | 100.0 | 0.0 | yes | yes | — |
| DOC-004 | 3 | 30.0 | 42.43 | yes | no | CRITICAL_FALSE_CLEARANCE |
| DOC-005 | 3 | 91.21 | 2.42 | yes | yes | — |
| DOC-006 | 3 | 28.61 | 40.46 | yes | no | CRITICAL_FALSE_CLEARANCE |
| DOC-007 | 3 | 100.0 | 0.0 | yes | no | HALLUCINATED_EVIDENCE |
| DOC-008 | 3 | 87.0 | 2.16 | yes | yes | — |

### `groq:qwen/qwen3.6-27b`

| Task | Trials | Mean | Spread | pass@k | pass^k | caps seen |
|---|---|---|---|---|---|---|
| DOC-001 | 3 | 100.0 | 0.0 | yes | yes | — |
| DOC-002 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE |
| DOC-003 | 3 | 98.33 | 2.36 | yes | yes | — |
| DOC-004 | 3 | 90.0 | 0.0 | yes | yes | — |
| DOC-005 | 3 | 0.0 | 0.0 | no | no | UNPARSEABLE_OUTPUT |
| DOC-006 | 3 | 85.83 | 0.0 | yes | yes | — |
| DOC-007 | 3 | 100.0 | 0.0 | yes | yes | — |
| DOC-008 | 3 | 90.0 | 0.0 | yes | yes | — |

### `groq:qwen/qwen3.8-27b`

| Task | Trials | Mean | Spread | pass@k | pass^k | caps seen |
|---|---|---|---|---|---|---|
| DOC-001 | 3 | 100.0 | 0.0 | yes | yes | — |
| DOC-002 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE |
| DOC-003 | 3 | 95.0 | 0.0 | yes | yes | — |
| DOC-004 | 3 | 78.75 | 0.0 | yes | yes | — |
| DOC-005 | 3 | 91.5 | 1.41 | yes | yes | — |
| DOC-006 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE |
| DOC-007 | 3 | 100.0 | 0.0 | yes | yes | — |
| DOC-008 | 3 | 0.0 | 0.0 | no | no | CRITICAL_FALSE_CLEARANCE |

## Warnings and coverage gaps

- gemini:models/gemini-3.6-flash: 10 trial(s) did not score ({'provider_error': 10}) — coverage is incomplete, not zero-performance
- groq:allam-2-7b: 24 trial(s) did not score ({'skipped_context': 24}) — coverage is incomplete, not zero-performance
- DOC-001: weaker-ranked groq:qwen/qwen3.8-27b outscored stronger-ranked groq:openai/gpt-oss-120b by 33.3 points. Guide p.11 says check task ambiguity and grader behaviour before treating this as a finding.
- DOC-004: weaker-ranked groq:openai/gpt-oss-safeguard-20b outscored stronger-ranked gemini:models/gemini-3.5-flash-lite by 30.0 points. Guide p.11 says check task ambiguity and grader behaviour before treating this as a finding.
- DOC-004: weaker-ranked groq:qwen/qwen3.6-27b outscored stronger-ranked groq:qwen/qwen3.8-27b by 11.2 points. Guide p.11 says check task ambiguity and grader behaviour before treating this as a finding.
- DOC-004: weaker-ranked groq:qwen/qwen3.8-27b outscored stronger-ranked groq:openai/gpt-oss-120b by 78.8 points. Guide p.11 says check task ambiguity and grader behaviour before treating this as a finding.
- DOC-006: weaker-ranked groq:openai/gpt-oss-safeguard-20b outscored stronger-ranked gemini:models/gemini-3.5-flash-lite by 28.6 points. Guide p.11 says check task ambiguity and grader behaviour before treating this as a finding.
- DOC-006: weaker-ranked groq:qwen/qwen3.6-27b outscored stronger-ranked groq:qwen/qwen3.8-27b by 85.8 points. Guide p.11 says check task ambiguity and grader behaviour before treating this as a finding.
- DOC-007: weaker-ranked groq:openai/gpt-oss-safeguard-20b outscored stronger-ranked gemini:models/gemini-3.5-flash-lite by 100.0 points. Guide p.11 says check task ambiguity and grader behaviour before treating this as a finding.
- DOC-008: weaker-ranked groq:openai/gpt-oss-safeguard-20b outscored stronger-ranked gemini:models/gemini-3.5-flash-lite by 30.6 points. Guide p.11 says check task ambiguity and grader behaviour before treating this as a finding.
- DOC-008: weaker-ranked groq:qwen/qwen3.6-27b outscored stronger-ranked groq:qwen/qwen3.8-27b by 90.0 points. Guide p.11 says check task ambiguity and grader behaviour before treating this as a finding.

## Excluded after probing (never silently absent)

- none
