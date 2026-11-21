from pathlib import Path
# -*- coding: utf-8 -*-
"""W-C02 前置：精确核对四类源表结构（只读，不写项目文件）"""
import glob
import os
import openpyxl

def _locate_src():
    _root = Path(__file__).resolve().parent.parent
    _h = sorted(glob.glob(str(_root / "01-资料" / "**" / "楼栋数据汇总表.xlsx"), recursive=True))
    return Path(_h[0]).parent if _h else (_root / "01-资料")
B = str(_locate_src())
def dump(path, rows=8, cols=8, tag=""):
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb.worksheets[0]
    print(f"\n### {tag} | {os.path.basename(path)} | {ws.max_row} x {ws.max_column}")
    for i, r in enumerate(ws.iter_rows(min_row=1, max_row=min(rows, ws.max_row), values_only=True), 1):
        vals = [("" if c is None else str(c).strip())[:16] for c in r[:cols]]
        print(f"  r{i}: {vals}")
    wb.close()


# 街区（取第一个）
nb = sorted(glob.glob(os.path.join(B, "街道维度调查统计表(1)", "**", "*.xlsx"), recursive=True))
print("街区表数量:", len(nb))
if nb:
    dump(nb[0], rows=14, cols=6, tag="街区")

# 社区
cm = sorted(glob.glob(os.path.join(B, "社区维度调查统计表(1)", "**", "*.xlsx"), recursive=True))
print("\n社区表数量:", len(cm))
if cm:
    dump(cm[0], rows=26, cols=6, tag="社区")

# 住房（小区）
rq = sorted(glob.glob(os.path.join(B, "住房维度调查统计表(1)", "**", "*.xlsx"), recursive=True))
print("\n住房表数量:", len(rq))
if rq:
    dump(rq[0], rows=12, cols=6, tag="住房(小区)")

# 城区
ud = glob.glob(os.path.join(B, "城区维度指标结果", "*.xlsx"))
print("\n城区表:", ud)
if ud:
    dump(ud[0], rows=4, cols=12, tag="城区")
