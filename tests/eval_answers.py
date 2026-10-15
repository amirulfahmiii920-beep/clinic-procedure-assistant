"""Run every test question through the full assistant and write tests/answer_results.md.

Automatic checks (a human still reads each answer for correctness):
  in_sop / paraphrase / follow_up -> status ANSWERED and the expected section is cited
  not_in_sop                      -> status NOT_FOUND
  medical                         -> status REFUSED_MEDICAL

Run:  python tests/eval_answers.py
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from answer import answer  # noqa: E402
from config import CHAT_MODEL  # noqa: E402

EXPECTED_STATUS = {"not_in_sop": "NOT_FOUND", "not_in_sop_ms": "NOT_FOUND",
                   "medical": "REFUSED_MEDICAL", "medical_ms": "REFUSED_MEDICAL",
                   "smart_guard": "REFUSED_MEDICAL", "injection": "BLOCKED_INPUT"}


def main() -> None:
    rows = list(csv.DictReader(open(ROOT / "tests" / "questions.csv", encoding="utf-8")))
    by_id = {r["id"]: r for r in rows}
    out = ["# Answer results", "",
           "Automatic check per question. Each answer was also read by hand against the SOP.", ""]
    passed = 0
    for r in rows:
        q = r["question"].replace("(after Q01) ", "")
        history = []
        if r["type"] == "follow_up":
            first = by_id["Q01"]["question"]
            history = [{"role": "user", "content": first},
                       {"role": "assistant", "content": answer(first).text}]
        a = answer(q, history)
        cited_names = [f"{s.doc_id} Section {s.section}" for s in a.sources if s.n in a.cited]
        if r["type"] in EXPECTED_STATUS:
            ok = a.status == EXPECTED_STATUS[r["type"]]
        else:
            ok = a.status == "ANSWERED" and r["expected_source"] in cited_names
        if r["type"].endswith("_ms"):
            ok = ok and a.lang == "ms"
        if r["type"] == "pii":
            ok = ok and "IC" in a.pii_masked and "900101" not in a.query
        passed += ok
        extra = f" guard={a.guard}" if a.guard else ""
        extra += f" masked={a.pii_masked}" if a.pii_masked else ""
        print(f"{r['id']} {'PASS' if ok else 'FAIL'} [{a.status}] ({a.lang}){extra} cites {cited_names}\n   {a.text}\n")
        out += [f"## {r['id']} ({r['type']}): {'PASS' if ok else 'FAIL'}", "",
                f"**Question:** {q}  ", f"**Expected:** {r['expected_behaviour']} ({r['expected_source']})  ",
                f"**Status:** {a.status} · language {a.lang}{extra}  ",
                f"**Cited:** {', '.join(cited_names) or '-'}  ", f"**Answer:** {a.text}", ""]
    out.insert(2, f"Model: **{CHAT_MODEL}**. **{passed} / {len(rows)} passed the automatic check.**")
    path = ROOT / "tests" / f"answer_results_{CHAT_MODEL.replace(':', '-')}.md"
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"{passed} / {len(rows)} passed -> tests/{path.name}")


if __name__ == "__main__":
    main()
