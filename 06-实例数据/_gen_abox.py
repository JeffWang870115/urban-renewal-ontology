# -*- coding: utf-8 -*-
"""W-C02：由样本市四维度成果生成实例层 ABox（脱敏）。

输入（真实数据，不入库）：01-资料/样本成果/
  街道维度 5 / 社区维度 53 / 住房维度 404 / 楼栋台账 1 / 城区 1
输出（脱敏，可入库）：06-实例数据/abox/城市体检实例.ttl
编号映射（真名→编号，不入库）：01-资料/样本成果/_脱敏映射/编号映射.csv

口径要点
  1) 层级取自**目录结构**（区/街道/社区/小区），不依赖名称匹配；台账仅用于楼栋与属性。
  2) 指标 1（结构安全住宅数量）：楼栋旗标按小区聚合 → AssessmentResult（measures=楼栋，assesses=小区）。
  3) 指标 14（公共活动场地未达标社区数）：社区级 IndicatorJudgement（三值）→ 城区级 AssessmentResult（计数）。
     无场地台账 → 由小区级「是否配建 + 面积」派生场地实例，标 dataSource=派生；新建/既有缺判据 → 暂按「既有」并标 derived。
  4) 不臆造：缺失值不写；无法判定的分支在汇总里报数，不静默通过。
"""
from pathlib import Path
import csv
import glob
import os
import re
import warnings

import openpyxl
from rdflib import Graph, Literal, Namespace, RDF, RDFS, XSD

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
# 源目录用「楼栋台账」动态定位，脚本内不出现任何真实地名（脱敏红线）
_HINT = sorted(glob.glob(str(ROOT / "01-资料" / "**" / "楼栋数据.xlsx"), recursive=True))
SRC = Path(_HINT[0]).parent if _HINT else (ROOT / "01-资料")
OUT = ROOT / "06-实例数据" / "abox" / "城市体检实例.ttl"
MAPCSV = SRC / "_脱敏映射" / "编号映射.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)
MAPCSV.parent.mkdir(parents=True, exist_ok=True)

UR = Namespace("https://ontology.cset-digital.cn/urban-renewal#")
G = Graph()
G.bind("ur", UR)
G.bind("rdfs", RDFS)
G.bind("xsd", XSD)

TS = "2025"
anomalies = []


# ---------------- 工具 ----------------
def wb_of(p):
    return openpyxl.load_workbook(str(p), data_only=True)


def val_by_label(ws, key, lo=3, hi=60, val_cols=(3, 4, 5)):
    """按首列标签前缀取值（容忍换行、括号）。"""
    for r in range(lo, min(hi, ws.max_row) + 1):
        lab = ws.cell(r, 1).value
        if not lab:
            continue
        s = re.sub(r"\s+", "", str(lab))
        if s.startswith(key):
            for c in val_cols:
                v = ws.cell(r, c).value
                if v is not None and str(v).strip() != "":
                    return v
    return None


def num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return v
    s = str(v).strip().replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def truthy(v):
    if v is None:
        return None
    s = str(v).strip()
    if s in ("是", "1", "1.0", "True", "有", "已配建"):
        return True
    if s in ("否", "0", "0.0", "False", "无", "未配建"):
        return False
    return None


def year_of(v):
    if v is None:
        return None
    m = re.search(r"(19|20)\d{2}", str(v))
    return m.group(0) if m else None


def add(s, p, o):
    if o is not None:
        G.add((s, UR[p], o))


# ---------------- 1) 目录结构 → 空间单元 ----------------
nb_files = sorted(glob.glob(str(SRC / "街道维度调查统计表(1)" / "**" / "*.xlsx"), recursive=True))
cm_files = sorted(glob.glob(str(SRC / "社区维度调查统计表(1)" / "**" / "*.xlsx"), recursive=True))
rq_files = sorted(glob.glob(str(SRC / "住房维度调查统计表(1)" / "**" / "*.xlsx"), recursive=True))


def relparts(p, base):
    rel = os.path.relpath(p, str(SRC / base))
    return [x for x in Path(rel).parts]


nb_names = sorted({relparts(p, "街道维度调查统计表(1)")[-1].replace(".xlsx", "") for p in nb_files})
NB = {n: "NB_" + chr(ord("A") + i) for i, n in enumerate(nb_names)}

cm_key = {}   # (street, community) -> code
for p in cm_files:
    parts = relparts(p, "社区维度调查统计表(1)")
    street, cm = parts[-2], parts[-1].replace(".xlsx", "")
    cm_key[(street, cm)] = None
cm_sorted = sorted(cm_key.keys())
CM = {k: "CM_S%02d" % (i + 1) for i, k in enumerate(cm_sorted)}

rq_key = {}
for p in rq_files:
    parts = relparts(p, "住房维度调查统计表(1)")
    street, cm, rq = parts[-3], parts[-2], parts[-1].replace(".xlsx", "")
    rq_key[(street, cm, rq)] = p
RQ = {k: "RQ_R%03d" % (i + 1) for i, k in enumerate(sorted(rq_key.keys()))}
RQ_PATH = {RQ[k]: rq_key[k] for k in rq_key}


def norm(s):
    """名称归一：去空白、统一全半角括号、去「XX社区-」前缀、去居委会后缀。"""
    s = str(s).strip()
    s = re.sub(r"\s+", "", s)
    s = s.replace("（", "(").replace("）", ")")
    s = re.sub(r"^.*?社区[-－_]", "", s)
    s = re.sub(r"居委会$", "", s)
    return s


RQ_NORM = {}
for k, c in RQ.items():
    RQ_NORM[(norm(k[0]), norm(k[1]), norm(k[2]))] = c

print(f"单元：街区 {len(NB)} / 社区 {len(CM)} / 小区 {len(RQ)}")

UD = "UD_01"
G.add((UR[UD], RDF.type, UR.UrbanDistrict))
G.add((UR[UD], RDFS.label, Literal("城区UD01", lang="zh")))
G.add((UR[UD], UR.code, Literal("UD01")))

# ---------------- 2) 街区 / 社区 属性 ----------------
for (street, cm), code in CM.items():
    nb = NB[street]
    s = UR[code]
    G.add((s, RDF.type, UR.Community))
    G.add((s, RDFS.label, Literal("社区" + code.split("_")[1], lang="zh")))
    add(s, "code", Literal(code))
    add(s, "locatedIn", UR[nb])

for n, code in NB.items():
    s = UR[code]
    G.add((s, RDF.type, UR.Neighborhood))
    G.add((s, RDFS.label, Literal("街区" + code.split("_")[1], lang="zh")))
    add(s, "code", Literal(code))
    add(s, "locatedIn", UR[UD])

# 街区属性
for p in nb_files:
    parts = relparts(p, "街道维度调查统计表(1)")
    code = NB[parts[-1].replace(".xlsx", "")]
    ws = wb_of(p).worksheets[0]
    for key, prop, typ in [
        ("街区管辖面积", "areaKm2", "dec"), ("街区管辖范围内的社区数量", "communityCount", "int"),
        ("覆盖居民人数", "residentPopulation", "int"), ("覆盖居民户数", "householdCount", "int"),
        ("覆盖企业数量", "enterpriseCount", "int"), ("覆盖就业人数", "employmentCount", "int"),
    ]:
        v = num(val_by_label(ws, key))
        if v is not None:
            add(UR[code], prop, Literal(int(v) if typ == "int" else v))

# 社区属性
for p in cm_files:
    parts = relparts(p, "社区维度调查统计表(1)")
    code = CM[(parts[-2], parts[-1].replace(".xlsx", ""))]
    ws = wb_of(p).worksheets[0]
    for key, prop, typ in [
        ("社区面积", "areaKm2", "dec"), ("社区管辖范围内的小区数量", "rqCount", "int"),
        ("覆盖居民人数", "residentPopulation", "int"), ("覆盖居民户数", "householdCount", "int"),
        ("小汽车拥有量", "carOwnership", "int"), ("新能源汽车数量", "evCount", "int"),
        ("停车位需求数", "parkingDemand", "int"), ("现有停车位数量", "parkingSupply", "int"),
    ]:
        v = num(val_by_label(ws, key))
        if v is not None:
            add(UR[code], prop, Literal(int(v) if typ == "int" else v))

# ---------------- 3) 小区属性 + 场地实例 ----------------
RQ_ATTR = [
    ("小区类型", "rqType", "str"), ("老旧小区改造情况", "renovationStatus", "str"),
    ("建筑全部数量", "buildingCount", "int"), ("总建筑面积", "totalFloorArea", "dec"),
    ("住宅总套数", "housingUnitCount", "int"), ("常住人口", "residentPopulation", "int"),
    ("六十岁以上常住人口", "elderlyPopulation", "int"),
    ("居民需求停车位数量", "parkingDemand", "int"), ("现有停车位数量", "parkingSupply", "int"),
    ("居民需求充电桩数量", "evChargerDemand", "int"), ("现有新能源汽车充电桩数量", "evChargerSupply", "int"),
    ("电动自行车充电设施数量", "ebikeFacilityCount", "int"),
    ("不达标的步行道长度", "nonCompliantWalkwayLength", "dec"),
    ("生活垃圾分类点数量", "wasteSortingStationCount", "int"),
]
RQ_BOOL = [
    ("是否配建电动自行车充电设施", "ebikeFacilityBuilt"),
    ("是否配建公共绿地", "publicGreenBuilt"),
    ("是否实施生活垃圾分类", "wasteSortingStatus"),
    ("是否实施物业管理", "propertyManagementStatus"),
    ("是否安装智能信包箱", "smartParcelLocker"),
    ("是否配备完善的智能安防设施", "smartSecurity"),
]
RQ_AREA = [("公共活动场地用地面积", "publicVenueArea"), ("公共绿地面积", "publicGreenArea")]

pv_count = 0
for key, code in RQ.items():
    p = RQ_PATH[code]
    street, cm, _ = key
    s = UR[code]
    G.add((s, RDF.type, UR.ResidentialQuarter))
    G.add((s, RDFS.label, Literal("小区" + code.split("_")[1], lang="zh")))
    add(s, "code", Literal(code))
    add(s, "locatedIn", UR[CM[(street, cm)]])
    ws = wb_of(p).worksheets[0]
    for lab, prop, typ in RQ_ATTR:
        v = val_by_label(ws, lab)
        if typ == "str":
            add(s, prop, Literal(str(v).strip(), lang="zh")) if v is not None else None
        else:
            n = num(v)
            if n is not None:
                add(s, prop, Literal(int(n) if typ == "int" else n))
    cy = year_of(val_by_label(ws, "建造时间"))
    if cy:
        add(s, "constructionYear", Literal(cy, datatype=XSD.gYear))
    for lab, prop in RQ_BOOL:
        b = truthy(val_by_label(ws, lab))
        if b is not None:
            add(s, prop, Literal(b))
    for lab, prop in RQ_AREA:
        n = num(val_by_label(ws, lab))
        if n is not None:
            add(s, prop, Literal(n))

    # 场地实例（派生）：仅在「配建=是」时物化，面积来自小区级填报
    built = truthy(val_by_label(ws, "是否配建公共活动场地"))
    area = num(val_by_label(ws, "公共活动场地用地面积"))
    if built:
        pv = UR["PV_" + code.split("_")[1]]
        G.add((pv, RDF.type, UR.PublicActivityVenue))
        G.add((pv, RDFS.label, Literal("公共活动场地（派生）" + code.split("_")[1], lang="zh")))
        G.add((pv, UR.belongsTo, s))
        G.add((pv, UR.dataSource, Literal("派生：由小区级「配建+面积」物化，非逐场地台账", lang="zh")))
        if area is not None:
            G.add((pv, UR.facilityArea, Literal(area)))
        pv_count += 1
print(f"场地实例（派生）：{pv_count}")

# ---------------- 4) 楼栋 + 指标 1 ----------------
# 2026-11-20 改：数据源切到大王指定的权威表 楼栋数据.xlsx（共享模块 _shared_楼栋台账）。
# 新表3599栋、三键(街道,社区,小区)100%命中映射表，不再有旧表128条跳过的问题。
import sys as _sys
_sys.path.insert(0, str(ROOT / "06-实例数据"))
from _shared_楼栋台账 import read_scopes as _read_scopes  # noqa: E402

_stats, _rows, _hz = _read_scopes()
assert len(_rows) == 3599, f"权威楼栋数应3599，实得{len(_rows)}"

# 新表列号 -> 本体核查项（指标号→CI，非成套5.x与节能8.2/8.3无对应CI，不映射）
_CI_MAP = {
 '1.1':'CI_H1_1','1.2':'CI_H1_2','1.3':'CI_H1_3','1.4':'CI_H1_4',
 '2.1':'CI_H2_1','2.2':'CI_H2_2','2.3':'CI_H2_3',
 '3.1':'CI_H3_1','3.2':'CI_H3_2','3.3':'CI_H3_3','3.4':'CI_H3_4',
 '3.5':'CI_H3_5','3.6':'CI_H3_6','3.7':'CI_H3_7','3.8':'CI_H3_8',
 '4.1':'CI_H4_1','4.2':'CI_H4_2','4.3':'CI_H4_3','4.4':'CI_H4_4','4.5':'CI_H4_5',
 '6.1':'CI_H5_1','6.2':'CI_H5_2','6.3':'CI_H5_3',
 '7.1':'CI_H6_1','7.2':'CI_H6_2','7.3':'CI_H6_3','7.4':'CI_H6_4',
 '8.1':'CI_H7_1',
 '9.1':'CI_H8_1','9.2':'CI_H8_2','9.3':'CI_H8_3','9.4':'CI_H8_4',
}
# 打开新表只读核查项列（按行2指标号定位，不硬编码列号）
import openpyxl as _opx
_led_path = sorted((ROOT / "01-资料").glob("**/楼栋数据.xlsx"))[0]
_wb = _opx.load_workbook(str(_led_path), data_only=True)
_ws = _wb.active
_ci_cols = {}
for _c in range(15, _ws.max_column + 1):
    _no = str(_ws.cell(2, _c).value or '').strip()
    if _no in _CI_MAP:
        _ci_cols[_no] = _c
assert len(_ci_cols) == 32, f"核查项列应32，实得{len(_ci_cols)}"
# 楼栋属性列（新表）：单元数8 / 层数9 / 建造时间10 / 住宅套数12 / 常住人口13 / 老年人口14
def _cellv(_r, _c):
    return _ws.cell(_r, _c).value

hits = {}       # (rcode, indicator_seq) -> set of building uris
ci_total = 0
rq_unsafe = {}
b_count = 0
miss_q = 0
# _rows 元组: (街道,社区,小区,楼栋名, flags[2026编号 1-8 bool])
for _s, _cm, _q, _bname, _flags in _rows:
    key = (str(_s).strip(), str(_cm).strip(), str(_q).strip())
    rcode = RQ.get(key) or RQ_NORM.get((norm(key[0]), norm(key[1]), norm(key[2])))
    if rcode is None:
        miss_q += 1
        continue
    b_count += 1
    b = UR["BD_B%04d" % b_count]
    G.add((b, RDF.type, UR.Building))
    G.add((b, RDFS.label, Literal("楼栋B%04d" % b_count, lang="zh")))
    add(b, "code", Literal("BD-B%04d" % b_count))
    add(b, "locatedIn", UR[rcode])
    add(b, "name", Literal("楼栋B%04d" % b_count, lang="zh"))
    add(b, "buildingNature", Literal("住宅", lang="zh"))
    # 属性按新表列读（行号=3+序号，_rows 保序）
    _r = 3 + b_count
    for _col, _prop in [(8, "unitCount"), (9, "floorCount"), (13, "residentPopulation"), (14, "elderlyPopulation")]:
        _n = num(_cellv(_r, _col))
        if _n is not None:
            add(b, _prop, Literal(int(_n)))
    _cy = year_of(_cellv(_r, 10))
    if _cy:
        add(b, "constructionYear", Literal(_cy, datatype=XSD.GYear))
    # 楼栋状态属性：8 项汇总旗标（新表列15/16/17/18/41/42/52/53，对应2026指标1-8）
    _SUMCOL = {1:15, 2:16, 3:17, 4:18, 5:41, 6:42, 7:52, 8:53}
    _PROPMAP = {1:("structureSafetyStatus",{1:"有隐患",0:"安全"}),
                2:("gasSafetyStatus",{1:"有隐患",0:"安全"}),
                3:("corridorSafetyStatus",{1:"有隐患",0:"安全"}),
                4:("envelopeSafetyStatus",{1:"有隐患",0:"安全"}),
                5:("pipelineStatus",{1:"破损",0:"正常"}),
                6:("agingAdaptationNeed",None), 7:("energyRetrofitNeed",None), 8:("digitalRetrofitNeed",None)}
    for _seq, _col in _SUMCOL.items():
        _raw = num(_cellv(_r, _col))
        if _raw is None:
            continue
        _prop, _mp = _PROPMAP[_seq]
        add(b, _prop, Literal(_mp.get(int(_raw),"未知"), lang="zh") if _mp else Literal(bool(int(_raw))))
    # 核查项命中：按指标号从新表细项列读（_ci_cols），映射到本体 CI
    for _no, _ci in _CI_MAP.items():
        _ciid = _ci  # 如 CI_H1_1
        _col = _ci_cols[_no]
        if num(_cellv(_r, _col)) == 1:
            G.add((b, UR.failsCheckItem, UR[_ciid]))
            _seq = int(_ciid.split("_")[1][1:])  # H1->1 ... H8->8
            hits.setdefault((rcode, _seq), set()).add(b)
            ci_total += 1
    # 指标1旗标（用于下游对账）
    if _flags.get("1"):
        rq_unsafe[rcode] = rq_unsafe.get(rcode, 0) + 1
_wb.close()

print(f"楼栋：{b_count}（权威表3599，小区名对不上目录跳过 {miss_q} 条）")
assert b_count == 3599, f"应建3599栋，实得{b_count}"
assert miss_q == 0, f"权威表应全部命中目录，跳过{miss_q}条"
if miss_q:
    anomalies.append(f"楼栋台账有 {miss_q} 条记录的（街道,社区,小区）组合在目录中不存在")

# 指标 1–8：由核查项命中派生（2026-11-08）。值 = 小区内「命中该指标任一核查项」的楼栋数（去重）
print(f"核查项命中记录：{ci_total}")
_ar_cnt = 0
for rcode in [RQ[k] for k in sorted(RQ.keys())]:
    for seq in range(1, 9):
        n = len(hits.get((rcode, seq), ()))
        ar = UR["AR_%s_I%02d" % (rcode, seq)]
        G.add((ar, RDF.type, UR.AssessmentResult))
        G.add((ar, UR.ofIndicator, UR["Indicator_%d" % seq]))
        G.add((ar, UR.assesses, UR[rcode]))
        G.add((ar, UR.indicatorValue, Literal(n)))
        G.add((ar, UR.unit, Literal("个", lang="zh")))
        G.add((ar, UR.year, Literal(TS, datatype=XSD.GYear)))
        _ar_cnt += 1

# 对账：指标 1 的核查项派生值 vs 原旗标口径（应完全一致）
_diff = 0
for rcode in [RQ[k] for k in sorted(RQ.keys())]:
    if rq_unsafe.get(rcode, 0) != len(hits.get((rcode, 1), ())):
        _diff += 1
print(f"指标 1 对账：核查项派生 vs 旗标口径，不一致小区数 = {_diff}（应为 0）")
print(f"指标 1–8 结果实例：{_ar_cnt}")

# ---------------- 5) 指标 14：判断（社区级）→ 结果（城区级） ----------------
def q_area(code):
    for pv in G.subjects(UR.belongsTo, UR[code]):
        a = G.value(pv, UR.facilityArea)
        return float(a) if a is not None else None
    return None


def q_has_venue(code):
    return any(True for _ in G.subjects(UR.belongsTo, UR[code]))


judg = {"未配建": 0, "配建不达标": 0, "达标": 0}
for (street, cm), code in CM.items():
    c = UR[code]
    pop = G.value(c, UR.residentPopulation)
    pop = int(pop) if pop is not None else None
    quarters = [RQ[k] for k in RQ if k[0] == street and k[1] == cm]
    has = any(q_has_venue(qc) for qc in quarters)
    areas = [a for a in (q_area(qc) for qc in quarters) if a is not None]
    maxa = max(areas) if areas else None

    if not has:
        jv, ev = "未配建", None
    else:
        # 口径：人口 ≤5000 → 既有 100 / 新建 600；>5000 → 既有 150 / 新建 800
        # 新建/既有缺场地级建设年代 → 暂按「既有」并标 derived
        if pop is None:
            jv, ev = "配建不达标", None     # 人口缺失，无法取阈 → 保守判「配建不达标」
            anomalies.append(f"{code} 缺常住人口，指标14 阈值无法确定，按「配建不达标」保守处理")
        else:
            thr = 150 if pop > 5000 else 100
            jv = "达标" if (maxa is not None and maxa >= thr) else "配建不达标"
        ev = next((pv for pv in G.subjects(UR.belongsTo, c)), None) if has else None
    judg[jv] += 1

    ij = UR["IJ_%s_I14" % code]
    G.add((ij, RDF.type, UR.IndicatorJudgement))
    G.add((ij, UR.ofIndicator, UR["Indicator_14"]))
    G.add((ij, UR.assesses, c))
    G.add((ij, UR.judgementValue, Literal(jv, lang="zh")))
    G.add((ij, UR.year, Literal(TS, datatype=XSD.GYear)))
    G.add((ij, UR.dataSource, Literal("派生：小区级配建与面积聚合；建设性质按「既有」假定", lang="zh")))
    for qc in quarters:
        for pv in G.subjects(UR.belongsTo, UR[qc]):
            G.add((ij, UR.basedOnEvidence, pv))

bad = judg["未配建"] + judg["配建不达标"]
ar = UR["AR_UD01_I14"]
G.add((ar, RDF.type, UR.AssessmentResult))
G.add((ar, UR.ofIndicator, UR["Indicator_14"]))
G.add((ar, UR.assesses, UR[UD]))
G.add((ar, UR.indicatorValue, Literal(bad)))
G.add((ar, UR.unit, Literal("个", lang="zh")))
G.add((ar, UR.year, Literal(TS, datatype=XSD.GYear)))

print(f"指标14 判断：未配建 {judg['未配建']} / 配建不达标 {judg['配建不达标']} / 达标 {judg['达标']} → 城区结果 {bad}")

# ---------------- 5.2 指标 15：不达标的步行道长度（E 类，小区 Σ → 社区） ----------------
_e15 = 0
for (street, cm), code in CM.items():
    quarters = [RQ[k] for k in RQ if k[0] == street and k[1] == cm]
    vals = [float(v) for v in (G.value(UR[q], UR.nonCompliantWalkwayLength) for q in quarters) if v is not None]
    if not vals:
        continue                       # 无实测值不写 0，避免把「缺测」当「达标」
    ar = UR["AR_%s_I15" % code]
    G.add((ar, RDF.type, UR.AssessmentResult))
    G.add((ar, UR.ofIndicator, UR["Indicator_15"]))
    G.add((ar, UR.assesses, UR[code]))
    G.add((ar, UR.indicatorValue, Literal(round(sum(vals), 2))))
    # 单位按《55项指标.yaml》指标 15 = 千米；住房表源列未标单位，与社区表填报值的比值见对账清单
    G.add((ar, UR.unit, Literal("千米", lang="zh")))
    G.add((ar, UR.year, Literal(TS, datatype=XSD.GYear)))
    _e15 += 1
print(f"指标 15（Σ 步行道长度）：{_e15} 个社区有结果")

# ---------------- 5.3 街区 8 项（2026 编号 19–26），源：街区数据.xlsx（2025 编码 22–29） ----------------
def lead_num(x):
    """取单元格首段数字：如 '1,分别是…' → 1；'61.7' → 61.7。"""
    if x is None:
        return None
    m = re.match(r"\s*(-?\d+(?:\.\d+)?)", str(x).replace(",", ""))
    return float(m.group(1)) if m else None


NB_MAP = [(10, 22, "%"), (11, 21, "个"), (12, 20, "个"), (13, 19, "%"),
          (14, 23, "条"), (15, 26, "个"), (16, 25, "个"), (19, 24, "个")]
p_nb = SRC / "街区数据.xlsx"
_nb_cnt = 0
if p_nb.exists():
    ws2 = wb_of(p_nb).worksheets[0]
    for r in range(4, ws2.max_row + 1):
        nm = ws2.cell(r, 1).value
        if not nm:
            continue
        code = NB.get(str(nm).strip())
        if code is None:
            anomalies.append("街区表出现未匹配街道名（行 %d），已跳过" % r)
            continue
        for col, y26, unit in NB_MAP:
            v = lead_num(ws2.cell(r, col).value)
            if v is None:
                continue
            ar = UR["AR_%s_I%02d" % (code, y26)]
            G.add((ar, RDF.type, UR.AssessmentResult))
            G.add((ar, UR.ofIndicator, UR["Indicator_%d" % y26]))
            G.add((ar, UR.assesses, UR[code]))
            G.add((ar, UR.indicatorValue, Literal(v)))
            G.add((ar, UR.unit, Literal(unit, lang="zh")))
            G.add((ar, UR.year, Literal(TS, datatype=XSD.GYear)))
            _nb_cnt += 1
print(f"街区指标 19–26：{_nb_cnt} 条结果")

# ---------------- 5.4 社区 10 项（2026 编号 9–18）+ 小区 8 项校验基准 ----------------
# 源：社区数据.xlsx / 小区数据.xlsx（均为 2025 手册编号，须按「指标名称」对齐 2026，不可按编号直搬）
# 大王 2026-11-08 口径：
#   ① 9/10/14 判断的是「社区下辖养老服务设施 / 婴幼儿托育设施 / 公共活动场地」的配建情况；
#      源表给的是「未达标配建 X 的小区数量」(2025)，>0 即该社区设施未达标 → 社区口径记 1。
#   ② 12/13/15/16/17/18 数值本身即 2026 口径，直接挂对应层级。
#   ③ 11 按「停车泊位 < 1 车位/户」自算，允许以「住宅总套数」代替户数【口径近似·待核】。
#   A 方案：小区 1–8 保留核查项派生值；填报值作校验基准；差异进清单。

def find_src(name):
    hits = [p for p in glob.glob(str(ROOT / "01-资料" / "**" / name), recursive=True)
            if not os.path.basename(p).startswith("~$")]
    return Path(hits[0]) if hits else None


def cm_lookup(street, community):
    k = (str(street or "").strip(), str(community or "").strip())
    if k in CM:
        return CM[k]
    n = (norm(k[0]), norm(k[1]))
    cand = [c for kk, c in CM.items() if (norm(kk[0]), norm(kk[1])) == n]
    if len(cand) == 1:
        return cand[0]
    cand = [c for kk, c in CM.items() if norm(kk[1]) == n[1]]
    return cand[0] if len(cand) == 1 else None


def rq_lookup(street, community, rq):
    k = (str(street or "").strip(), str(community or "").strip(), str(rq or "").strip())
    if k in RQ:
        return RQ[k]
    n = (norm(k[0]), norm(k[1]), norm(k[2]))
    if n in RQ_NORM:
        return RQ_NORM[n]
    cand = [c for kk, c in RQ.items() if norm(kk[2]) == n[2]]
    return cand[0] if len(cand) == 1 else None


def put_result(code, y26, value, unit):
    ar = UR["AR_%s_I%02d" % (code, y26)]
    G.add((ar, RDF.type, UR.AssessmentResult))
    G.add((ar, UR.ofIndicator, UR["Indicator_%d" % y26]))
    G.add((ar, UR.assesses, UR[code]))
    G.add((ar, UR.indicatorValue, Literal(value)))
    G.add((ar, UR.unit, Literal(unit, lang="zh")))
    G.add((ar, UR.year, Literal(TS, datatype=XSD.GYear)))
    return ar


RECON = []      # 全量对账：填报值即校验基准，差异行即差异清单


def recon(layer, code, y26, derived, reported, note=""):
    d = None if derived is None or reported is None else abs(float(derived) - float(reported))
    RECON.append([layer, code, y26,
                  "" if derived is None else derived,
                  "" if reported is None else reported,
                  "" if d is None else round(d, 3),
                  "一致" if d is not None and d < 0.001 else ("差异" if d is not None else "缺测"),
                  note])


# 2025 社区表列 → (2026 指标, 单位, 处置类别)
CM_COLS = {
    18: (9,  "个",   "①转社区口径"),          # 2025-10 未达标配建养老服务设施的小区数量
    19: (10, "个",   "①转社区口径"),          # 2025-11 未达标配建婴幼儿照护服务设施的小区数量
    22: (11, "个",   "③参考·缺口总量"),       # 2025-14 停车泊位缺口数（口径不同，仅留痕）
    23: (12, "个",   "②直接"),                # 2025-15 新能源汽车充电桩缺口数
    24: (13, "个",   "②直接"),                # 2025-16 未配建电动自行车充电设施的小区数量
    26: (14, "个",   "①转社区口径·校验"),     # 2025-17 未达标配建公共活动场的小区数量
    27: (15, "千米", "②保留派生·校验"),       # 2025-18 不达标的步行道长度（千米）
    28: (16, "个",   "②直接"),                # 2025-19 未实施生活垃圾分类的小区数量
    29: (17, "个",   "②直接"),                # 2025-20 未实施好物业管理的小区数量
    30: (18, "个",   "②直接"),                # 2025-21 需要进行智慧化改造的小区数量
}
FACILITY = {9: ("ElderlyCareFacility", "ECF"), 10: ("InfantCareFacility", "ICF")}

p_cm = find_src("社区数据.xlsx")
cm_vals = {}
if p_cm:
    ws3 = wb_of(p_cm).worksheets[0]
    cur_st = ""
    for r in range(4, ws3.max_row + 1):
        st, cmn = ws3.cell(r, 1).value, ws3.cell(r, 2).value
        if st and str(st).strip():
            cur_st = str(st).strip()
        if not cmn or str(cmn).strip() == "":
            continue
        code = cm_lookup(cur_st, str(cmn).strip())
        if code is None:
            anomalies.append("社区表第 %d 行未匹配到社区编号，已跳过" % r)
            continue
        vals = {y26: lead_num(ws3.cell(r, col).value) for col, (y26, _u, _k) in CM_COLS.items()}
        cm_vals[code] = vals
        # ② 直接挂：数值本身即 2026 口径（assesses=社区；measures 见 yaml，二者不同）
        for y26 in (12, 13, 16, 17, 18):
            v = vals.get(y26)
            if v is None:
                continue
            put_result(code, y26, v, "个")
        # ① 9 / 10：社区级判断（依据＝下辖设施配建情况）→ 城区级计数
        for y26 in (9, 10):
            v = vals.get(y26)
            if v is None:
                continue                    # 缺测不建判断，避免把「缺测」当「达标」
            cls, pref = FACILITY[y26]
            fac = UR["%s_%s" % (pref, code.split("_")[1])]
            G.add((fac, RDF.type, UR[cls]))
            G.add((fac, UR.belongsTo, UR[code]))
            G.add((fac, UR.dataSource, Literal(
                "派生：源表仅给「未达标小区数量」，无逐设施台账；未配建态无法区分【待核】", lang="zh")))
            jv = "配建不达标" if v > 0 else "达标"
            ij = UR["IJ_%s_I%02d" % (code, y26)]
            G.add((ij, RDF.type, UR.IndicatorJudgement))
            G.add((ij, UR.ofIndicator, UR["Indicator_%d" % y26]))
            G.add((ij, UR.assesses, UR[code]))
            G.add((ij, UR.judgementValue, Literal(jv, lang="zh")))
            G.add((ij, UR.year, Literal(TS, datatype=XSD.GYear)))
            G.add((ij, UR.dataSource, Literal(
                "派生：2025「未达标小区数量」转 2026 社区口径；判断依据为社区下辖设施配建情况", lang="zh")))
            G.add((ij, UR.basedOnEvidence, fac))
    print("社区表：匹配 %d 个社区" % len(cm_vals))
else:
    anomalies.append("未找到社区数据.xlsx，社区 10 项未接入")

# 城区级聚合：9 / 10（count 未达标社区）
for y26 in (9, 10):
    n = sum(1 for vals in cm_vals.values() if (vals.get(y26) or 0) > 0)
    put_result(UD, y26, n, "个")
    print("指标 %d 城区结果（未达标社区数）：%d" % (y26, n))

# 14 校验：派生三值判断层（5.1 的 bad）vs 社区表填报口径
n14_report = sum(1 for vals in cm_vals.values() if (vals.get(14) or 0) > 0)
recon("城区", UD, 14, bad, n14_report, "派生三值判断 vs 2025 填报值>0 的社区数")
print("指标 14 对账：派生 %d / 填报 %d" % (bad, n14_report))

# 15 校验：ABox 派生值（5.2，单位千米）vs 社区表填报值（千米）
for code, vals in cm_vals.items():
    rep = vals.get(15)
    if rep is None:
        continue
    av = G.value(UR["AR_%s_I15" % code], UR.indicatorValue)
    recon("社区", code, 15, float(av) if av is not None else None, rep, "派生Σ vs 填报(千米)")

# ---------------- ③ 指标 11：停车泊位 < 1 车位/户（以住宅总套数代替户数） ----------------
n11 = 0
n11_missing = 0
for rcode in RQ.values():
    sup = G.value(UR[rcode], UR.parkingSupply)
    units = G.value(UR[rcode], UR.housingUnitCount)
    if sup is None or units is None or float(units) <= 0:
        n11_missing += 1
        continue
    flag = 1 if float(sup) / float(units) < 1 else 0
    ar = put_result(rcode, 11, flag, "个")
    G.add((ar, UR.dataSource, Literal(
        "口径近似：以住宅总套数代替户数判「车位/户<1」【待核】", lang="zh")))
    n11 += flag
put_result(UD, 11, n11, "个")
print("指标 11 自算：参与 %d 小区 / 缺口小区 %d / 缺数据 %d" %
      (len(RQ) - n11_missing, n11, n11_missing))

# ---------------- A 方案：小区 1–8 填报值作校验基准 ----------------
RQ_COLS = {13: (1, 1), 15: (2, 2), 17: (3, 3), 19: (4, 4),
           25: (6, 5), 27: (7, 6), 29: (8, 7), 31: (9, 8)}
p_rq = find_src("小区数据.xlsx")
n_rq_recon = 0
if p_rq:
    ws4 = wb_of(p_rq).worksheets[0]
    cur_st = cur_cm = ""
    for r in range(5, ws4.max_row + 1):
        st, cmn, rqn = ws4.cell(r, 1).value, ws4.cell(r, 2).value, ws4.cell(r, 3).value
        if st and str(st).strip():
            cur_st = str(st).strip()
        if cmn and str(cmn).strip():
            cur_cm = str(cmn).strip()
        if not rqn:
            continue
        code = rq_lookup(cur_st, cur_cm, str(rqn).strip())
        if code is None:
            anomalies.append("小区表第 %d 行未匹配到小区编号，已跳过" % r)
            continue
        for col, (_sy, y26) in RQ_COLS.items():
            rep = lead_num(ws4.cell(r, col).value)
            if rep is None:
                continue
            av = G.value(UR["AR_%s_I%02d" % (code, y26)], UR.indicatorValue)
            recon("小区", code, y26, float(av) if av is not None else None, rep,
                  "核查项派生值 vs 填报值（A 方案：派生为主）")
            n_rq_recon += 1
    print("小区 1–8 校验基准行：%d" % n_rq_recon)
else:
    anomalies.append("未找到小区数据.xlsx，小区 8 项校验基准未生成")

# ---------------- 校验基准 / 差异清单落盘 ----------------
OUT_RECON = ROOT / "06-实例数据" / "校验" / "实例接入对账.csv"
OUT_RECON.parent.mkdir(parents=True, exist_ok=True)
with open(OUT_RECON, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["层级", "编号", "指标序号", "派生值(ABox)", "填报值(校验基准)",
                "差值", "状态", "备注"])
    w.writerows(RECON)
diff_rows = [x for x in RECON if x[6] == "差异"]
print("WROTE:", OUT_RECON, "| 对账行", len(RECON), "| 差异行", len(diff_rows))

# ---------------- 6) 落盘 ----------------
G.serialize(destination=str(OUT), format="turtle")
print("WROTE:", OUT, "| triples:", len(G))

with open(MAPCSV, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["编号", "层级", "原名（本地，不入库）"])
    w.writerow([UD, "城区", ""])
    for n, c in NB.items():
        w.writerow([c, "街区", n])
    for (st, cm), c in CM.items():
        w.writerow([c, "社区", st + "/" + cm])
    for (st, cm, rq), c in RQ.items():
        w.writerow([c, "小区", st + "/" + cm + "/" + rq])
print("WROTE:", MAPCSV)

if anomalies:
    print("\n异常（进异常清单，不静默丢弃）：")
    for a in anomalies[:10]:
        print("  -", a)
