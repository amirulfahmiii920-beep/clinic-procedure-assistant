"""Answer a patient question from the SOPs only, with citations.

Pipeline:
  1. Scope guard     -> medical-advice questions are refused (no model call).
  2. Opening-hours   -> "is it open now?" goes to a Python tool, not the model.
  3. Retrieval       -> top-k SOP sections above the score cutoff. None -> NOT_FOUND.
  4. Generation      -> the model answers only from numbered evidence and cites [n].
  5. Evidence check  -> citations must point to evidence that was actually supplied.

Run:  python src/answer.py "What documents do I need to register?"
"""
import re
import sys
from typing import Literal

from pydantic import BaseModel, ValidationError

from clinic_hours import asks_if_open_now, check_clinic_open, describe
from config import CHAT_MODEL
from guards import REFUSAL, is_medical_advice
from ollama_client import OllamaUnavailable, chat
from retrieve import retrieve

NOT_FOUND_TEXT = ("The clinic's SOPs don't cover this question, so I can't answer it. "
                  "Please ask at the registration counter.")
SENTINEL = "NOT_IN_SOP"

SYSTEM = f"""You answer patient questions for a clinic using ONLY the numbered SOP evidence provided.
Reply as JSON with two fields:
- "answer": short, plain English (up to 5 sentences), written to the patient, using only facts
  stated in the evidence. No outside knowledge, no guesses, no medical advice.
  Copy times, amounts and conditions exactly as written. Keep each rule with the day or group it
  belongs to; do not mix rules from different days. If a rule has steps or conditions ("if ... then"),
  include every step in order. If the evidence lists several items (documents, groups, steps),
  list all of them, not only the first ones.
  If the evidence does not answer the question, the answer must be exactly: {SENTINEL}
- "cited": the list of evidence numbers you used, e.g. [1] or [1, 2]. Use [] only for {SENTINEL}."""


class ModelReply(BaseModel):
    """Schema the model must follow (sent to Ollama as a JSON Schema)."""
    answer: str
    cited: list[int]


class Source(BaseModel):
    n: int
    doc_id: str
    doc_title: str
    section: str
    section_title: str
    version: str
    score: float
    text: str


class Answer(BaseModel):
    status: Literal["ANSWERED", "NOT_FOUND", "REFUSED_MEDICAL", "TOOL", "UNVERIFIED", "MODEL_UNAVAILABLE"]
    text: str
    query: str                      # the text actually used for retrieval (shows follow-up resolution)
    sources: list[Source] = []      # evidence supplied to the model
    cited: list[int] = []           # evidence numbers the answer actually cites


# Pronouns that point back to the previous question. "there" and "this" are left out on
# purpose: "Is there paid parking?" and "Is this clinic open?" are new questions.
FOLLOW_UP = re.compile(r"\b(it|that|they|them|those)\b", re.I)
LEADS_ON = re.compile(r"^\s*(and|also|what about|how about|what if)\b", re.I)


def resolve_query(question: str, history: list[dict]) -> str:
    """Short or pronoun-led follow-ups are searched together with the previous user question."""
    prev = next((m["content"] for m in reversed(history) if m["role"] == "user"), None)
    if prev and (len(question.split()) <= 4 or FOLLOW_UP.search(question) or LEADS_ON.match(question)):
        return f"{prev} {question}"
    return question


def build_prompt(question: str, sources: list[Source]) -> str:
    evidence = "\n\n".join(
        f"[{s.n}] {s.doc_id} Section {s.section} ({s.section_title}):\n{s.text}" for s in sources)
    return f"Evidence:\n{evidence}\n\nPatient question: {question}"


def answer(question: str, history: list[dict] | None = None) -> Answer:
    history = history or []
    question = question.strip()

    if is_medical_advice(question):
        return Answer(status="REFUSED_MEDICAL", text=REFUSAL, query=question)

    if asks_if_open_now(question):
        return Answer(status="TOOL", text=describe(check_clinic_open()), query=question)

    query = resolve_query(question, history)
    try:
        hits = retrieve(query)
    except OllamaUnavailable as e:
        return Answer(status="MODEL_UNAVAILABLE", text=str(e), query=query)
    if not hits:
        return Answer(status="NOT_FOUND", text=NOT_FOUND_TEXT, query=query)

    sources = [Source(n=i + 1, score=round(h["score"], 3),
                      **{k: h[k] for k in ("doc_id", "doc_title", "section", "section_title", "version", "text")})
               for i, h in enumerate(hits)]
    messages = [{"role": "system", "content": SYSTEM}]
    messages += [m for m in history[-4:] if m["role"] in ("user", "assistant")]
    messages.append({"role": "user", "content": build_prompt(question, sources)})
    try:
        raw = chat(messages, CHAT_MODEL, temperature=0.0, schema=ModelReply.model_json_schema())
    except OllamaUnavailable as e:
        # Keep the retrieved evidence visible even though no answer could be written.
        return Answer(status="MODEL_UNAVAILABLE", text=str(e), query=query, sources=sources)

    # Layers 1 and 2: the reply must parse as JSON and match the schema.
    try:
        reply = ModelReply.model_validate_json(raw)
    except ValidationError:
        return Answer(status="UNVERIFIED", text=raw.strip(), query=query, sources=sources)

    if SENTINEL in reply.answer:
        return Answer(status="NOT_FOUND", text=NOT_FOUND_TEXT, query=query, sources=sources)

    # Layer 3, evidence check: every cited number must be evidence that was actually supplied.
    cited = sorted(set(reply.cited))
    valid = [n for n in cited if 1 <= n <= len(sources)]
    status = "ANSWERED" if valid and valid == cited else "UNVERIFIED"
    return Answer(status=status, text=reply.answer.strip(), query=query, sources=sources, cited=valid)


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "What documents do I need to bring to register?"
    a = answer(q)
    print(f"[{a.status}] {a.text}")
    for s in a.sources:
        mark = "*" if s.n in a.cited else " "
        print(f" {mark}[{s.n}] {s.doc_id} Section {s.section} ({s.section_title})  score {s.score}")
