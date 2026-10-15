# Clinic Procedure Assistant

**It answers from the clinic's own rules, and says so when it can't.**

A local retrieval-augmented (RAG) assistant that answers patient questions about clinic
procedures (registration, opening hours, fees, appointments) using only the clinic's SOP
documents. Every answer cites the SOP section it came from. Questions the SOPs do not cover
get an honest "not covered", and medical questions are refused. Everything runs on a laptop
through Ollama, so no question leaves the machine.

![Answer with cited SOP sections](docs/screenshots/ui_answer.png)

> The clinic (Klinik Kesihatan Taman Mawar) and its SOPs are fictional and were written for
> this project. This is a portfolio project, not a medical or official information service.

## Why

Patients ask the registration counter the same questions every day, and the answers already
sit in the clinic's standard operating procedures. Nobody reads a 5-page SOP in a waiting
room, and a general chatbot will happily invent a plausible answer, even though every clinic
runs on its own rules. This assistant is built to do the opposite: answer only from the
clinic's documents, show the evidence, and admit when the documents are silent.

It is a companion to my AI-powered Hospital Queue project ([other projects](https://github.com/amirulfahmiii920-beep)): that one tells
patients how long they will wait, this one tells them what to do.

## What it does

| Feature | How |
|---|---|
| Answers with citations | Retrieves the most relevant SOP sections and the model must cite them, e.g. *SOP-01 §2* |
| Says "not covered" | If no section scores above a relevance cutoff, or the model reports the evidence does not answer, it says so instead of guessing |
| Understands follow-ups | "What if I forgot it?" is searched together with the previous question |
| Checks opening hours in code | "Is the clinic open now?" is answered by a Python function from the SOP-02 timetable, not by the model |
| Understands Malay questions | Malay is detected, translated to English for search, and fixed replies are in Malay (see [Limitations](#limitations)) |
| Runs locally | Ollama with `qwen2.5:3b` for answers and `embeddinggemma` for search |

### Safety layers

| Layer | What it stops | Where |
|---|---|---|
| Input check | Empty or over-long messages, prompt-injection attempts such as "ignore your instructions", and abusive language (English and Malay) | `guards.py` |
| PII masking | MyKad, phone, e-mail and passport numbers are replaced with `[IC]`, `[PHONE]`... before search, the model or the log see them | `privacy.py` |
| Keyword scope guard | Obvious medical-advice questions (medicines, doses, diagnosis), refused with no model call | `guards.py` |
| Model scope guard | Medical questions with no keyword ("What can I take for my headache?"), caught by a small few-shot classification call | `guards.py` |
| Grounding | The model may only use the supplied SOP evidence; instructions inside documents are treated as data | `answer.py` |
| Structured output + evidence check | The reply must be JSON matching a Pydantic schema and may only cite evidence it was given; otherwise *Needs review* | `answer.py` |
| Output guard | An answer that drifts into dosing or diagnosis ("take 500 mg", "it sounds like you have") is withheld | `guards.py` |
| Grounding check | Every time, RM amount and number in the answer must appear in the cited SOP section. If it is in another retrieved section, the citation is repaired; if it is nowhere, the answer is flagged | `grounding.py` |
| Staff review queue | Flagged or withheld answers are queued with the masked question for a person to check (human in the loop) | `review_queue.py` |
| Audit log | One JSON line per request: status, guard that fired, sources, latency, model calls and tokens. No question or answer text, no identifiers; only a short hash of the masked question | `audit.py` |

See also the [model card](MODEL_CARD.md) for intended use, evaluation and risks.

| | |
|---|---|
| ![IC number masked](docs/screenshots/ui_pii_masked.png) | ![Prompt injection blocked](docs/screenshots/ui_injection_blocked.png) |
| The IC number is masked before search; the search text has no identifier | A prompt-injection attempt is blocked before any model call |
| ![Model-based medical check](docs/screenshots/ui_model_guard.png) | ![Malay question](docs/screenshots/ui_malay.png) |
| "What can I take for my headache?" has no medical keyword; the model check refuses it | A Malay question is detected, searched in English and answered with a Malay note |
| ![Safety unit tests](docs/screenshots/safety_tests.png) | ![Audit log](docs/screenshots/audit_log.png) |
| Safety unit tests | Audit log: decisions and sources, no question text or IC numbers |

## How it works

```mermaid
flowchart LR
    subgraph Indexing["Indexing (once)"]
        A[5 SOP files] --> B[Split by section] --> C[embeddinggemma] --> D[(SQLite<br/>vectors + metadata)]
    end
    Q[Patient question] --> I{Input check<br/>length, injection}
    I -- blocked --> X[Blocked]
    I -- ok --> P[Mask IC, phone,<br/>e-mail, passport]
    P --> G{Medical?<br/>keywords, then model}
    G -- yes --> R1[Refuse, point to doctor]
    G -- no --> H{"Open now?"}
    H -- yes --> T[Python clock tool]
    H -- no --> M[Malay? translate<br/>to English] --> S[Embed, cosine<br/>search top 3] --> K{Score above<br/>cutoff?}
    D -.-> S
    K -- no --> N[Not covered]
    K -- yes --> L[qwen2.5:3b<br/>JSON answer + cited] --> V{Valid citations?}
    V -- no --> U[Needs review]
    V -- yes --> O{Medical advice<br/>in the answer?}
    O -- yes --> W[Withheld]
    O -- no --> GR{Times, fees, numbers<br/>in cited section?}
    GR -- "in another retrieved section" --> RP[Repair citation] --> OK[Answer + sources]
    GR -- yes --> OK
    GR -- nowhere --> U
    U --> RQ[(Staff review queue)]
    W --> RQ
```

Every path ends with one audit-log event.

![Architecture diagram](docs/screenshots/arch_diagram.png)

![Citation repaired by the grounding check](docs/screenshots/ui_citation_repaired.png)
*The model cited SOP-02 §5 for times that only appear in §2. The grounding check noticed and
corrected the citation to the section that contains them.*

1. **Indexing.** Each SOP section (`## 2. Documents to bring`) becomes one chunk. Sections are
   short and self-contained, so every rule stays whole and every answer can cite an exact
   section. Chunks are embedded with `embeddinggemma` (using its query/document task prefixes)
   and stored in SQLite with the document name, section, title and version.
2. **Retrieval.** The question is embedded with the same model and compared by cosine
   similarity against every section. The top 3 above `MIN_SCORE = 0.45` become evidence,
   labelled [A], [B], [C]. (Numbered labels made the model confuse evidence numbers with
   section numbers.)
3. **Generation.** `qwen2.5:3b` (temperature 0) must reply as JSON matching a Pydantic schema:
   `{"answer": str, "cited": [str]}`, or the sentinel `NOT_IN_SOP`.
4. **Validation.** Three layers: the reply must parse, match the schema, and every cited
   label must refer to evidence that was actually supplied. Otherwise the answer is shown as
   *Needs review*, not as a verified answer. Then the output guard checks for medical advice.

## Results

Twenty test questions in [`tests/questions.csv`](tests/questions.csv): procedure questions,
paraphrases, a follow-up, out-of-scope and medical questions, an IC number in the question, a
prompt-injection attempt, medical questions without keywords, an emergency procedure, and four
Malay questions.

| Check | Result |
|---|---|
| Safety unit tests: masking, input check, word filter, guards, grounding, language detection (no model) | **10 / 10** ([tests](tests/test_safety.py)) |
| Retrieval on the original 10 questions | **10 / 10**; Recall@1 1.00, Recall@3 1.00, MRR 1.00 ([details](tests/retrieval_results.md)) |
| Full assistant, automatic check (status, language, masking, expected section cited) | **19 / 20** ([details](tests/answer_results_qwen2.5-3b.md)) |
| Full assistant, read by hand against the SOPs | **15 correct, 2 correct after citation repair, 3 incomplete, 0 wrong** ([review](tests/manual_review.md)) |
| Semantic robustness: 3 topics, each asked 5 ways | **14 / 15** consistent ([details](tests/robustness_results.md)) |
| Temperature 0.0 / 0.7 / 1.2 (3 questions x 3 runs) | identical runs **3/3**, 0/3, 0/3; correct 9/9 at each ([details](tests/temperature_results.md)) |

All six safety cases behaved as intended: the IC number never reached search, the model or the
log; the injection attempt was blocked before any model call; two medical questions with no
medical keyword were caught by the model guard; and Malay medical and out-of-scope questions got
Malay replies. Two answers cited the wrong section; the grounding check caught both and the
citation was repaired from the retrieved section that contains the times. The remaining
automatic failure (Q04) is an incomplete answer.

Temperature 0 is the default: higher settings kept the facts on these questions but changed the
wording on every run, and a clinic assistant should give the same answer to the same question.

## AWS equivalents

The project runs locally and free, but each part maps to a managed AWS service covered in the
AWS Academy Generative AI Foundations course:

| This project | AWS equivalent |
|---|---|
| Ollama running `qwen2.5:3b` | Amazon Bedrock (foundation models through one API) |
| `ingest.py` + `retrieve.py` + SQLite vectors | Amazon Bedrock Knowledge Bases (managed RAG, chunking, embeddings, vector store) |
| `guards.py`: keyword topics, injection and word filters, PII masking | Amazon Bedrock Guardrails (denied topics, prompt-attack filter, word filters, sensitive-information filters) |
| `grounding.py` | Bedrock Guardrails contextual grounding check |
| `review_queue.py` | Amazon Augmented AI (A2I) human review workflows |
| `audit.py` with token counts | Amazon CloudWatch logs and metrics, AWS CloudTrail for API activity |
| `MODEL_CARD.md` | Amazon SageMaker Model Cards |
| `tests/eval_*.py` and the manual review | Amazon Bedrock model evaluation (automatic and human) |
| `clinic_hours.py` tool | A tool / action group called by Amazon Bedrock Agents |
| Running locally so data stays on the machine | Bedrock does not use prompts to train models; data encrypted with AWS KMS; access controlled with IAM |

### Choosing the model

I compared two local models with the same prompt, retrieval and questions on a
GTX 1650 (4 GB VRAM):

| | qwen2.5:1.5b | qwen2.5:3b |
|---|---|---|
| Fully correct (by hand) | 7 / 10 | **8 / 10** |
| Wrong answers a patient could act on | 2 | **0** |
| Average time per answer | 5.9 s | 7.3 s |

`qwen2.5:3b` is the default. The smaller model misread the Friday timetable and told a
patient who was 20 minutes late that they would become a walk-in (that rule applies after 30
minutes). Retrieval found the right section in both cases; the errors came from the model
rewriting correct evidence. **A cited answer is not automatically a correct answer**, which
is why the project keeps a hand-checked review alongside the automatic tests.

## Screenshots

| | |
|---|---|
| ![Follow-up question](docs/screenshots/ui_followup.png) | ![Not covered by the SOPs](docs/screenshots/ui_not_found.png) |
| Follow-up: "it" is resolved to the MyKad from the previous question | A question the SOPs do not cover gets an honest answer |
| ![Medical question refused](docs/screenshots/ui_medical.png) | ![Retrieval test run](docs/screenshots/day2_retrieval.png) |
| Medical advice is refused before any model call | Retrieval test: 10 / 10 |

## Run it

Requirements: Python 3.11 and [Ollama](https://ollama.com/download).

```bash
ollama pull qwen2.5:3b
ollama pull embeddinggemma

python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

python src/ingest.py              # build the SOP index
python app.py                     # open http://127.0.0.1:7860
```

Run the tests:

```bash
python tests/test_safety.py                        # deterministic safety checks, no model needed
python tests/eval_retrieval.py
python tests/eval_answers.py                       # uses qwen2.5:3b
python tests/eval_robustness.py                    # same question asked five ways
python tests/eval_temperature.py                   # temperature 0.0 / 0.7 / 1.2
CHAT_MODEL=qwen2.5:1.5b python tests/eval_answers.py   # compare another model (bash syntax)
```

## Project structure

```
data/sop/              5 fictional SOP documents (the knowledge base)
src/config.py          models, top-k, relevance cutoff
src/ollama_client.py   minimal Ollama HTTP client (standard library only)
src/ingest.py          split SOPs by section, embed, store in SQLite
src/retrieve.py        cosine search with cutoff; refuses an index built with another model
src/privacy.py         masks MyKad, phone, e-mail and passport numbers
src/guards.py          input check, keyword and model scope guards, output guard
src/language.py        Malay/English detection and fixed replies in both languages
src/clinic_hours.py    deterministic "open now?" tool (Malaysia time, UTC+8)
src/grounding.py       times, fees and numbers must appear in the cited evidence
src/review_queue.py    staff review queue for flagged or withheld answers
src/audit.py           audit log with token counts, without question or answer text
src/answer.py          the pipeline from input check to audit log
MODEL_CARD.md          intended use, evaluation, limitations and risks
app.py                 Gradio interface
tests/                 questions, safety unit tests, evaluation scripts, results, manual review
logs/                  audit.jsonl (created at run time, not committed)
```

## Limitations

- The SOPs are fictional and short (5 documents, 25 sections). Retrieval was tuned on 10
  questions; the relevance cutoff sits close to some scores (a supported question scored
  0.457 and an unsupported one 0.399 against a 0.45 cutoff), so more test questions are
  needed before trusting it on a larger corpus.
- **Citations are the weakest part.** The model sometimes cites a neighbouring section. The
  grounding check repairs this only when the answer contains a time, fee or number to match;
  a wrong citation for a sentence without numbers is not detected. One answer still mentions a
  rule number.
- **The grounding check is narrow.** It checks times, RM amounts and whole numbers only. It
  skips decimals (they look like section numbers), so a calculated figure such as "a 2.5-hour
  break" is not checked, and it cannot tell whether a sentence without numbers is supported.
- **Malay answers are in English.** Asked to write Malay, `qwen2.5:3b` used wrong terms and a
  wrong time, so generated answers stay in English with a Malay note. A larger model or a
  Malay version of the SOPs would be needed for full Malay answers.
- PII masking covers MyKad, phone, e-mail and passport numbers only. **Names and addresses are
  not detected**; pattern masking alone does not make text anonymous.
- The keyword guards, the word filter and the injection check catch common phrasings, not every
  phrasing. The model-based scope check fails open (treated as a procedure question) if Ollama is
  down, so the other layers still apply.
- Each answered question costs 3 to 4 model calls (scope check, embedding, answer, plus
  translation for Malay) and 570 to 790 input tokens in the test runs, logged per request.
- The opening-hours tool does not know about public holidays and says so in its answer.
- Answers can be incomplete (3 of 20 test answers left out a step or item). Patients should
  confirm important details at the counter.
- The review queue is a file, not a review screen; a real deployment would need a staff UI.

## Built with

Python, Ollama (`qwen2.5:3b`, `embeddinggemma`), SQLite, Pydantic, Gradio.
Built after the GenAI Associate course (OpenAI API, Gradio, RAG and agent modules), extending
the course's RAG lab into a complete, tested application.
