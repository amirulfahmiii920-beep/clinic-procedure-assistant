# Model card: Clinic Procedure Assistant

A short, standard description of what this system is for, how it was evaluated and where it
fails, in the spirit of model cards (Mitchell et al., 2019; Amazon SageMaker Model Cards).

## Overview

| | |
|---|---|
| System | Retrieval-augmented assistant that answers clinic procedure questions from SOP documents |
| Version | 2026-10-15 |
| Owner | Muhammad Amirul Fahmi (portfolio project) |
| Models | `qwen2.5:3b` (answers, scope check, Malay-to-English query translation), `embeddinggemma` (search), both through Ollama on a laptop |
| Knowledge | 5 fictional SOPs for a fictional clinic (Klinik Kesihatan Taman Mawar), 25 sections |
| Settings | temperature 0.0, top-k 3, relevance cutoff 0.45 |

## Intended use

- **Users:** patients and visitors of a government outpatient clinic, at a kiosk or on a phone.
- **Use:** answer questions about registration, documents, opening hours, fees, appointments and
  where to go, with the SOP section shown for every answer.
- **Not for:** medical advice, diagnosis, medicine or dosing questions, emergencies (it points
  to the treatment room or 999), or any decision about a specific patient's care.

## How it decides

1. Input check (length, prompt injection, abusive language) → PII masking → keyword and
   model-based medical scope checks → opening-hours tool → retrieval with a relevance cutoff.
2. The model answers only from the retrieved sections, as JSON validated by a schema.
3. Citation check, grounding check (times, fees and numbers must appear in the cited
   section, with automatic citation repair), and an output guard for medical advice.
4. Uncertain answers go to a staff review queue. Every request writes an audit event without
   the question text.

## Evaluation (2026-10-15, GTX 1650 4 GB)

| Test | Result |
|---|---|
| Safety unit tests (masking, input check, guards, grounding, language) | 10 / 10 |
| Retrieval, 10 questions | 10 / 10 passed; Recall@1 1.00, Recall@3 1.00, MRR 1.00 |
| Full assistant, 20 questions incl. safety and Malay cases | 19 / 20 automatic |
| Semantic robustness, 3 topics x 5 phrasings | 14 / 15 consistent |
| Temperature 0.0 / 0.7 / 1.2, 3 questions x 3 runs | identical runs 3/3, 0/3, 0/3; correct 9/9 at each |
| Model comparison, 10 questions read by hand | qwen2.5:3b 8/10 correct and 0 wrong; qwen2.5:1.5b 7/10 and 2 wrong |

Details: [`tests/manual_review.md`](tests/manual_review.md) and the result files in `tests/`.

## Known limitations and risks

| Risk | Status |
|---|---|
| Incomplete answers (a step or item left out) | Seen in 3 of 20 test answers (Q04, Q05, Q11); patients are told to confirm at the counter |
| Wrong section cited | Seen in 2 of 20 (Q02, Q17); repaired automatically because the facts were in another retrieved section, otherwise flagged |
| Rule numbers in the answer text | One answer (Q11) still says "rule 2.1" despite the instruction not to |
| Facts the model calculates itself ("a 2.5-hour break") | Not caught: the grounding check ignores decimal numbers because they look like section numbers |
| Malay answers | Generated answers are in English; the 3B model wrote wrong Malay terms and times |
| PII masking | MyKad, phone, e-mail and passport numbers only; names and addresses are not detected |
| Guards | Keyword lists and a small classifier; they catch common phrasings, not all |
| Relevance cutoff | Tuned on 10 questions; scores near the cutoff (0.399 vs 0.457) leave little margin |
| Public holidays | Not known to the opening-hours tool; its answer says so |

## Ethical considerations

- **Privacy:** runs locally; identifiers are masked before the model, the log and the review
  queue; the audit log stores a hash of the masked question, not the text.
- **Safety:** medical questions are refused twice (keywords, then a classifier) and answers are
  checked once more for medical advice before they are shown.
- **Fairness:** answer quality is lower for Malay speakers (English answers to Malay
  questions). This unequal performance is stated openly rather than hidden.
- **Accountability:** every request is logged with the check that decided the outcome, and
  uncertain answers wait for a person in the review queue.
