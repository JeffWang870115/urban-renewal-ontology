# -*- coding: utf-8 -*-
import json, glob, os

results = "E:/中设数字/00-01-个人/02-学习/01-wordbuddy/2026_working_space/城市体检与更新本体研究/城市体检与更新调研计划/results"
files = sorted(glob.glob(results + "/*.json"))
out = []
out.append("# 深度调研复核摘要（第1–2批，items 1–12）\n")
out.append("> 字段含义见 fields.yaml。每项列出：核心内容、关键引用、待核项。\n")

total_unc = 0
for f in files:
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        out.append(f"\n## (E) {os.path.basename(f)} 读取失败: {e}\n")
        continue
    name = d.get("名称", os.path.basename(f))
    cat = d.get("category", d.get("适用层级与范围", ""))
    note = d.get("备注", "")
    core = d.get("核心内容", "")
    cite = d.get("引用来源", "")
    uncertain = d.get("uncertain", [])
    total_unc += len(uncertain)
    out.append(f"\n## {name}\n")
    if cat:
        out.append(f"- 类别/范围：{cat}\n")
    if core:
        out.append(f"- 核心内容：{core}\n")
    if cite:
        out.append(f"- 关键引用：{cite}\n")
    if uncertain:
        out.append(f"- **待核项（{len(uncertain)}）**：{', '.join(uncertain)}\n")
    else:
        out.append(f"- 待核项：无\n")
    if note:
        out.append(f"- 备注：{note}\n")

out.append(f"\n---\n\n**待核项合计：{total_unc} 项**（均已在 JSON `uncertain` 数组标注，未编造）。\n")

with open(results + "/_复核_前12批.md", "w", encoding="utf-8") as fo:
    fo.write("\n".join(out))
print("OK files:", len(files), "total_unc:", total_unc)
