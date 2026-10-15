"""Human-in-the-loop review queue.

Answers the system is not confident about (citation check failed, grounding check failed,
or the output guard withheld the draft) are added to logs/review_queue.jsonl so clinic
staff can check them and fix the SOPs or the prompts. Only the masked question is stored,
never the original text, and the queue stays on the local machine.
"""
import json
from datetime import datetime, timezone

from config import ROOT

QUEUE_PATH = ROOT / "logs" / "review_queue.jsonl"


def add_to_review(status: str, reason: str | None, masked_question: str, draft: str,
                  sources: list[str]) -> None:
    item = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "reason": reason,
        "masked_question": masked_question,
        "draft_answer": draft,
        "sources": sources,
        "reviewed": False,
    }
    try:
        QUEUE_PATH.parent.mkdir(exist_ok=True)
        with QUEUE_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    except OSError:
        pass
