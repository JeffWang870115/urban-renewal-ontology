# -*- coding: utf-8 -*-
"""55 项录入模板 vs 本体（类与层级 §2.8 / 属性与关系）机械校验。
校验：序号连续性、维度∈五级、measures(=采集层级) 匹配、数据对象名∈本体类集合、多对象必带 formula。
只读，不写任何文件。"""
import re, json, os

BASE = r"E:\中设数字\00-01-个人\02-学习\01-wordbuddy\2026_working_space\城市体检与更新本体研究"
TMPL = os.path.join(BASE, "04-指标映射", "55项基础指标_录入模板.md")
CLS = os.path.join(BASE, "03-本体模型", "类与层级.md")
PROPS = os.path.join(BASE, "03-本体模型", "属性与关系.md")

LV = ["住房", "小区", "社区", "街区", "城区"]

# ---- 1. 已知类/实体名集合（从 类与层级.md + 属性与关系.md 反引号名提取）----
known = set()
for p in (CLS, PROPS):
    t = open(p, encoding="utf-8").read()
    # 反引号内的大驼峰名（含点路径的分段）
    for m in re.findall(r"`([A-Za-z][A-Za-z0-9_.]*)`", t):
        for seg in m.split("."):
            if seg and seg[0].isupper():
                known.add(seg)
# 主干 14 类兜底
known |= {"SpatialUnit", "Dimension", "Indicator", "DataObject", "ExaminationActivity",
          "AssessmentResult", "Problem", "RenewalObject", "RenewalProject", "RenewalApproach",
          "Actor", "Fund", "PolicyStandard", "TimePeriod"}

# ---- 2. 解析录入模板 §三 表格 ----
seen = {}
for line in open(TMPL, encoding="utf-8"):
    s = line.strip()
    if not s.startswith("|"):
        continue
    cells = [c.strip() for c in s.strip("|").split("|")]
    if len(cells) < 15:
        continue
    if not re.fullmatch(r"\d{1,2}", cells[0]):
        continue
    seq = int(cells[0])
    if 1 <= seq <= 55:
        seen[seq] = cells

rows = [seen[i] for i in sorted(seen)]
nums = sorted(seen)
gap = [i for i in range(1, 56) if i not in nums]

issues = {"dim_invalid": [], "level_mismatch": [], "missing_class": [], "multi_no_formula": [], "seq_gap": []}
obj_stat = []      # (seq, [names], 反引号原始)
multi_rows = []    # 多对象行
coverage_rows = [] # 覆盖率/比值类

for c in rows:
    seq = int(c[0]); name = c[2]; dim = c[3]; method = c[7]; dobj = c[8]; level = c[10]
    if dim not in LV:
        issues["dim_invalid"].append([seq, dim])
    if level != dim:
        issues["level_mismatch"].append([seq, dim, level])
    # 数据对象名（反引号内、首字母大写段）
    names_raw = re.findall(r"`([A-Za-z][A-Za-z0-9_.]*)`", dobj)
    names = []
    for n in names_raw:
        segs = [s for s in n.split(".") if s and s[0].isupper()]
        if not segs:
            continue
        names.append(n)
        for s in segs:
            if s not in known:
                issues["missing_class"].append([seq, s, dobj])
    obj_stat.append([seq, name, dim, level, names])
    multi = ("①" in dobj) or ("②" in dobj) or (len(names) >= 2)
    if multi:
        multi_rows.append(seq)
        if not method:
            issues["multi_no_formula"].append([seq, dobj])
    if ("%" in c[4]) or ("覆盖" in dobj) or ("率" in name) or ("密度" in name):
        coverage_rows.append(seq)

if gap:
    issues["seq_gap"] = gap

# 维度分布
dist = {}
for c in rows:
    dist[c[3]] = dist.get(c[3], 0) + 1

out = {
    "录入行数": len(rows), "序号范围": [min(nums), max(nums)], "断号": gap,
    "维度分布": dist,
    "本体已知类名数": len(known),
    "多对象行数": len(multi_rows), "多对象序号": multi_rows,
    "问题": {k: v for k, v in issues.items() if v},
}
print(json.dumps(out, ensure_ascii=False, indent=1))
