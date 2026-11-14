"""Body-text word count of the manuscript, per section, against the 8,000-8,100 target (author's decision).

Counts words in running text and headings with texcount; captions, tables, equations, the abstract,
keywords, declarations and references are excluded (they do not count towards the limit).
    python paper/tools/wordcount.py
"""
import re
import subprocess
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
SECTIONS = ["01_introduction", "02_related_work", "03_data", "04_method", "05_experiments",
            "06_results", "07_discussion", "08_conclusions"]
BUDGET = {"01_introduction": 850, "02_related_work": 850, "03_data": 900, "04_method": 1700,
          "05_experiments": 880, "06_results": 1800, "07_discussion": 850, "08_conclusions": 250}
TARGET = (8000, 8100)


def count(path):
    out = subprocess.run(["texcount", "-merge", "-brief", "-utf8", "-sum=1,1,0,0,0,0,0", str(path)],
                         capture_output=True, text=True, encoding="utf-8").stdout
    # -sum=1,1,0,...: text words + header words; captions, floats, inline and displayed math excluded
    m = re.search(r"^\s*(\d+)", out.strip().splitlines()[-1]) if out.strip() else None
    return int(m.group(1)) if m else 0


def main():
    total = 0
    print(f"{'section':18s} {'words':>6s} {'budget':>7s}")
    for s in SECTIONS:
        f = PAPER / "sections" / f"{s}.tex"
        n = count(f) if f.exists() else 0
        total += n
        print(f"{s:18s} {n:6d} {BUDGET[s]:7d}")
    lo, hi = TARGET
    state = "within target" if lo <= total <= hi else ("below target" if total < lo else "ABOVE target")
    print(f"{'total':18s} {total:6d} {sum(BUDGET.values()):7d}   ({state}: {lo:,}-{hi:,})")


if __name__ == "__main__":
    main()
