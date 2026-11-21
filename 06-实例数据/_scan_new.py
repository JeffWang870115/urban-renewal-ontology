import glob
import os
from pathlib import Path
# -*- coding: utf-8 -*-
"""查看街区/社区/小区数据表结构"""
import warnings

import openpyxl

warnings.filterwarnings("ignore")
def _locate_src():
    _root = Path(__file__).resolve().parent.parent
    _h = sorted(glob.glob(str(_root / "01-资料" / "**" / "楼栋数据汇总表.xlsx"), recursive=True))
    return Path(_h[0]).parent if _h else (_root / "01-资料")
B = str(_locate_src())
for fn in ["街区数据.xlsx", "社区数据.xlsx", "小区数据.xlsx"]:
    p = B + "/" + fn
    wb = openpyxl.load_workbook(p, data_only=True)
    print("\n" + "=" * 70)
    print(fn, "| sheets:", wb.sheetnames)
    for ws in wb.worksheets:
        print(f"-- {ws.title}: {ws.max_row} 行 x {ws.max_column} 列")
        for i, row in enumerate(ws.iter_rows(min_row=1, max_row=min(5, ws.max_row), values_only=True), 1):
            cells = [("" if c is None else str(c).strip())[:18] for c in row[:14]]
            print(f"   r{i}: {cells}")
    wb.close()
