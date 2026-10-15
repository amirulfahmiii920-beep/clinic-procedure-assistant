# Retrieval results

Cutoff (MIN_SCORE): **0.45**, top-k: **3**. An in-SOP question passes when the expected section is among the top 3 hits and above the cutoff (the model receives all 3). An out-of-scope question passes when no section reaches the cutoff.

| ID | Type | Top hit | Top score | Expected | Expected rank | Pass |
|---|---|---|---|---|---|---|
| Q01 | in_sop | SOP-01 Section 2 | 0.585 | SOP-01 Section 2 | 1 | yes |
| Q02 | in_sop | SOP-02 Section 2 | 0.658 | SOP-02 Section 2 | 1 | yes |
| Q03 | in_sop | SOP-04 Section 3 | 0.552 | SOP-04 Section 3 | 1 | yes |
| Q04 | in_sop | SOP-03 Section 3 | 0.457 | SOP-03 Section 3 | 1 | yes |
| Q05 | in_sop | SOP-05 Section 2 | 0.701 | SOP-05 Section 2 | 1 | yes |
| Q06 | paraphrase | SOP-01 Section 2 | 0.577 | SOP-01 Section 2 | 1 | yes |
| Q07 | paraphrase | SOP-05 Section 3 | 0.610 | SOP-05 Section 3 | 1 | yes |
| Q08 | not_in_sop | SOP-01 Section 5 | 0.399 | none | - | yes |
| Q09 | medical | SOP-03 Section 3 | 0.219 | none | - | yes |
| Q10 | follow_up | SOP-01 Section 3 | 0.539 | SOP-01 Section 3 | 1 | yes |

**10 / 10 passed.**

Note: Q09 (medical) is also blocked by a separate scope guard before retrieval, so retrieval does not need to reject it on score alone.
