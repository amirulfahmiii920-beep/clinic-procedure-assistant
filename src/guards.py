"""Safety checks that run before and after the model.

Input checks
  check_input()        empty, too long, or a prompt-injection attempt
  is_medical_advice()  fast keyword guard (English and Malay)
  classify_scope()     model-based guard for medical questions the keywords miss
Output check
  output_has_medical_advice()  blocks an answer that drifts into dosing or treatment

Emergency symptoms are NOT blocked: SOP-05 tells patients where to go.
"""
import re

from pydantic import BaseModel, ValidationError

from config import CHAT_MODEL
from ollama_client import OllamaUnavailable, chat

MAX_QUESTION_CHARS = 500

# ---------- input: length and prompt injection ----------
INJECTION = re.compile(
    r"\b(ignore|disregard|forget|override)\b.{0,30}\b(instructions?|rules?|prompt|above|previous)\b"
    r"|\bsystem prompt\b|\byou are now\b|\bact as\b|\bjailbreak\b|\bdeveloper mode\b"
    r"|\babaikan\b.{0,30}\b(arahan|peraturan)\b",
    re.I)


def check_input(question: str) -> str | None:
    """Return a reason code if the question must be blocked, else None."""
    if not question.strip():
        return "EMPTY"
    if len(question) > MAX_QUESTION_CHARS:
        return "TOO_LONG"
    if INJECTION.search(question):
        return "INJECTION"
    return None


# ---------- input: keyword medical guard ----------
MEDICAL_PATTERNS = [
    r"\bmedicines?\b", r"\bmedications?\b", r"\bdrugs?\b", r"\bdos(e|es|age)\b",
    r"\btablets?\b", r"\bpills?\b", r"\bantibiotics?\b", r"\bparacetamol\b", r"\bpanadol\b",
    r"\bprescribe\b", r"\bdiagnos\w*", r"\bcure\b", r"\btreat(ment)? (for|my)\b",
    r"\bshould i take\b", r"\bwhat (disease|illness|condition) do i have\b",
    r"\bis (it|this) (serious|cancer|infected)\b",
    # Malay
    r"\bubat\b", r"\bdos\b", r"\bpil\b", r"\bantibiotik\b", r"\brawat\w*\b", r"\bpenyakit apa\b",
    r"\bpatut makan\b", r"\bsakit apa\b",
]
_MEDICAL = re.compile("|".join(MEDICAL_PATTERNS), re.I)
# Procedure questions that mention medicine are allowed (collecting it, pharmacy hours, the record book).
_ALLOWED = re.compile(r"\b(collect|pick up|pharmacy|farmasi|record book|buku rekod|ambil ubat)\b", re.I)


def is_medical_advice(question: str) -> bool:
    return bool(_MEDICAL.search(question)) and not _ALLOWED.search(question)


# ---------- input: model-based scope guard ----------
class Scope(BaseModel):
    category: str  # "procedure" or "medical"


CLASSIFIER = """Classify a patient's question to a clinic help desk. Reply as JSON {"category": ...}.
"procedure": registration, documents, opening hours, fees, appointments, queues, where to go, what to do in an emergency.
"medical": asks what is wrong with them, what to take, how to treat a symptom, or for any health advice.
Examples:
"What documents do I need to register?" -> procedure
"What should I do if someone has chest pain at the clinic?" -> procedure
"How much is the fee for non-citizens?" -> procedure
"What can I take for my headache?" -> medical
"My child has a rash, is it serious?" -> medical
"How do I get rid of a cough fast?" -> medical
"Apa saya boleh makan untuk sakit kepala?" -> medical
"Klinik buka pukul berapa?" -> procedure"""


def classify_scope(question: str) -> str:
    """Return "medical" or "procedure". Fails open to "procedure" if the model is unavailable,
    because the keyword guard, the grounding rules and the output check still apply."""
    try:
        raw = chat([{"role": "system", "content": CLASSIFIER}, {"role": "user", "content": question}],
                   CHAT_MODEL, temperature=0.0, schema=Scope.model_json_schema())
        return "medical" if Scope.model_validate_json(raw).category.strip().lower() == "medical" else "procedure"
    except (OllamaUnavailable, ValidationError):
        return "procedure"


# ---------- output: medical advice in the answer ----------
OUTPUT_MEDICAL = re.compile(
    r"\b\d+\s?(mg|ml|mcg)\b"
    r"|\b(take|takes|taking|makan|ambil)\s+(\d+|a|an|some|the)?\s*(paracetamol|panadol|ibuprofen|aspirin|"
    r"antibiotics?|antibiotik|tablets?|pills?|medicine|medication|ubat)\b"
    r"|\b(you (may|might|probably) have|it (sounds|looks) like you have|you are suffering from)\b"
    r"|\b(diagnos(is|ed)|prescription for)\b",
    re.I)


def output_has_medical_advice(answer: str) -> bool:
    return bool(OUTPUT_MEDICAL.search(answer))
