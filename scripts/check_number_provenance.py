#!/usr/bin/env python3
"""Report measurements in a generated post that appear nowhere in the source logs.

2026-08-08: the weekly post rendered an 8/1 design study as lived experience and
supplied its own figures ("30秒に伸ばしたら", "2%/日"). The generator prompt now
forbids that, but a prompt is not a guarantee — the model can drop it on any run.
A number is checkable, so this checks it: every measured value in the post must
exist somewhere in logs/. A value that does not was invented by the model.

Precision over recall on purpose. Only numbers carrying a unit are examined, and
a hit anywhere in logs/ counts as grounded — so a flagged number is a real find,
not a guess. It never blocks publishing; it prints so the reviewer knows to look.

Usage: check_number_provenance.py <post.md> [logs_dir]
Exit 0 always (advisory). Prints "OK" or the unsourced values.
"""
import re
import sys
from pathlib import Path

UNITS = (
    "%|％|秒|分|時間|日|週|ヶ月|か月|件|倍|回|個|台|人|円|"
    "GB|MB|TB|KB|GHz|MHz|ms|W|kW|B|文字|行|本|枚"
)
MEASURE = re.compile(rf"(\d+(?:[.,]\d+)?)\s*({UNITS})")
# 2026年 / 2026-08-01 / 8月1日 are timestamps, not measurements.
DATEISH = re.compile(r"\d{4}\s*[-/年]|\d{1,2}\s*[月日]\s*$")


def measurements(text: str) -> list[tuple[str, str]]:
    found = []
    for m in MEASURE.finditer(text):
        value, unit = m.group(1), m.group(2)
        window = text[max(0, m.start() - 6): m.end()]
        if DATEISH.search(window):
            continue
        if unit in ("日", "分", "時間") and len(value) == 4:
            continue
        found.append((value, unit))
    return found


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: check_number_provenance.py <post.md> [logs_dir]", file=sys.stderr)
        return 0
    post = Path(sys.argv[1])
    logs_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else post.resolve().parents[1] / "logs"
    if not post.is_file():
        print(f"provenance: {post} が読めないので確認をとばした")
        return 0

    corpus = ""
    if logs_dir.is_dir():
        for p in sorted(logs_dir.rglob("*")):
            if p.is_file() and p.suffix in (".md", ".txt", ".json", ".jsonl"):
                corpus += p.read_text(encoding="utf-8", errors="ignore")
    if not corpus:
        print(f"provenance: {logs_dir} に元ログが無いので確認をとばした")
        return 0

    unsourced = []
    for value, unit in measurements(post.read_text(encoding="utf-8")):
        # The value must appear WITH its unit. Matching the bare digits would let
        # "30" in any timestamp vouch for "30秒" — which is how the 8/7 post passed
        # a first version of this check.
        plain = re.escape(value.replace(",", ""))
        grouped = re.escape(value)
        unit_alt = re.escape(unit)
        if unit in ("%", "％"):
            unit_alt = "[%％]"
        if re.search(rf"(?:{plain}|{grouped})\s*{unit_alt}", corpus):
            continue
        pair = f"{value}{unit}"
        if pair not in unsourced:
            unsourced.append(pair)

    if unsourced:
        print(f"provenance: 元ログに無い数値 {len(unsourced)}件 — {' / '.join(unsourced[:12])}")
    else:
        print("provenance: OK（本文の数値はすべて元ログにある）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
