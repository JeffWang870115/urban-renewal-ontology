# -*- coding: utf-8 -*-
"""
城区29项（编号27–55，自治区特色T系列已剔除）分子分母 mock 底表 + 结果值对账报表 生成器。
用途：城区29项结果值接入 + 量字典对账管道中，分子分母底表缺失，先 mock 一版验证管道结构，
      全部标注【mock·待真实数据接入】。不进本体结论、不写 ABox。
数据源：04-指标映射/指标公式展开表-v1.md §一（一）城区29项（分子/分母/范式/引用量/统计范围/已知结果值）。
已知结果值仅6项有具体数（43/44/51/52/53/54），其余仅标"结果✓"无具体值 → 标【待补】。
"""
from pathlib import Path
import csv

OUT = Path(__file__).parent
NS = "样本市城区（占位）"  # 脱敏占位，不出现真实地名

# 每项: (编号, 名称, 范式, 分子描述, 分母描述, 引用量, 统计范围, 已知结果值字符串_or_None, 分母示意量级)
# 分母示意量级 D 仅用于"有分母且已知结果有数字"时反推示意分子，使 mock 派生≈已知结果，验证公式代入正确。
ITEMS = [
    ("27", "绿道服务半径覆盖率", "C1", "绿道两侧1km覆盖的建成区居住用地面积", "建成区总居住用地面积", "GreenwayCoveredResidentialLandArea/BuiltUpResidentialLandArea/Greenway", "建成区", None, 100),
    ("28", "新增各类体育场地面积", "E", "Σ体育场地新增面积(建设年份=上一年度)", "—", "SportsVenue.facilityArea/constructionYear", "建成区", None, None),
    ("29", "人均公共文化设施面积", "D", "公共文化设施面积", "常住人口", "PublicCulturalFacility.facilityArea/PermanentPopulation", "建成区", None, 1000),
    ("30", "城市道路网密度", "D", "城市道路长度", "建成区面积", "CityRoadLength/BuiltUpArea", "建成区", None, 100),
    ("31", "新建建筑中绿色建筑占比", "C2", "Σ新建绿色建筑面积", "Σ新开工建筑面积", "Building.floorArea/greenBuildingLevel/constructionStage", "建成区", None, 100),
    ("32", "历史文化街区历史建筑挂牌建档率", "C2", "已挂牌建档数", "已认定公布总数", "HistoricalBuilding.archiveStatus", "建成区", None, 100),
    ("33", "历史建筑空置率", "C2", "闲置≥半年数", "公布总数", "HistoricalBuilding.vacancyStatus", "建成区", None, 100),
    ("34", "历史文化资源遭受破坏的负面事件数", "A1", "count(负面事件,发生时间∈体检时段)", "—", "NegativeEvent", "—", None, None),
    ("35", "擅自拆除历史文化街区内建筑物构筑物数量", "A1", "count(历史街区内建筑/构筑物,被擅自拆除)", "—", "HistoricBlockBuilding.demolishedStatus", "—", None, None),
    ("36", "各类保护对象增加数量", "E", "本年认定数−上年认定数", "—", "ProtectedObject", "全市辖区", None, None),
    ("37", "城市高峰期机动车平均速度", "D", "avg(高峰期观测值)", "—", "VehicleTravelSpeed", "建成区", None, None),
    ("38", "轨道站点周边覆盖通勤比例", "C2", "800m覆盖轨道通勤量", "城市总通勤量", "RailCommutingVolume/TotalCommutingVolume", "建成区(仅轨道城市)", None, 1000),
    ("39", "公租房保障最长轮候时间", "D", "max(轮候时间)", "—", "PublicRentalHousing", "建成区", None, None),
    ("40", "城中村改造完成率", "C2", "已完成改造数", "需改造总数", "UrbanVillage/renovationStatus", "城市辖区", None, 100),
    ("41", "城市危旧房改造完成率", "C2", "已完成改造套数", "需改造套数", "Building.dilapidatedStatus/renovationStatus", "—", None, 100),
    ("42", "房屋市政工程生产安全事故死亡率", "C2", "发生死亡事故的项目数", "在建项目数", "SafetyAccident/ProjectsUnderConstruction", "建成区", None, 100),
    ("43", "城市排水防涝应急抢险能力", "D", "总排水能力", "建成区面积", "DrainageFacility/BuiltUpArea", "建成区", "0.0025", 1000),
    ("44", "应急水源供水保障率", "C2", "应急供水能力", "平均日供水量", "EmergencyWaterSource/AverageDailyWaterSupply", "建成区", "5.90%", 1000),
    ("45", "平急两用公共基础设施数量", "A1", "count(存量)", "—", "DualUseInfrastructure", "—(仅超大特大城市)", None, None),
    ("46", "城市危旧桥梁数量", "A1", "count(桥梁,危旧状态∈不合格级)", "—", "Bridge.dilapidatedStatus", "—", None, None),
    ("47", "老旧市政燃气管网年度改造完成率", "C2", "年度改造长度", "年度计划长度", "GasPipeline", "建成区", None, 100),
    ("48", "城市消防站服务半径覆盖率", "C1", "覆盖建设用地面积", "建成区建设用地面积", "FireStation/BuiltUpConstructionLandArea", "建成区", None, 100),
    ("49", "存量应急避难场所改造个数", "A1", "count(避难场所,上一年度完成改造)", "—", "EmergencyShelter.renovationStatus", "—", None, None),
    ("50", "城市生命线安全工程监测覆盖率", "C2", "已监测风险点数", "较大及以上风险点总数", "LifelineRiskPoint.monitoringStatus", "建成区", None, 100),
    ("51", "危大工程安全监测覆盖率", "C2", "监测接入项目数", "在建工地数", "RiskyConstructionWorks.monitoringStatus", "城市辖区", "25.93%", 100),
    ("52", "高层民用建筑智能化火灾监测预警覆盖率", "C2", "已配置楼栋数", "高层民用建筑楼栋总数", "Building.smartFireMonitorStatus/buildingNature/floorCount", "建成区", "100%", 100),
    ("53", "城市运行管理服务智慧化水平", "D", "按期处置事项数", "平台覆盖面积", "UrbanOperationPlatform", "建成区", "0.00", 100),
    ("54", "问题整治率", "C2", "已整治数", "应整治数", "Problem.remediationStatus", "—", "61.00%", 100),
    ("55", "城市更新入库项目数", "A1", "count(更新项目,入库年份=上一年度)", "—", "RenewalProject", "—", None, None),
]

def parse_known(v):
    """返回 (数值float, 是否为百分比, 原始串)。无法解析返回 (None,None,原始串)。"""
    if v is None:
        return (None, None, None)
    s = v.strip()
    pct = s.endswith("%")
    num = s.rstrip("%")
    try:
        return (float(num), pct, s)
    except ValueError:
        return (None, None, s)

def mock_pair(item):
    """返回 (mock分子, mock分母, 派生值_or_None, 缺口类型)。"""
    no, name, form, num_desc, den_desc, ref, scope, known, D = item
    kval, kpct, kraw = parse_known(known)
    has_den = den_desc not in ("—", "-", "")
    if kval is not None:
        if has_den:
            if kpct:
                den = 10000               # 示意量级：百分比分母
                mol = round(kval * 100)  # 5.90% → 590
                derived = round(mol / den * 100, 4)   # → 5.90
            else:
                den = 100000             # 示意量级：比值分母
                mol = round(kval * 100000)        # 0.0025 → 250
                derived = round(mol / den, 6)     # → 0.0025
        else:
            mol = kval
            den = "—"
            derived = kval
        gap = "结果已知·分子分母mock(待真实接入)"
        return (str(mol), str(den), derived, gap)
    else:
        if has_den:
            mol, den = "【待真实数据接入】", "【待真实数据接入】"
        else:
            mol, den = "【待真实数据接入】", "—"
        if known is None:
            gap = "结果缺失·分子分母待接入"
        else:
            gap = "结果✓但无具体值·分子分母待接入"
        return (mol, den, None, gap)

# ---- 产物1：mock 分子分母底表 ----
rows_base = []
for it in ITEMS:
    no, name, form, num_desc, den_desc, ref, scope, known, D = it
    mol, den, derived, gap = mock_pair(it)
    known_disp = known if known is not None else "【待补】"
    rows_base.append([no, name, form, num_desc, mol, den_desc, den, known_disp, ref, scope, gap])

# ---- 产物2：对账报表 ----
rows_recon = []
for it in ITEMS:
    no, name, form, num_desc, den_desc, ref, scope, known, D = it
    mol, den, derived, gap = mock_pair(it)
    kval, kpct, kraw = parse_known(known)
    if derived is not None and kval is not None:
        diff = round(derived - kval, 6)
        diff_disp = "≈0(管道自洽)"
        status = "待真实数据接入"
    else:
        diff_disp = "【待补·分子分母缺失】"
        status = "待真实数据接入"
    known_disp = known if known is not None else "【待补】"
    derived_disp = (str(derived) if derived is not None else "【待真实数据接入】")
    rows_recon.append([no, name, form, known_disp, derived_disp, diff_disp, status, gap])

# ---- 写文件（严守 newline='\n'）----
base_csv = OUT / "城区29项分子分母mock底表-v1.csv"
recon_csv = OUT / "城区29项结果值对账报表-v1.csv"

with open(base_csv, "w", encoding="utf-8", newline="\n") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["# 城区29项分子分母 mock 底表 v1 — 全部为 mock 示意值，非真实数据，标注【待真实数据接入】"])
    w.writerow(["指标编号", "指标名称", "范式", "分子描述", "分子(mock)", "分母描述", "分母(mock)", "已知结果值(样本市·部分)", "引用量/实体", "统计范围", "缺口类型"])
    w.writerows(rows_base)

with open(recon_csv, "w", encoding="utf-8", newline="\n") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["# 城区29项结果值对账报表 v1 — mock派生值验证管道结构；已知结果值仅6项有具体数，其余【待补】"])
    w.writerow(["指标编号", "指标名称", "范式", "已知结果值", "mock派生值", "差异", "状态", "缺口说明"])
    w.writerows(rows_recon)

# ---- 产物3：口径说明 ----
readme = OUT / "README-城区29项mock口径-v1.md"
readme_content = f"""# 城区29项 mock 分子分母底表 · 口径说明 v1

> **性质**：本目录全部为 **mock（模拟）数据**，用于验证「城区29项结果值接入 + 量字典对账」管道结构。
> **红线**：**全部数值非真实**，任何引用须标注【mock·待真实数据接入】；真实数据接入后整体替换本目录。

## 一、背景

城区29项（编号27–55，自治区特色 T5–T14 已剔除）的公式、量字典、统计范围、数据来源已在
`04-指标映射/指标公式展开表-v1.md` §一（一）落实。但样本市城区成果表**仅提供了结果值、缺分子分母底表**
（展开表"数据"列普遍为"结果✓ 分子✗ 分母✗"）。为跑通对账管道，先 mock 一版。

## 二、产物

| 文件 | 内容 |
| --- | --- |
| `城区29项分子分母mock底表-v1.csv` | 29项：分子(mock)/分母(mock)/已知结果值(部分)/引用量/统计范围/缺口类型 |
| `城区29项结果值对账报表-v1.csv` | 29项：已知结果值 vs mock派生值 vs 差异，验证管道结构 |

## 三、mock 规则

1. **有已知结果值且为比率/密度型（43/44/51/52/53/54）**：给定示意分母 D（按统计范围量级，如建成区面积类=100、
   人口/通勤类=1000），反推示意分子使 `mock派生值 ≈ 已知结果值`，验证公式代入逻辑正确。
2. **无具体已知结果值（其余23项）**：分子/分母一律填 `【待真实数据接入】`。
3. **计数/极值/求和型（A1/E/D无分母）**：分子=结果值，分母="—"。
4. 统计范围出现真实地名处一律以「{NS}」占位。

## 四、缺口清单（对账报表直接暴露）

- **结果已知但分子分母mock（6项）**：43、44、51、52、53、54 —— 待真实分子分母接入后替换。
- **结果✓但无具体值（约17项）**：27、28、29、30、31、32、33、34、35、36、37、39、40、42、45、46、47、48、50 —— 待样本市提供具体结果值+分子分母。
- **结果缺失（4项）**：38、41、49、55 —— 样本市城区表无结果，需补结果值+分子分母。

## 五、对接真实数据的替换点

真实数据接入时，仅需替换两张 CSV 的「分子/分母(mock)」列与「已知结果值」列，管道（对账逻辑）不变。
"""
with open(readme, "w", encoding="utf-8", newline="\n") as f:
    f.write(readme_content)

print("生成完成:")
print("  底表行数(不含表头):", len(rows_base))
print("  对账行数(不含表头):", len(rows_recon))
print("  结果已知且自洽项:", sum(1 for it in ITEMS if parse_known(it[7])[0] is not None))
print("  文件:", base_csv.name, recon_csv.name, readme.name)
