# -*- coding: utf-8 -*-
"""补 属性与关系.md 两处定义域扩展（跨表按 URI 名定位），并重排被改的表。"""
from pathlib import Path
import unicodedata

P = str(Path(__file__).resolve().parent / "属性与关系.md")

TARGET = {
    "`constructionYear`": "Building、ResidentialQuarter（小区表建造时间 r4）",
    "`renovationStatus`": "GasPipeline、EmergencyShelter、UrbanVillage、Building（危旧房）、ResidentialQuarter（小区改造情况 r5）",
}


def w(s):
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)


def pad(s, n):
    return s + " " * max(0, n - w(s))


def is_sep(r):
    return all(set(c) <= set("-: ") for c in r)


def render(rows):
    ncol = max(len(r) for r in rows)
    widths = [0] * ncol
    for r in rows:
        if is_sep(r):
            continue
        for j, c in enumerate(r):
            widths[j] = max(widths[j], w(c))
    out = []
    for r in rows:
        if is_sep(r):
            out.append("|" + "|".join("-" * (widths[j] + 2) for j in range(len(r))) + "|")
        else:
            out.append("|" + "|".join(" " + pad(c, widths[j]) + " " for j, c in enumerate(r)) + "|")
    return out


lines = open(P, encoding="utf-8", newline="").read().replace("\r\n", "\n").split("\n")
hits = []
i = 0
while i < len(lines):
    if not lines[i].startswith("|"):
        i += 1
        continue
    j = i
    while j < len(lines) and lines[j].startswith("|"):
        j += 1
    rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in lines[i:j]]
    changed = False
    for r in rows:
        if len(r) > 3 and r[1] in TARGET:
            r[2] = TARGET[r[1]]
            hits.append(r[1])
            changed = True
    if changed:
        lines[i:j] = render(rows)
    i = j

assert len(hits) == 2, hits
open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("OK", hits)
