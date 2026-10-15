# Manual review: qwen2.5:1.5b vs qwen2.5:3b

The automatic check in `eval_answers.py` only confirms the status and that the expected
section was cited. Every answer below was also read by hand against the SOP.
Both models used the same prompt, the same retrieval and the same 10 questions
(full answers: `answer_results_qwen2.5-1.5b.md` and `answer_results_qwen2.5-3b.md`).

Hardware: GTX 1650 Max-Q (4 GB VRAM), 7.8 GB RAM. Date: 2026-10-15.

| ID | Question | qwen2.5:1.5b | qwen2.5:3b |
|---|---|---|---|
| Q01 | Documents to register | Correct, all five items | Correct, all five items |
| Q02 | Friday closing time | **Wrong**: says it "closes from 8:00 am to 12:15 pm" and calls 2:45 to 5:00 pm a lunch break | Correct: 5:00 pm |
| Q03 | Senior citizen fees | Correct | Correct fact, but adds "present any necessary documents", which the SOP does not say. Flagged UNVERIFIED by the citation check |
| Q04 | After screening | Correct | Correct |
| Q05 | Change appointment | Correct, includes the two-change limit | Correct, includes the two-change limit |
| Q06 | Compulsory papers (paraphrase) | Correct, all five items | Leaves out the medication record book |
| Q07 | 20 minutes late | **Wrong**: says the patient becomes a walk-in (that rule is for more than 30 minutes) | Correct |
| Q08 | Paid parking (not in SOP) | Correct: says the SOP does not cover it | Correct |
| Q09 | Fever medicine | Refused by scope guard | Refused by scope guard |
| Q10 | Forgot MyKad (follow-up) | **Incomplete**: skips the name and date-of-birth lookup | Correct, includes the lookup and the new-patient fallback |
| | **Fully correct** | **7 / 10** (2 wrong, 1 incomplete) | **8 / 10** (0 wrong, 2 minor issues, 1 of them flagged) |
| | Average time per answer | 5.9 s | 7.3 s |

## Decision
`qwen2.5:3b` is the default model. It made no factual errors on the test set, while
1.5b gave two wrong answers that a patient could act on. The cost is about 1.4 s more
per answer, which is acceptable for a counter-side assistant.

## Lessons
- A cited answer is not automatically a correct answer. Retrieval found the right
  evidence for every question; all errors happened when the model rewrote that evidence.
- Small models trade completeness for brevity differently: 1.5b listed every document
  but misread rules, 3b read rules correctly but sometimes shortened lists.
- The citation check caught one answer (3b, Q03) that added advice not in the SOP.
