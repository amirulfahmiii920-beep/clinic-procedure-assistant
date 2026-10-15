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
              cited: list[str], model: str, latency_s: float, reason: str | None = None,
              usage: dict | None = None) -> None:
    usage = usage or {}
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
        # Model calls and tokens (embedding + chat). Local inference is free, but on a hosted
        # API these numbers are what the cost would be based on.
        "model_calls": usage.get("calls", 0),
        "tokens_in": usage.get("tokens_in", 0),
        "tokens_out": usage.get("tokens_out", 0),
    }
    try:
        LOG_PATH.parent.mkdir(exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except OSError:
        pass  # logging must never break answering
