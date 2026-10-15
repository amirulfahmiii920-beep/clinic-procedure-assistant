"""Semantic robustness: does the same question, asked five different ways, get the same answer?

For each topic the expected SOP section and a fact the answer must contain are fixed. Every
variant is run through the full assistant. A variant passes when it is ANSWERED, cites the
expected section and contains the fact.

Run:  python tests/eval_robustness.py      -> tests/robustness_results.md
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from answer import answer  # noqa: E402

TOPICS = [
    {
        "name": "Late arrival",
        "source": "SOP-05 Section 3",
        "fact": "30 minutes",
        "variants": [
            "I came 20 minutes after my appointment time. Will the doctor still see me?",
            "Will I still be seen if I am 20 minutes late?",
            "I'm running late for my appointment, around 20 minutes. Is that okay?",
            "What happens if I arrive late for my appointment?",
            "how late can i be for my appointment",
        ],
    },
    {
        "name": "Senior citizen fees",
        "source": "SOP-04 Section 3",
        "fact": "60",
        "variants": [
            "Do senior citizens need to pay?",
            "Is the visit free for elderly patients?",
            "My father is 70. Does he have to pay the fee?",
            "Are old people exempt from fees?",
            "fees for pensioners and seniors?",
        ],
    },
    {
        "name": "Changing an appointment",
        "source": "SOP-05 Section 2",
        "fact": "one working day",
        "variants": [
            "How do I change my appointment?",
            "Can I reschedule my appointment?",
            "I need to move my appointment to another day. What should I do?",
            "Is it possible to postpone my clinic appointment?",
            "how to change appointment date",
        ],
    },
]


def main() -> None:
    lines = ["# Semantic robustness", "",
             "Each topic is asked five ways. A variant passes when it is answered, cites the expected "
             "section and contains the key fact.", ""]
    total = passed_all = 0
    for t in TOPICS:
        lines += [f"## {t['name']} (expects {t['source']}, fact \"{t['fact']}\")", "",
                  "| Variant | Status | Cited | Fact present | Pass |", "|---|---|---|---|---|"]
        passed = 0
        for v in t["variants"]:
            a = answer(v)
            cited = [f"{s.doc_id} Section {s.section}" for s in a.sources if s.n in a.cited]
            has_fact = t["fact"].lower() in a.text.lower()
            ok = a.status == "ANSWERED" and t["source"] in cited and has_fact
            passed += ok
            lines.append(f"| {v} | {a.status} | {', '.join(cited) or '-'} | {'yes' if has_fact else 'no'} "
                         f"| {'yes' if ok else 'NO'} |")
            print(f"{'PASS' if ok else 'FAIL'} [{a.status}] {v}")
        lines += ["", f"**{passed} / {len(t['variants'])} consistent.**", ""]
        total += len(t["variants"])
        passed_all += passed
    lines.insert(3, f"**Overall: {passed_all} / {total} variants consistent.**\n")
    (ROOT / "tests" / "robustness_results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{passed_all} / {total} consistent -> tests/robustness_results.md")


if __name__ == "__main__":
    main()
