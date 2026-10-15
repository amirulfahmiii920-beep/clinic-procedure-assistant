"""Append one audit event per answered question to logs/audit.jsonl.

The event records the decision, not the conversation: no question text, no answer text
and no identifiers. A short hash of the masked question lets an owner spot repeats
without being able to read what a patient asked.
"""
import hashlib
import json
from datetime import datetime, timezone

from config import ROOT

LOG_PATH = ROOT / "logs" / "audit.jsonl"


def log_event(status: str, masked_question: str, lang: str, pii_types: list[str],
              cited: list[str], model: str, latency_s: float, reason: str | None = None) -> None:
    event = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "reason": reason,
        "lang": lang,
        "question_hash": hashlib.sha256(masked_question.encode()).hexdigest()[:12],
        "question_chars": len(masked_question),
        "pii_masked": sorted(set(pii_types)),
        "cited": cited,
        "model": model,
        "latency_s": round(latency_s, 2),
    }
    try:
        LOG_PATH.parent.mkdir(exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except OSError:
        pass  # logging must never break answering
