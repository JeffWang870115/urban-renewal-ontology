# -*- coding: utf-8 -*-
import json, os

results = "E:/中设数字/00-01-个人/02-学习/01-wordbuddy/2026_working_space/城市体检与更新本体研究/城市体检与更新调研计划/results"
files = [
    "行业标准与团体标准.json",
    "技术导则.json",
    "自然资源口配套政策.json",
    "国土空间规划城市体检评估规程_边界.json",
    "地方城市更新条例立法进展.json",
    "中央财政支持城市更新示范.json",
]

out = []
out.append("# 深度调研复核摘要（第3批，items 13–18）\n")
out.append("> 字段含义见 fields.yaml。每项列出：核心内容、关键引用、待核项。\n")

total_unc = 0
for fn in files:
    p = os.path.join(results, fn)
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        out.append(f"\n## ⚠️ {fn} 读取失败: {e}\n")
        continue
    name = d.get("名称", fn)
    cat = d.get("category", d.get("适用层级与范围", ""))
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
        # 引用可能过长，截断到前2条
        if isinstance(cite, list):
            cite_s = "；".join(cite[:2])
        else:
            cite_s = str(cite)[:600]
        out.append(f"- 关键引用（节选）：{cite_s}\n")
    if uncertain:
        out.append(f"- **待核项（{len(uncertain)}）**：{', '.join(uncertain)}\n")
    else:
        out.append(f"- 待核项：无\n")

out.append(f"\n---\n\n**待核项合计：{total_unc} 项**（均已在 JSON `uncertain` 数组标注，未编造）。\n")

out.append("\n## 边界与冲突提示（建模前需大王拍板）\n")
notes = [
    "1. **TD/T 1063-2021 指标数**：outline/前期复核写\"104项(33+89)\"有误——33+89=122；本批 agent 据标准附录标注 122 项(33基本+89推荐)。另：2025 年新版已印发施行、替代原版，但新标准号未公开→标【待核】。建模引用时按 122 项口径，注明新版待核。",
    "2. **国家层面\"城市体检评估技术导则(试行)\"**：经核验住建部未见权威公开发布；住建口城市体检统领文件实为 建科〔2023〕75号 及附件《城市体检基础指标体系(试行)》《城市体检工作手册(试行)》，地方多以\"城市体检技术导则/指南(试行)\"印发。勿把\"技术导则\"当作国家强制/指导文件名。",
    "3. **团体标准核验渠道**：std.samr.gov.cn 国标库对团标返回无数据；团标应在 全国团体标准信息平台(tcgb.org.cn) 核验。本批 T/CACP 0001-2025、T/CAIEC 125-2025 经协会公告+国家数字标准馆交叉核验现行。",
    "4. **自然资源口配套政策归口**：自然资办发〔2023〕47号、自然资发〔2025〕226号 归口自然资源部（226号为自然+住建联合），属更新土地/规划支撑，非住建口体检体系；本期仅作协同背景。",
    "5. **地方条例层级**：全国约27部（省级4+市级20余）；浙江《城镇社区更新条例》为全国首部社区更新省级法规(2025-07-01)；山西(2026-05-01)为最新省级。列名须标立法层级(省/市)。",
    "6. **中央财政示范文号**：财办建〔2024〕24号(首批15城)、财办建〔2025〕11号(第二批20城)、绩效评价 财办建〔2024〕46号；奖补分区域定额(东≤8亿/中≤10亿/西≤12亿/直辖≤12亿)，3年拨付。",
]
for n in notes:
    out.append(n + "\n")

with open(os.path.join(results, "_复核_第3批.md"), "w", encoding="utf-8") as fo:
    fo.write("\n".join(out))
print("OK, files:", len(files), "total_unc:", total_unc)
