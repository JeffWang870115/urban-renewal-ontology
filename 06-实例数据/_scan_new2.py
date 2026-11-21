import glob
import os
from pathlib import Path
# -*- coding: utf-8 -*-
"""打印三份汇总表每一列的表头（分类/编码/名称/子列）"""
import warnings

import openpyxl

warnings.filterwarnings("ignore")
def _locate_src():
    _root = Path(__file__).resolve().parent.parent
    _h = sorted(glob.glob(str(_root / "01-资料" / "**" / "楼栋数据汇总表.xlsx"), recursive=True))
    return Path(_h[0]).parent if _h else (_root / "01-资料")
B = str(_locate_src())
SPEC = [("街区数据.xlsx", 3), ("社区数据.xlsx", 3), ("小区数据.xlsx", 4)]
for fn, hdr in SPEC:
    wb = openpyxl.load_workbook(B + "/" + fn, data_only=True)
    ws = wb.worksheets[0]
    print("\n" + "=" * 78)
    print(fn, f"| {ws.max_row} x {ws.max_column} | 表头 {hdr} 行")
    for c in range(1, ws.max_column + 1):
        parts = []
        for r in range(1, hdr + 1):
            v = ws.cell(r, c).value
            if v is not None and str(v).strip():
                parts.append(str(v).strip().replace("\n", "")[:22])
        print(f"  c{c:>2}: " + " | ".join(parts))
    wb.close()
