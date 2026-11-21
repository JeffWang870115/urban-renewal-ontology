from pathlib import Path
# -*- coding: utf-8 -*-
"""扫描街道维度表：指标 19–26 各自到底有什么数据"""
import glob
import os
import warnings
from collections import OrderedDict

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
    print("\n=" * 30)
    print("文件：", os.path.basename(p), "| 行数", ws.max_row)
    cur = None
    groups = OrderedDict()
    for r in range(12, ws.max_row + 1):
        name = ws.cell(r, 2).value
        if name and str(name).strip():
            cur = str(name).strip()
            groups.setdefault(cur, {"range": [r, r], "rows": 0, "sample": []})
            groups[cur]["range"][0] = r
        if cur:
            groups[cur]["rows"] += 1
            groups[cur]["range"][1] = r
            if len(groups[cur]["sample"]) < 3:
                vals = [ws.cell(r, c).value for c in range(1, 8)]
                groups[cur]["sample"].append([("" if v is None else str(v).strip())[:26] for v in vals])
    for k, v in groups.items():
        print(f"  · {k[:34]:<34} 行 v[{v['range'][0]}-{v['range'][1]}] n={v['rows']}")
        if "老旧" in k or "公共活动" in k or "体育" in k:
            for s in v["sample"]:
                print("       ", s)
    wb.close()
