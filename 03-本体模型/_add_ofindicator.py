# -*- coding: utf-8 -*-
"""向 属性与关系.md §一 插入 ofIndicator，并重排该表。"""
from pathlib import Path
import unicodedata

P = str(Path(__file__).resolve().parent / "属性与关系.md")


def w(s):
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)


def pad(s, n):
    return s + " " * max(0, n - w(s))


def is_sep(r):
    return all(set(c) <= set("-: ") for c in r)


lines = open(P, encoding="utf-8", newline="").read().replace("\r\n", "\n").split("\n")
start = next(k for k, l in enumerate(lines) if l.startswith("| 关系"))
end = start
while end < len(lines) and lines[end].startswith("|"):
    end += 1
rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in lines[start:end]]
assert not any(len(r) > 2 and r[2] == "`ofIndicator`" for r in rows), "已存在"

NEW = ["针对指标", "of indicator", "`ofIndicator`", "AssessmentResult / IndicatorJudgement → Indicator",
       "**2026-11-08 新增**：评估结果 / 指标判断**针对哪个指标**，基数 1..1。原设计只经 `produces` 反查体检活动，而一个活动用 55 个指标，反查是**多对多**、无法定位到具体指标——聚合对账、判断唯一性校验都缺这把钥匙",
       "建模稿（本轮新增）"]
k = next(a for a, r in enumerate(rows) if len(r) > 2 and r[2] == "`assesses`")
rows.insert(k + 1, NEW)

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
lines[start:end] = out
open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("OK rows", len(rows))
