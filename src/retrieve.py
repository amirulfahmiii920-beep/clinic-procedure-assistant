"""Find the SOP sections most relevant to a question.

Run:  python src/retrieve.py "What documents do I need to register?"
"""
import json
import math
import sqlite3
import sys
from pathlib import Path

from config import EMBED_MODEL, INDEX_PATH, MIN_SCORE, QUERY_PREFIX, TOP_K
from ollama_client import embed


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def load_index(db_path: Path = INDEX_PATH) -> list[dict]:
    if not db_path.exists():
        raise SystemExit("Index not found. Run: python src/ingest.py")
    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        built_with = con.execute("SELECT value FROM meta WHERE key='embed_model'").fetchone()[0]
        if built_with != EMBED_MODEL:
            raise SystemExit(f"Index was built with {built_with}, config uses {EMBED_MODEL}. "
                             "Rebuild it: python src/ingest.py")
        rows = [dict(r) for r in con.execute("SELECT * FROM chunks")]
    for r in rows:
        r["vector"] = json.loads(r["vector"])
    return rows


def retrieve(question: str, k: int = TOP_K, min_score: float = MIN_SCORE,
             db_path: Path = INDEX_PATH) -> list[dict]:
    """Return up to k chunks scoring at least min_score, best first. Empty list = no evidence."""
    rows = load_index(db_path)
    q = embed([QUERY_PREFIX + question], EMBED_MODEL)[0]
    scored = sorted(({**r, "score": cosine(q, r["vector"])} for r in rows),
                    key=lambda r: r["score"], reverse=True)
    for r in scored:
        del r["vector"]
    return [r for r in scored[:k] if r["score"] >= min_score]


def rank_all(question: str, db_path: Path = INDEX_PATH) -> list[dict]:
    """Every chunk with its score, best first (used to calibrate MIN_SCORE)."""
    return retrieve(question, k=10_000, min_score=-1.0, db_path=db_path)


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "What documents do I need to bring to register?"
    hits = retrieve(question)
    print(f"Q: {question}")
    if not hits:
        print("No SOP section scored above the cutoff. The assistant will say it does not know.")
    for h in hits:
        print(f"  {h['score']:.3f}  [{h['doc_id']}, Section {h['section']}] {h['section_title']}")
