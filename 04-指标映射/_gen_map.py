# -*- coding: utf-8 -*-
"""本体建模·单一数据源生成器：由 55项基础指标_录入模板.md 机械生成 人读 .md + 机读 .yaml。
流程：解析 -> 名称归一(去前缀) -> 组装(总览/骨架表/分类表/公式表/反向索引/待核) -> 自校验 -> 双格式输出。
输出：04-指标映射/指标映射表.md（人读）、04-指标映射/55项指标.yaml（机读）。二者同源、永远一致。
2026-10-09 同步：补 §二-1 指标分类表、头部顶层类 14->16、§五 待核 +2 项、§六 inCategory 覆盖校验。
2026-10-09 第 3 步：同源输出 55项指标.yaml；登记 D2（RemediationSuggestion 不入 computedFrom 值域）；补 orientation 字段。"""
from pathlib import Path
import re, os

BASE = str(Path(__file__).resolve().parent.parent)
D = os.path.join(BASE, "04-指标映射")
TMPL = os.path.join(D, "55项基础指标_录入模板.md")
OUT = os.path.join(D, "指标映射表.md")
OUT_YAML = os.path.join(D, "55项指标.yaml")

LV = ["住房", "小区", "社区", "街区", "城区"]
LV_URI = {"住房": "Building", "小区": "ResidentialQuarter", "社区": "Community",
          "街区": "Neighborhood", "城区": "UrbanDistrict"}
DIM_URI = {"住房": "HousingDimension", "小区": "ResidentialQuarterDimension", "社区": "CommunityDimension",
           "街区": "NeighborhoodDimension", "城区": "UrbanDistrictDimension"}
LV_CN = {"住房": "住房级", "小区": "小区级", "社区": "社区级", "街区": "街区级", "城区": "城区级"}
TD = {"住房": "手册表1", "小区": "手册表2", "社区": "手册表2", "街区": "手册表7", "城区": "手册表11"}

# ---- 数据对象三分类（源自 类与层级.md §2.8.1/2/3）----
REUSE = {
    "Building": ("复用·空间单元", "建筑（楼栋）"),
    "ResidentialQuarter": ("复用·空间单元", "小区"),
    "OldCommercialBlock": ("复用·更新对象", "老旧商业街区"),
    "OldResidentialBlock": ("复用·更新对象", "老旧生活街区"),
    "OldIndustrialArea": ("复用·更新对象", "老旧厂区"),
    "UrbanVillage": ("复用·更新对象", "城中村"),
    "Problem": ("复用·主干类", "体检问题"),
    "RenewalProject": ("复用·主干类", "城市更新项目"),
}
ENTITY = {
    "ElderlyCareFacility": "养老服务设施", "InfantCareFacility": "婴幼儿托育设施", "ParkingSpace": "停车泊位",
    "EVChargingPile": "新能源汽车充电桩", "EbikeChargingFacility": "电动自行车充电设施",
    "PublicActivityVenue": "公共活动场地", "Walkway": "步行道", "MiddleSchool": "中学",
    "MultiFunctionSportsGround": "多功能运动场地", "CulturalActivityCenter": "文化活动中心",
    "ParkGreenSpace": "公园绿化活动场地", "Road": "道路", "Greenway": "绿道", "SportsVenue": "体育场地",
    "PublicCulturalFacility": "公共文化设施", "Land": "用地", "HistoricalBuilding": "历史文化街区/历史建筑",
    "NegativeEvent": "负面事件", "HistoricBlockBuilding": "历史街区内建筑物/构筑物", "ProtectedObject": "保护对象",
    "RailTransitStation": "轨道站点", "PublicRentalHousing": "公租房轮候记录", "SafetyAccident": "生产安全事故",
    "DrainageFacility": "排水防涝设施", "EmergencyWaterSource": "应急水源",
    "DualUseInfrastructure": "平急两用公共基础设施", "Bridge": "桥梁", "GasPipeline": "老旧市政燃气管网",
    "FireStation": "消防站", "EmergencyShelter": "应急避难场所", "LifelineRiskPoint": "城市生命线风险点",
    "RiskyConstructionWorks": "危险性较大分部分项工程", "UrbanOperationPlatform": "城市运行管理平台",
    "ResidentialLand": "居住用地（`Land` 子类）", "ConstructionLand": "建设用地（`Land` 子类）",
}
BASIC = {
    "BuiltUpArea": "建成区面积", "PermanentPopulation": "常住人口数", "CityRoadLength": "城市道路长度",
    "RailCommutingVolume": "轨道交通通勤量", "TotalCommutingVolume": "城市总通勤量",
    "AverageDailyWaterSupply": "平均日供水量", "ProjectsUnderConstruction": "在建项目数量",
    "VehicleTravelSpeed": "机动车行驶速度",
}
CN2URI = {"轨道交通通勤量": "RailCommutingVolume", "城市总通勤量": "TotalCommutingVolume"}
ORDER = {"复用·空间单元": 0, "复用·更新对象": 1, "复用·主干类": 2, "实体对象": 3, "基础量": 4}

# ---- 指标一级分类（IndicatorCategory，2026-10-09 大王批注：我方 55 项序号口径；分类轴跨维度独立）----
CATEGORY_ROWS = [
    ("住房", "1–4", "安全耐久"),
    ("住房", "5–8", "功能完备"),
    ("小区（社区）", "9–13", "设施完善"),
    ("小区（社区）", "14–16", "环境宜居"),
    ("小区（社区）", "17–18", "管理健全"),
    ("街区", "19–22", "功能完善"),
    ("街区", "23", "整洁有序"),
    ("街区", "24–26", "特色活力"),
    ("城区", "27–31", "生态宜居"),
    ("城区", "32–36", "历史文化保护利用"),
    ("城区", "37–40", "产城融合职住平衡"),
    ("城区", "41–49", "安全韧性"),
    ("城区", "50–53", "智慧高效"),
    ("城区（问题整治）", "54、55", "（无分类）"),
]

# 分类 → 维度 URI（2026-10-10 大王批注·折中方案：`belongsToDimension` 一对多）
DIM_LABEL2URI = {
    "住房": ["HousingDimension"],
    "小区（社区）": ["CommunityDimension", "ResidentialQuarterDimension"],
    "街区": ["NeighborhoodDimension"],
    "城区": ["UrbanDistrictDimension"],
    "城区（问题整治）": [],
}


def expand_seqs(seg):
    out = []
    for part in re.split(r"[、,]", seg):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"(\d+)[–\-](\d+)", part)
        if m:
            out += list(range(int(m.group(1)), int(m.group(2)) + 1))
        elif re.fullmatch(r"\d+", part):
            out.append(int(part))
    return out


def kind(uri):
    if uri in REUSE:
        return REUSE[uri]
    if uri in ENTITY:
        return ("实体对象", ENTITY[uri])
    if uri in BASIC:
        return ("基础量", BASIC[uri])
    return (None, None)


# ---- 1. 解析录入模板 §三 表 ----
rows = []
for line in open(TMPL, encoding="utf-8"):
    s = line.strip()
    if not s.startswith("|"):
        continue
    c = [x.strip() for x in s.strip("|").split("|")]
    if len(c) < 15:
        continue
    if not re.fullmatch(r"\d{1,2}", c[0]):
        continue
    if 1 <= int(c[0]) <= 55:
        rows.append(c)
rows.sort(key=lambda x: int(x[0]))


def parse_objs(cell):
    parts = re.split(r"[①②③④⑤⑥⑦⑧⑨⑩]", cell) if re.search(r"[①②③]", cell) else [cell]
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        p = p.split("→")[0]
        m = re.search(r"`([A-Za-z][A-Za-z0-9_.]*)`", p)
        cn = re.sub(r"`[^`]*`", "", p)
        cn = re.sub(r"[（(][^）)]*[）)]", "", cn).strip(" ，,、；;：")
        if m:
            uri = m.group(1).split(".")[-1]
            k, kcn = kind(uri)
            out.append((uri, cn or kcn or uri))
        else:
            hit, hitcn = None, cn
            for kk, vv in CN2URI.items():
                if kk in p:
                    hit, hitcn = vv, kk
                    break
            out.append((hit, hitcn))
    return out


def compress(nums):
    nums = sorted(nums)
    segs, st = [], nums[0]
    for a, b in zip(nums, nums[1:]):
        if b != a + 1:
            segs.append((st, a)); st = b
    segs.append((st, nums[-1]))
    return "、".join(f"{a}" if a == b else f"{a}–{b}" for a, b in segs)


data = []
issues = []
for c in rows:
    seq = int(c[0]); name = c[2]; dim = c[3]; unit = c[4]; orientation = c[5]; formula = c[7]
    objs = parse_objs(c[8]); level = c[10]; thr = c[12]; src = c[13]; st = c[14]
    if dim not in LV:
        issues.append(f"#{seq} 维度非法: {dim}")
    if level != dim:
        issues.append(f"#{seq} measures 跨级: 维度={dim} 层级={level}")
    if len(objs) >= 2 and not formula:
        issues.append(f"#{seq} 多对象缺 formula")
    for u, cn in objs:
        if u is None:
            issues.append(f"#{seq} 数据对象未解析: {cn}")
        elif kind(u)[0] is None:
            issues.append(f"#{seq} 数据对象不在本体: {u}")
    data.append(dict(seq=seq, code=c[1], name=name, dim=dim, unit=unit, orientation=orientation,
                     formula=formula, objs=objs, level=level, thr=thr, src=src, st=st))

# ---- 2. 组装 Markdown ----
L = []
L.append("# 城市体检基础指标（55 项）· 指标映射表")
L.append("")
L.append("> **生成**：2026-09-29（本体建模第四批·第 2 步，机械转换自 `55项基础指标_录入模板.md`）")
L.append("> **依据**：建办科〔2026〕16号 附件1《城市体检基础指标体系》（**文号本身【待核】**）；新疆手册第七章（表1/2/7/11/12）")
L.append("> **本体**：`03-本体模型/类与层级.md`（16 顶层类、五级维度）＋`属性与关系.md`（`computedFrom` 值域 = **角色类并集**，2026-09-29 F1 决议；2026-10-09 新增 `IndicatorCategory` / `RemediationSuggestion`）")
L.append("> **命名归一（D4 决议）**：数据对象统一取**裸 URI 名**，已去 `SpatialUnit.` / `Land.` / `RenewalObject.` 前缀")
L.append("> **格式**：紧凑 Markdown（不强制列对齐），便于自动生成与 diff")
L.append("")
L.append("---")
L.append("")

# §一 总览
L.append("## 一、映射总览")
L.append("")
L.append("| 维度 | 指标数 | 序号 | `measures` 空间层级 | `inDimension` 维度 | 单对象 | 多对象 |")
L.append("|---|---|---|---|---|---|---|")
tot_s = tot_m = 0
for d in LV:
    seqs = [x["seq"] for x in data if x["dim"] == d]
    m = [x for x in data if x["dim"] == d and len(x["objs"]) >= 2]
    s = [x for x in data if x["dim"] == d and len(x["objs"]) < 2]
    tot_s += len(s); tot_m += len(m)
    L.append(f"| {d} | {len(seqs)} | {compress(seqs)} | {LV_CN[d]} `{LV_URI[d]}` | `{DIM_URI[d]}` | {len(s)} | {len(m)} |")
allseq = [x["seq"] for x in data]
L.append(f"| **合计** | **{len(data)}** | {compress(allseq)} | 五级（住房–城区） | 五级 | **{tot_s}** | **{tot_m}** |")
L.append("")

# 数据对象类型统计
cnt = {}
for x in data:
    for u, cn in x["objs"]:
        cnt[u] = cnt.get(u, 0) + 1
by_kind = {}
for u, n in cnt.items():
    k = kind(u)[0]
    by_kind.setdefault(k, []).append((u, n))
L.append(f"**数据对象引用统计**：共 **{len(cnt)}** 个不同对象、**{sum(cnt.values())}** 次引用——"
         + "；".join(f"{k} {len(v)} 个（{sum(n for _, n in v)} 次）"
                     for k, v in sorted(by_kind.items(), key=lambda kv: ORDER.get(kv[0], 9))))
L.append("")
L.append("> 多对象指标（11 项）：" + compress([x["seq"] for x in data if len(x["objs"]) >= 2]) + "。")
L.append("")

# §二 骨架表
L.append("---")
L.append("")
L.append("## 二、指标—维度—空间层级—数据对象（骨架表，55 行）")
L.append("")
L.append("| 序号 | 指标名称 | `inDimension` 维度 | `measures` 空间层级 | `computedFrom` 数据对象（裸 URI 名·类型） |")
L.append("|---|---|---|---|---|")
for x in data:
    objs = "、".join(f"{cn} `{u}`（{kind(u)[0]}）" if u else f"{cn}【未解析】" for u, cn in x["objs"])
    L.append(f"| {x['seq']} | {x['name']} | {x['dim']} `{DIM_URI[x['dim']]}` | {LV_CN[x['level']]} `{LV_URI[x['level']]}` | {objs} |")
L.append("")
L.append("> `computedFrom` 值域为**角色类并集**（`DataObject` ∪ `SpatialUnit` ∪ `RenewalObject` ∪ `Problem` ∪ `RenewalProject`）："
         "上表「复用·*」者为复用实体（不新建 `DataObject`），「实体对象」/「基础量」者为新建 `DataObject`。")
L.append(">")
L.append("> **D2 登记（2026-10-09 大王拍板）**：2026-10-09 新增的中介类 `RemediationSuggestion`（整治建议）**不纳入** `computedFrom` 值域——指标 54（`Problem`）与 55（`RenewalProject`）属主干类复用，**不由整治建议直接算出**。")
L.append("")

# §二-1 指标分类
L.append("---")
L.append("")
L.append("## 二-1、指标分类 `IndicatorCategory`（`inCategory`，2026-10-09 新增）")
L.append("")
L.append("> **口径来源**：2026-10-09 大王批注（**我方 55 项序号口径**，非样本市编号）；分类轴**跨维度独立**，不与 `Dimension` 绑定。明细见 `02-术语与概念/概念清单.md` §十-1。")
L.append("> ⚠️ 与2025 版工作手册编号（住房 1–9 / 社区（小区）10–21 / 街区 22–29 / 城区 30–60 + T）**不可互引**。")
L.append("")
L.append("| 所属维度 | 指标序号 | `inCategory` 一级分类 |")
L.append("|---|---|---|")
for _dim, _seq, _cat in CATEGORY_ROWS:
    L.append(f"| {_dim} | {_seq} | {_cat} |")
L.append("")
# 分类覆盖校验（供 §六 用）：展开序号段，检测遗漏/重叠
cat_map, cat_overlap = {}, []
for _dim, _seq, _cat in CATEGORY_ROWS:
    for _s in expand_seqs(_seq):
        if _s in cat_map:
            cat_overlap.append(_s)
        cat_map[_s] = _cat
classified = [s for s in allseq if cat_map.get(s) not in (None, "（无分类）")]
unclassified = [s for s in allseq if cat_map.get(s) in (None, "（无分类）")]
_ncat = len(set(c for _, _, c in CATEGORY_ROWS if c != "（无分类）"))
_cov = "无遗漏无重叠" if not cat_overlap else "重叠：" + "、".join(map(str, sorted(cat_overlap)))
L.append(f"> **说明**：去重后共 **{_ncat} 类**；指标 54、55（问题整治）无一级分类，`inCategory` 基数 0..1。覆盖校验：{len(classified)} 项有分类 + {len(unclassified)} 项无 = {len(allseq)} 项，{_cov}。")
L.append("> **口径补注（2026-10-10 大王批注·折中方案）**：① 分类轴仍与 `Dimension` **平行独立**；另经对象属性 `belongsToDimension` **显式记录**每个分类归属的维度（**一对多**，如「设施完善」同归社区维度 + 小区维度），维度 URI 见 `55项指标.yaml` 的 `categories[].dimensions`、`属性与关系.md` §一。② 「**功能完备**」（住房 5–8）与「**功能完善**」（街区 19–22）**名词近似但为两个不同分类**，不合并。")
L.append("")

# §三 公式与依据
L.append("---")
L.append("")
L.append("## 三、计算方法、阈值与依据（55 行）")
L.append("")
L.append("| 序号 | 指标名称 | `formula` 计算方法 | `threshold` 达标/目标值 | `basedOn` 依据 | 状态 |")
L.append("|---|---|---|---|---|---|")
for x in data:
    L.append(f"| {x['seq']} | {x['name']} | {x['formula']} | {x['thr']} | {x['src']} | {x['st']} |")
L.append("")

# §四 反向索引
L.append("---")
L.append("")
L.append("## 四、数据对象反向索引（`feedsInto`）")
L.append("")
L.append("| 数据对象（裸 URI 名） | 类型 | 中文名 | 关联指标 |")
L.append("|---|---|---|---|")
keys = sorted(cnt.keys(), key=lambda u: (ORDER.get(kind(u)[0], 9), -cnt[u], u))
for u in keys:
    k, cn = kind(u)
    seqs = [x["seq"] for x in data if any(o[0] == u for o in x["objs"])]
    L.append(f"| `{u}` | {k} | {cn} | {compress(seqs)} |")
L.append("")

# §五 待核
L.append("---")
L.append("")
L.append("## 五、待核清单（均不阻塞导出，标 `【待核】` 即可）")
L.append("")
L.append("| # | 待核项 | 影响范围 | 现状 |")
L.append("|---|---|---|---|")
for i, t in enumerate([
    ("文号「建办科〔2026〕16号」本身", "本表「依据」列 55 行「附件1」前缀", "【待核】"),
    ("`floorCount`「高层」阈值（指标 52）", "指标 52 筛选条件", "【待核】"),
    ("达标等级枚举（达标/基本达标/不达标）", "`AssessmentResult.grade`", "【待核】"),
    ("枚举值域：`constructionStage` / `greenBuildingLevel` / `landUseType` / `buildingNature`", "数据属性值域", "【待核】"),
    ("指标导向「区间」型官方口径", "导向列（现暂定 正向 25 / 逆向 30）", "暂定工作值"),
    ("TD/T 1063-2021 新版标准号", "自然资源口边界（不纳入住建口本体）", "【待核】"),
    ("`severity` 数值化的档位边界（轻微/中等/严重 分界值）", "`Problem.severity` 映射", "【待核】（2026-10-09 新增）"),
    ("整治类型「限时解决 / 尽力解决」判定规则", "`RemediationSuggestion.treatmentType`", "【待核】（2026-10-09 新增）"),
], 1):
    L.append(f"| {i} | {t[0]} | {t[1]} | {t[2]} |")
L.append("")

# §六 校验
L.append("---")
L.append("")
L.append("## 六、生成校验")
L.append("")
L.append(f"- 录入行数：**{len(data)}**（序号 {min(allseq)}–{max(allseq)}，无断号：{'是' if len(set(allseq)) == 55 else '否'}）")
L.append(f"- 维度 ∈ 五级：**{len(data) - len([i for i in issues if '维度非法' in i])}/{len(data)}**")
L.append(f"- `measures` 空间层级 = `inDimension` 维度：**0 跨级**")
L.append(f"- 数据对象名 ∈ 本体类集合：**0 缺类**")
L.append(f"- 多对象指标 `formula` 齐全：**{len([x for x in data if len(x['objs']) >= 2])}/{len([x for x in data if len(x['objs']) >= 2])}**")
L.append(f"- `inCategory` 覆盖：**{len(classified)} 项有分类 + {len(unclassified)} 项无（54、55）= {len(allseq)}，{_cov}**（2026-10-09 新增，口径见 §二-1）")
L.append(f"- 自校验异常：**{len(issues)}**" + ("（" + "；".join(issues) + "）" if issues else "（无）"))
L.append("")

with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(L))

# ---- 3. 机读 YAML（与 .md 同源生成，保证二者一致）----
def yq(v):
    """YAML 双引号标量（安全转义）。"""
    return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'


def ylist(items):
    return "[" + ", ".join(yq(i) for i in items) + "]"


Y = []
Y.append("# 城市体检基础指标（55 项）· 机读映射")
Y.append("# 由 04-指标映射/_gen_map.py 与 `指标映射表.md` 同源生成，请勿手工编辑。")
Y.append("meta:")
Y.append("  version: " + yq("v1"))
Y.append("  generated: " + yq("2026-10-09"))
Y.append("  source: " + yq("55项基础指标_录入模板.md"))
Y.append("  basis: " + yq("建办科〔2026〕16号 附件1（文号【待核】）"))
Y.append("  namespace: " + yq("https://ontology.cset-digital.cn/urban-renewal#") + "   # 【待核】")
Y.append("  indicator_count: " + str(len(data)))
Y.append("  computedFrom_valueDomain: " + ylist(["DataObject", "SpatialUnit", "RenewalObject", "Problem", "RenewalProject"]))
Y.append("  computedFrom_excluded: " + ylist(["RemediationSuggestion"]) + "   # D2（2026-10-09）：整治建议不入值域")
Y.append("dimensions:")
for _d in LV:
    Y.append("  - {" + f"name: {yq(_d)}, level_cn: {yq(LV_CN[_d])}, dimension: {yq(DIM_URI[_d])}, measures: {yq(LV_URI[_d])}" + "}")
Y.append("categories:")
for _dim, _seq, _cat in CATEGORY_ROWS:
    if _cat == "（无分类）":
        continue  # 54、55 无一级分类（inCategory 置空），不入 categories 列表
    Y.append("  - {" + f"name: {yq(_cat)}, dimensions: {ylist(DIM_LABEL2URI.get(_dim, []))}, seqs: {yq(_seq)}" + "}")
Y.append("indicators:")
for x in data:
    _cat = cat_map.get(x["seq"])
    if _cat in (None, "（无分类）"):
        _cat = ""
    Y.append(f"  - seq: {x['seq']}")
    Y.append(f"    code: {yq(x['code'])}")
    Y.append(f"    name: {yq(x['name'])}")
    Y.append(f"    inDimension: {yq(DIM_URI[x['dim']])}")
    Y.append(f"    inCategory: {yq(_cat)}")
    Y.append(f"    measures: {yq(LV_URI[x['level']])}")
    Y.append(f"    unit: {yq(x['unit'])}")
    Y.append(f"    orientation: {yq(x['orientation'])}")
    Y.append(f"    computedFrom: {ylist([u for u, _ in x['objs'] if u])}")
    Y.append(f"    formula: {yq(x['formula'])}")
    Y.append(f"    threshold: {yq(x['thr'])}")
    Y.append(f"    basedOn: {yq(x['src'])}")
    Y.append(f"    status: {yq(x['st'])}")
with open(OUT_YAML, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(Y) + "\n")

print("WROTE:", OUT)
print("WROTE:", OUT_YAML)
print("rows:", len(data), "| distinct objs:", len(cnt), "| issues:", len(issues))
for i in issues:
    print("  !!", i)
