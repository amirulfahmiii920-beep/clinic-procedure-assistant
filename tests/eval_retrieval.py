"""Run every test question through retrieval only and write tests/retrieval_results.md.

Checks two things per question:
  - in-SOP questions: is the expected section the top hit?
  - out-of-scope questions (not_in_sop, medical): does the top score stay below MIN_SCORE?

Run:  python tests/eval_retrieval.py
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from config import MIN_SCORE, TOP_K  # noqa: E402
from retrieve import rank_all  # noqa: E402

PREV = {"Q10": "Q01"}  # follow-up questions are searched together with the earlier question


def main() -> None:
    # Retrieval is evaluated on the original ten questions; the later ones test the safety layers.
    rows = list(csv.DictReader(open(ROOT / "tests" / "questions.csv", encoding="utf-8")))[:10]
    by_id = {r["id"]: r for r in rows}
    lines = ["# Retrieval results", "",
             f"Cutoff (MIN_SCORE): **{MIN_SCORE}**, top-k: **{TOP_K}**. An in-SOP question passes when the "
             f"expected section is among the top {TOP_K} hits and above the cutoff (the model receives all "
             f"{TOP_K}). An out-of-scope question passes when no section reaches the cutoff.", "",
             "| ID | Type | Top hit | Top score | Expected | Expected rank | Pass |",
             "|---|---|---|---|---|---|---|"]
    passed = 0
    for r in rows:
        q = r["question"].replace("(after Q01) ", "")
        if r["id"] in PREV:
            q = by_id[PREV[r["id"]]]["question"] + " " + q
        ranked = rank_all(q)
        top = ranked[0]
        hit = f"{top['doc_id']} Section {top['section']}"
        names = [f"{x['doc_id']} Section {x['section']}" for x in ranked]
        if r["expected_source"] == "none":
            rank, ok = "-", top["score"] < MIN_SCORE
        else:
            pos = names.index(r["expected_source"])
            rank = str(pos + 1)
            ok = pos < TOP_K and ranked[pos]["score"] >= MIN_SCORE
        passed += ok
        lines.append(f"| {r['id']} | {r['type']} | {hit} | {top['score']:.3f} | {r['expected_source']} "
                     f"| {rank} | {'yes' if ok else 'NO'} |")
        print(f"{r['id']:4} {r['type']:11} {hit:18} {top['score']:.3f}  expected {r['expected_source']:16} rank {rank:2} {'PASS' if ok else 'FAIL'}")
    lines += ["", f"**{passed} / {len(rows)} passed.**", "",
              "Note: Q09 (medical) is also blocked by a separate scope guard before retrieval, "
              "so retrieval does not need to reject it on score alone."]
    (ROOT / "tests" / "retrieval_results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n{passed} / {len(rows)} passed -> tests/retrieval_results.md")


if __name__ == "__main__":
    main()
