from pathlib import Path
# -*- coding: utf-8 -*-
"""对账：小区表的指标结果 vs 我们用楼栋核查项派生的结果（只读）"""
import glob
import os
import re
import warnings

import openpyxl
from rdflib import Graph, Namespace

warnings.filterwarnings("ignore")
def _locate_src():
    _root = Path(__file__).resolve().parent.parent
    _h = sorted(glob.glob(str(_root / "01-资料" / "**" / "楼栋数据汇总表.xlsx"), recursive=True))
    return Path(_h[0]).parent if _h else (_root / "01-资料")
B = str(_locate_src())
ROOT = str(Path(__file__).resolve().parent.parent) + "/"
UR = Namespace("https://ontology.cset-digital.cn/urban-renewal#")


def norm(s):
    s = str(s or "").strip()
    s = re.sub(r"\s+", "", s)
    s = s.replace("（", "(").replace("）", ")")
    s = re.sub(r"居委会$", "", s)
    return s


# 目录结构 → 编号（与 _gen_abox.py 同口径）
nb_names = sorted({os.path.basename(f).replace(".xlsx", "")
                   for f in glob.glob(os.path.join(B, "街道维度调查统计表(1)", "**", "*.xlsx"), recursive=True)
                   if not os.path.basename(f).startswith("~$")})
NB = {n: "NB_" + chr(ord("A") + i) for i, n in enumerate(nb_names)}

cm_keys = set()
for f in glob.glob(os.path.join(B, "社区维度调查统计表(1)", "**", "*.xlsx"), recursive=True):
    if os.path.basename(f).startswith("~$"):
        continue
    parts = os.path.relpath(f, os.path.join(B, "社区维度调查统计表(1)")).split(os.sep)
    cm_keys.add((parts[-2], parts[-1].replace(".xlsx", "")))
CM = {k: "CM_S%02d" % (i + 1) for i, k in enumerate(sorted(cm_keys))}

rq_keys = set()
for f in glob.glob(os.path.join(B, "住房维度调查统计表(1)", "**", "*.xlsx"), recursive=True):
    if os.path.basename(f).startswith("~$"):
        continue
    parts = os.path.relpath(f, os.path.join(B, "住房维度调查统计表(1)")).split(os.sep)
    rq_keys.add((parts[-3], parts[-2], parts[-1].replace(".xlsx", "")))
RQ = {k: "RQ_R%03d" % (i + 1) for i, k in enumerate(sorted(rq_keys))}

g = Graph().parse(ROOT + "06-实例数据/abox/城市体检实例.ttl", format="turtle")

# 小区表：2025 编号 → 2026 编号
COL = {13: (1, 1), 15: (2, 2), 17: (3, 3), 19: (4, 4), 23: (5, None),
       25: (6, 5), 27: (7, 6), 29: (8, 7), 31: (9, 8)}
stat = {v[1]: {"n": 0, "diff": 0, "sum_diff": 0, "unmatched": 0} for v in COL.values() if v[1]}

wb = openpyxl.load_workbook(B + "/小区数据.xlsx", data_only=True)
ws = wb.worksheets[0]
rows = 0
cur_st = cur_cm = ""
for r in range(5, ws.max_row + 1):
    st, cmn, rqn = ws.cell(r, 1).value, ws.cell(r, 2).value, ws.cell(r, 3).value
    if st and str(st).strip():
        cur_st = str(st).strip()
    if cmn and str(cmn).strip():
        cur_cm = str(cmn).strip()
    if not rqn:
        continue
    key = (cur_st, cur_cm, str(rqn).strip())
    code = RQ.get(key) or RQ.get((norm(key[0]), norm(key[1]), norm(key[2])))
    if code is None:
        # 归一化再试一次
        cand = [c for k, c in RQ.items() if norm(k[2]) == norm(key[2])]
        code = cand[0] if len(cand) == 1 else None
    if code is None:
        rows += 1
        continue
    rows += 1
    for col, (sy, y26) in COL.items():
        if y26 is None:
            continue
        raw = ws.cell(r, col).value
        if raw is None or str(raw).strip() == "":
            continue
        try:
            v = float(str(raw).replace("%", "").strip())
        except ValueError:
            continue
        ar = UR["AR_%s_I%02d" % (code, y26)]
        av = g.value(ar, UR.indicatorValue)
        if av is None:
            stat[y26]["unmatched"] += 1
            continue
        stat[y26]["n"] += 1
        d = abs(float(av) - v)
        if d > 0.001:
            stat[y26]["diff"] += 1
            stat[y26]["sum_diff"] += d
wb.close()

print("小区表参与对账行数:", rows)
print("指标 | 可比小区数 | 不一致 | 差异合计")
for k in sorted(stat):
    s = stat[k]
    print(f"  {k} | {s['n']} | {s['diff']} | {s['sum_diff']:.0f}")
