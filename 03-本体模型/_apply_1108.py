# -*- coding: utf-8 -*-
"""W-C01 批注落地：属性与关系.md
1) 对象属性表插入 assesses 并重排该表
2) 新增 §2.2 实例数据接入属性（29 个数据属性）
3) §四 追加 assesses / 聚合校验 约束
4) §五 追加风险条目
"""
from pathlib import Path
import unicodedata, os, shutil

D = Path(__file__).resolve().parent
P = str(D / "属性与关系.md")
BAK = D / "_bak_20261108"
BAK.mkdir(exist_ok=True)
shutil.copy2(P, str(BAK / "属性与关系.md.bak1"))
print("backup ok")


def w(s):
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)


def pad(s, n):
    return s + " " * max(0, n - w(s))


def is_sep(r):
    return all(set(c) <= set("-: ") for c in r)


def render(rows):
    ncol = max(len(r) for r in rows)
    widths = [0] * ncol
    for r in rows:
        if is_sep(r):
            continue
        for j, c in enumerate(r):
            widths[j] = max(widths[j], w(c))
    out = []
    for r in rows:
        if is_sep(r):
            out.append("|" + "|".join("-" * (widths[j] + 2) for j in range(len(r))) + "|")
        else:
            out.append("|" + "|".join(" " + pad(c, widths[j]) + " " for j, c in enumerate(r)) + "|")
    return out


txt = open(P, encoding="utf-8", newline="").read().replace("\r\n", "\n")
lines = txt.split("\n")

# ---------- 1) 对象属性表：插入 assesses ----------
start = None
for i, l in enumerate(lines):
    if l.startswith("| 关系"):
        start = i
        break
assert start is not None, "未找到对象属性表"
end = start
while end < len(lines) and lines[end].startswith("|"):
    end += 1
rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in lines[start:end]]
assert not any(r[2] == "`assesses`" for r in rows if len(r) > 2), "assesses 已存在"

NEW = [
    "评估",
    "is assessed on",
    "`assesses`",
    "AssessmentResult → SpatialUnit",
    "**2026-11-08 新增（W-C01）**：评估结果**落在哪个空间单元**，基数 1..1。与 `measures`（指标数的是什么）、`computedFrom`（由什么算出）**三线正交**，互不替代——住房 8 项即「`measures` = 楼栋、`assesses` = 小区」的典型",
    "建模稿（本轮新增）",
]
idx = next(i for i, r in enumerate(rows) if len(r) > 2 and r[2] == "`produces`")
rows.insert(idx + 1, NEW)
lines[start:end] = render(rows)
print("assesses inserted at row", idx + 2)

txt = "\n".join(lines)

# ---------- 2) 新增 §2.2 ----------
DATA = [
    ("面积（平方千米）", "`areaKm2`", "`SpatialUnit`", "decimal", "街区 r4、社区 r4"),
    ("常住人口", "`residentPopulation`", "`SpatialUnit`", "integer", "街区 r6、社区 r6、小区 r9、楼栋台账"),
    ("户数", "`householdCount`", "`SpatialUnit`", "integer", "街区 r7、社区 r7"),
    ("单元数量", "`unitCount`", "`Building`", "integer", "楼栋台账「单元数量（个）」"),
    ("老年人口", "`elderlyPopulation`", "`SpatialUnit`", "integer", "楼栋台账「六十岁以上常住人口」、小区 r10"),
    ("小区类型", "`rqType`", "`ResidentialQuarter`", "string", "住房 r3"),
    ("建筑数量", "`buildingCount`", "`ResidentialQuarter`", "integer", "住房 r6"),
    ("总建筑面积", "`totalFloorArea`", "`ResidentialQuarter`", "decimal", "住房 r7"),
    ("住宅套数", "`housingUnitCount`", "`ResidentialQuarter`", "integer", "住房 r8"),
    ("停车位需求", "`parkingDemand`", "`ResidentialQuarter` + `Community`", "integer", "住房 r16、社区 r13"),
    ("停车位供给", "`parkingSupply`", "`ResidentialQuarter` + `Community`", "integer", "住房 r17、社区 r14"),
    ("充电桩需求", "`evChargerDemand`", "`ResidentialQuarter`", "integer", "住房 r21"),
    ("充电桩供给", "`evChargerSupply`", "`ResidentialQuarter`", "integer", "住房 r22"),
    ("配建电动自行车设施", "`ebikeFacilityBuilt`", "`ResidentialQuarter`", "boolean", "住房 r25"),
    ("电动自行车设施数量", "`ebikeFacilityCount`", "`ResidentialQuarter`", "integer", "住房 r27"),
    ("配建公共活动场地", "`publicVenueBuilt`", "`ResidentialQuarter`", "boolean", "住房 r30"),
    ("公共活动场地面积", "`publicVenueArea`", "`ResidentialQuarter`", "decimal", "住房 r31"),
    ("配建公共绿地", "`publicGreenBuilt`", "`ResidentialQuarter`", "boolean", "住房 r32"),
    ("公共绿地面积", "`publicGreenArea`", "`ResidentialQuarter`", "decimal", "住房 r33"),
    ("不达标步行道长度", "`nonCompliantWalkwayLength`", "`ResidentialQuarter`", "decimal", "住房 r36"),
    ("垃圾分类点数量", "`wasteSortingStationCount`", "`ResidentialQuarter`", "integer", "住房 r40"),
    ("智能信包箱", "`smartParcelLocker`", "`ResidentialQuarter`", "boolean", "住房 r47"),
    ("智能安防", "`smartSecurity`", "`ResidentialQuarter`", "boolean", "住房 r48"),
    ("小区数量", "`rqCount`", "`Community`", "integer", "社区 r5"),
    ("小汽车拥有量", "`carOwnership`", "`Community`", "integer", "社区 r9"),
    ("新能源汽车数量", "`evCount`", "`Community`", "integer", "社区 r10"),
    ("社区数量", "`communityCount`", "`Neighborhood`", "integer", "街区 r5"),
    ("企业数量", "`enterpriseCount`", "`Neighborhood`", "integer", "街区 r8"),
    ("就业人数", "`employmentCount`", "`Neighborhood`", "integer", "街区 r9"),
]
assert len(DATA) == 29, len(DATA)

trows = [["属性", "URI 名", "适用类", "值域", "来源字段"]]
trows.append(["-", "-", "-", "-", "-"])
for a, b, c, d, e in DATA:
    trows.append([a, b, c, d, e])

SEC = [
    "",
    "### 2.2 实例数据接入属性（2026-11-08，随 W-C01 数据契约）",
    "",
    "> **来源**：`06-实例数据/待补属性清单-v1.md` 大王批注（2026-11-08）——原列 57 项，**保留 29 个数据属性**、删除 27 项；另新增 1 个对象属性 `assesses`（见 §一）。",
    "> **口径**：`SpatialUnit` 者为**五级子类共性属性**（街区/社区/小区/楼栋共用）；`parkingDemand` / `parkingSupply` 在小区与社区**共用同一属性**（两处同义字段，不重复建）。",
    "> **不属于本表**：`constructionYear`（建成年代）、`renovationStatus`（改造完成状态）为**既有属性扩定义域**（均追加 `ResidentialQuarter`），见 §2.1。",
    "",
] + render(trows) + [
    "",
    "**与指标的消费关系**（20 个属性直接支撑住房/小区维度指标）：",
    "",
    "- 指标 11（停车缺口）← `parkingDemand` / `parkingSupply`；指标 12（充电桩缺口）← `evChargerDemand` / `evChargerSupply`",
    "- 指标 13（未配建电动自行车设施）← `ebikeFacilityBuilt`；指标 15（不达标步行道）← `nonCompliantWalkwayLength`",
    "- 指标 14（公共活动场地未达标）← `publicVenueBuilt` / `publicVenueArea` / `publicGreenBuilt` / `publicGreenArea`（场地与绿地**可统筹衡量**）",
    "- 指标 18（需智慧化改造）← `smartParcelLocker` / `smartSecurity`（与既有 `smartRetrofitNeed` 并存）",
    "- 一致性校验用：`buildingCount` / `totalFloorArea` / `housingUnitCount` / `rqCount` / `communityCount`",
    "- 背景信息（当前无指标消费，按大王批注保留）：`carOwnership` / `evCount` / `employmentCount`",
    "",
    "> ⚠️ **`unitCount` ≠ `housingUnitCount`**：单元数量与住宅套数不是同一量，源数据楼栋台账仅有「单元数量」，套数加和只能近似【待核】。",
    "",
]
anchor = "## 三、借鉴同事成果新增的属性与约束"
assert anchor in txt
txt = txt.replace(anchor, "\n".join(SEC) + anchor, 1)

# ---------- 3) §四 追加约束 ----------
CONS = [
    "- [x] `assesses` **基数（2026-11-08 新增）**：每条 `AssessmentResult` **恰 1 个**空间单元（`sh:minCount 1` / `sh:maxCount 1`）。与 `measures` 分工：`measures` 说「数的是什么」（如楼栋），`assesses` 说「这条值属于哪个单元」（如小区）。",
    "- [x] `residentPopulation` / `householdCount` / `areaKm2` **非负**：`sh:minInclusive 0`；面积单位统一平方千米。",
    "- [x] **面积偏序（2026-11-08 大王批注，`sh:sparql`）**：`Neighborhood.areaKm2` ≥ **每一个**下辖 `Community.areaKm2`。这是**偏序而非加和**——街区面积不等于社区面积之和（含道路、绿地等未纳入社区面积的部分）。社区与小区之间同理，但小区表无面积字段，本期**不可校**。",
    "- [x] **人口加和（2026-11-08 大王批注，`sh:sparql`）**：`Neighborhood.residentPopulation` = Σ 下辖 `Community.residentPopulation`；`Community.residentPopulation` = Σ 下辖 `ResidentialQuarter.residentPopulation`。户数同理，但小区表无户数字段，社区级**不可校**。",
    "- [x] **设施计数一致（`sh:sparql`）**：`ResidentialQuarter.buildingCount` = `count(下辖 Building)`；`Community.rqCount` = `count(下辖 ResidentialQuarter)`；`Neighborhood.communityCount` = `count(下辖 Community)`。",
    "- [x] **本表不承载的校验**：`totalFloorArea` = Σ 楼栋 `floorArea`、`housingUnitCount` = Σ 楼栋套数——因源数据无楼栋面积/套数字段，**本期只登记规则、不实际校验**（见 `数据契约-v1.md` §七 Q15/Q16）。",
    "",
]
anchor2 = "## 五、已知风险"
assert anchor2 in txt
txt = txt.replace(anchor2, "\n".join(CONS) + anchor2, 1)

# ---------- 4) §五 追加风险 ----------
RISK = [
    "- **实例数据接入的属性范围已收敛（2026-11-08 大王批注）**：原列 57 项，**保留 30 项**（1 对象属性 + 29 数据属性）、**删除 27 项**。「删除」不等于「源数据丢弃」——源表完整存于 `01-资料/`，可按原行号回填。删除理由分五类：可派生 / 自由文本 / 自治区特色（T 系列）/ 2026 已删指标 / 无指标消费。",
    "- **`assesses` 是接实例数据后最先撞到的缺口（2026-11-08 补）**：`measures` 只回答「数的是什么」，不回答「这条值算在哪个单元」。住房 8 项 `measures = Building` 但值挂小区，若无 `assesses` 则指标值无处安放、无法上卷。",
    "- **聚合类约束无法用 `sh:property` 表达（2026-11-08 补）**：面积偏序、三级人口加和、设施计数一致均需 `sh:sparql` 形状；且其中 4 项因源数据缺字段（小区面积 / 小区户数 / 楼栋面积 / 楼栋套数）**本期只能登记、无法校验**——不得以造数方式掩盖。",
    "- **`publicVenueBuilt`（布尔）与 `PublicActivityVenue`（实体）并存（2026-11-08 补）**：前者是**小区级填报口径**（有/无 + 面积），后者是**可追溯的设施实例**（面积/配套/所属单元）。指标 14 判「社区数量」，需要逐场地证据时须落到实体；仅凭布尔只能判「有无」，判不了「面积是否达标、场地与绿地能否统筹」。二者**不可互替**，接入时按可得证据择一，并在 `Problem.problemDescription` 写明依据。",
]
txt = txt.rstrip("\n") + "\n" + "\n".join(RISK) + "\n"

open(P, "w", encoding="utf-8", newline="\n").write(txt)
print("OK, bytes=", len(txt.encode("utf-8")))
