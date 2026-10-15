"""Grounding check: every time, amount and number in an answer must appear in the evidence it cites.

This is a narrow, deterministic version of a contextual grounding check. It cannot judge
whether a sentence is supported, but it catches the most harmful kind of error for a
clinic: a wrong time, fee, age or limit. Section and rule numbers ("Section 2", "2.1") are
ignored because they are references, not facts.
"""
import re

TIME = re.compile(r"\b(\d{1,2}):(\d{2})\s*(am|pm)?", re.I)
MONEY = re.compile(r"RM\s?(\d+(?:\.\d{2})?)", re.I)
# A full stop after a number ends the sentence ("is 70."); a digit after it makes a decimal.
NUMBER = re.compile(r"(?<![\w.:])(\d+)(?![\w:]|\.\d)")
REFERENCE = re.compile(r"\b(section|rule|sop-0?)\s*\d+(\.\d+)?|\b\d+\.\d+\b", re.I)


def _times(text: str) -> set[str]:
    return {f"{int(h)}:{m}{(ap or '').lower()}" for h, m, ap in TIME.findall(text)}


def _money(text: str) -> set[str]:
    return {f"{float(v):.2f}" for v in MONEY.findall(text)}


def _numbers(text: str) -> set[str]:
    text = REFERENCE.sub(" ", TIME.sub(" ", MONEY.sub(" ", text)))
    return set(NUMBER.findall(text))


def ungrounded_facts(answer: str, evidence: str, question: str = "") -> list[str]:
    """Return the times, amounts and numbers in the answer that the evidence (or question) lacks."""
    source = f"{evidence}\n{question}"
    missing = []
    src_times = _times(source)
    # "5:00 pm" in the answer is grounded by "5:00 pm" or "5:00" in the evidence.
    src_bare = {t.rstrip("apm") for t in src_times}
    for t in _times(answer):
        if t not in src_times and t.rstrip("apm") not in src_bare:
            missing.append(t)
    missing += [f"RM{v}" for v in _money(answer) - _money(source)]
    missing += sorted(_numbers(answer) - _numbers(source) - {"0", "1"})
    return missing
