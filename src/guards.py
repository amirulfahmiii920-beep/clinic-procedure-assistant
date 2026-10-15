"""Scope guard: refuse medical-advice questions before any retrieval or model call.

The assistant answers clinic procedure questions only. Questions about medicines,
doses, diagnosis or treatment are refused and pointed to a doctor. Emergency
symptoms are NOT blocked here, because SOP-05 tells patients where to go.
"""
import re

MEDICAL_PATTERNS = [
    r"\bmedicines?\b", r"\bmedications?\b", r"\bdrugs?\b", r"\bdos(e|es|age)\b",
    r"\btablets?\b", r"\bpills?\b", r"\bantibiotics?\b", r"\bparacetamol\b", r"\bpanadol\b",
    r"\bprescribe\b", r"\bdiagnos\w*", r"\bcure\b", r"\btreat(ment)? (for|my)\b",
    r"\bshould i take\b", r"\bwhat (disease|illness|condition) do i have\b",
    r"\bis (it|this) (serious|cancer|infected)\b",
]
_MEDICAL = re.compile("|".join(MEDICAL_PATTERNS), re.I)

# Collecting a prescription at the pharmacy is a procedure question, not medical advice.
_ALLOWED = re.compile(r"\b(collect|pick up|pharmacy (hours|counter)|where is the pharmacy)\b", re.I)

REFUSAL = ("I can only answer questions about the clinic's procedures, such as registration, "
           "opening hours, fees and appointments. I can't give advice about medicines, symptoms "
           "or treatment. Please ask a doctor or pharmacist at the clinic. If it is an emergency, "
           "go straight to the treatment room or call 999.")


def is_medical_advice(question: str) -> bool:
    return bool(_MEDICAL.search(question)) and not _ALLOWED.search(question)
