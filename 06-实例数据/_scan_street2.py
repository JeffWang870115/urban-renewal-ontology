from pathlib import Path
# -*- coding: utf-8 -*-
"""逐个街道打印「老旧」相关指标块的完整采集行"""
import glob
import os
import warnings

import openpyxl

warnings.filterwarnings("ignore")
def _locate_src():
    _root = Path(__file__).resolve().parent.parent
    _h = sorted(glob.glob(str(_root / "01-资料" / "**" / "楼栋数据汇总表.xlsx"), recursive=True))
    return Path(_h[0]).parent if _h else (_root / "01-资料")
B = str(_locate_src())
files = [f for f in sorted(glob.glob(os.path.join(B, "街道维度调查统计表(1)", "**", "*.xlsx"), recursive=True))
         if not os.path.basename(f).startswith("~$")]

for p in files:
    wb = openpyxl.load_workbook(p, data_only=True)
    ws = wb.worksheets[0]
    print("\n=====", os.path.basename(p), "行数", ws.max_row)
    r = 12
    while r <= ws.max_row:
        nm = ws.cell(r, 2).value
        if nm and ("老旧" in str(nm) or "厂区" in str(nm) or "商业街区" in str(nm)):
            end = r + 1
            while end <= ws.max_row and not (ws.cell(end, 2).value and str(ws.cell(end, 2).value).strip()):
                end += 1
            print(f"\n-- [{r}-{end-1}] {str(nm).strip()}")
            for k in range(r, end):
                a = ws.cell(k, 4).value
                e = ws.cell(k, 5).value
                f = ws.cell(k, 6).value
                g = ws.cell(k, 7).value
                print("   实体:", ("" if a is None else str(a).strip())[:14],
                      "| 名称:", ("" if e is None else str(e).strip())[:18],
                      "| 属性:", ("" if f is None else str(f).strip())[:18],
                      "| 值:", ("" if g is None else str(g).strip())[:40])
            r = end
        else:
            r += 1
    wb.close()
