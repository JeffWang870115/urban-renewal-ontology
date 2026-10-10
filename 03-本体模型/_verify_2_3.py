# -*- coding: utf-8 -*-
"""校验 2026-09-29 借鉴定（二、三建议）落盘：CRLF、表格列数一致、新增段落存在。"""
import os, re

BASE = r"E:\中设数字\00-01-个人\02-学习\01-wordbuddy\2026_working_space\城市体检与更新本体研究"
FILES = [
    r"03-本体模型\类与层级.md",
    r"03-本体模型\属性与关系.md",
    r"02-术语与概念\概念清单.md",
]

def cjk_w(s):
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)

for rel in FILES:
    p = os.path.join(BASE, rel)
    raw = open(p, "rb").read()
    print("=" * 70)
    print(rel, "| bytes=", len(raw), "| CRLF=", raw.count(b"\r\n"), "| LF=", raw.count(b"\n"),
          "| CRLF=0 ->", raw.count(b"\r\n") == 0)
    text = raw.decode("utf-8")
    lines = text.split("\n")
    # 表格块列数一致性
    blocks, cur = [], []
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("|"):
            cur.append((i + 1, ln))
        else:
            if cur:
                blocks.append(cur); cur = []
    if cur:
        blocks.append(cur)
    bad = 0
    for blk in blocks:
        counts = [ln.count("|") for _, ln in blk]
        if len(set(counts)) != 1:
            bad += 1
            print("  [列数不一致] 行", blk[0][0], "-", blk[-1][0], "pipe count=", sorted(set(counts)))
    print("  表格块数=", len(blocks), "| 列数不一致块数=", bad)
    # 新增段落/关键表头
    for kw in ["### 2.9", "#### 2.9.1", "#### 2.9.2", "#### 2.9.3", "#### 2.9.4",
               "分类父类", "FormulaType", "CollectionMethod", "ProblemCause",
               "TemporalTrend", "ProblemIndicatorMapping", "problemCategory",
               "## 九、借鉴同事成果新增概念", "## 三、借鉴同事成果新增的属性与约束"]:
        hit = text.count(kw)
        if hit:
            print("  含 %-32s x%d" % (kw, hit))
print("=" * 70)
print("DONE")
