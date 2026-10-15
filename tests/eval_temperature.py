"""Inference parameter experiment: how does temperature change answers?

Three questions are each asked three times at temperatures 0.0, 0.7 and 1.2. For each
setting we record how often the three runs gave the same answer word for word, and how
often the answer contained the key fact and passed every check (status ANSWERED).

Run:  python tests/eval_temperature.py      -> tests/temperature_results.md
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from answer import answer  # noqa: E402

QUESTIONS = [
    ("What time does the clinic close on Friday?", "5:00"),
    ("How much do non-citizens pay for a visit?", "RM40"),
    ("I came 20 minutes after my appointment time. Will the doctor still see me?", "30 minutes"),
]
TEMPERATURES = [0.0, 0.7, 1.2]
RUNS = 3


def main() -> None:
    lines = ["# Temperature experiment", "",
             f"{len(QUESTIONS)} questions x {RUNS} runs at each temperature. *Identical* = all runs gave "
             "the same text. *Correct* = answered, passed the checks and contained the key fact.", "",
             "| Temperature | Identical across runs | Correct answers | Answers flagged for review |",
             "|---|---|---|---|"]
    detail = ["", "## Answers", ""]
    for t in TEMPERATURES:
        identical = correct = flagged = 0
        for q, fact in QUESTIONS:
            texts = []
            for _ in range(RUNS):
                a = answer(q, temperature=t)
                texts.append(a.text)
                squash = lambda s: s.lower().replace(" ", "")  # noqa: E731  "5:00 pm" == "5:00pm"
                correct += a.status == "ANSWERED" and squash(fact) in squash(a.text)
                flagged += a.status == "UNVERIFIED"
            identical += len(set(texts)) == 1
            detail += [f"**t={t}** · {q}", ""] + [f"- {x}" for x in texts] + [""]
        n = len(QUESTIONS) * RUNS
        lines.append(f"| {t} | {identical} / {len(QUESTIONS)} questions | {correct} / {n} | {flagged} / {n} |")
        print(f"t={t}: identical {identical}/{len(QUESTIONS)}, correct {correct}/{n}, flagged {flagged}/{n}")
    (ROOT / "tests" / "temperature_results.md").write_text("\n".join(lines + detail) + "\n", encoding="utf-8")
    print("-> tests/temperature_results.md")


if __name__ == "__main__":
    main()
