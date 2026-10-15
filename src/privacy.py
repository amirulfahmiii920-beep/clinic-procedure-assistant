"""Mask personal identifiers before a question reaches retrieval, the model or the logs.

Only the identifiers this clinic's patients are likely to type are covered: MyKad
numbers, Malaysian phone numbers, e-mail addresses and passport numbers. Names and
addresses are NOT detected; pattern masking alone does not make text anonymous.
"""
import re

PATTERNS = [
    # MyKad: YYMMDD-PB-###G, with or without dashes or spaces
    ("IC", re.compile(r"\b\d{6}[-\s]?\d{2}[-\s]?\d{4}\b")),
    # Malaysian mobile and landline numbers, local or +60 format
    ("PHONE", re.compile(r"(?:\+?60|\b0)1\d[-\s]?\d{3,4}[-\s]?\d{4}\b|(?:\+?60|\b0)[3-9][-\s]?\d{3,4}[-\s]?\d{4}\b")),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    # Passport: one or two letters followed by 7 to 8 digits (e.g. A12345678)
    ("PASSPORT", re.compile(r"\b[A-Z]{1,2}\d{7,8}\b")),
]


def mask_pii(text: str) -> tuple[str, list[str]]:
    """Return the masked text and the list of identifier types that were masked."""
    found = []
    for label, pattern in PATTERNS:
        text, n = pattern.subn(f"[{label}]", text)
        found += [label] * n
    return text, found
