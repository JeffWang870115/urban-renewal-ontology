# -*- coding: utf-8 -*-
"""本体建模·第 4 步导出生成器：由 55项指标.yaml + 类与层级.md / 属性与关系.md
导出 三个机读产物（rdflib）：
  - 03-本体模型/城市体检-更新本体.ttl    （TBox + ABox，OWL/Turtle）
  - 03-本体模型/城市体检-更新约束.shacl  （SHACL 形状）
  - 03-本体模型/常用查询.sparql          （示例 SPARQL）

设计要点：
  1) TBox 结构在脚本内显式声明（每条注明来源小节）。生成前跑**两条断言**：
     ① 正向防漂移——每个已声明 URI 均出现在源 md；
     ② 反向引用闭合（2026-10-11 新增）——凡被当作父类、或被属性定义域/值域引用的类，
        都必须已在脚本中声明，否则直接失败（防「被 subClassOf 引用却未声明」）。
  2) ABox 由 04-指标映射/55项指标.yaml 读取（55 个 Indicator 实例）。
  3) 值域/取值含【待核】处一律以注释标出，不臆造。
"""
import os
from rdflib import Graph, Namespace, BNode, Literal, RDF, RDFS, OWL, XSD
from rdflib.namespace import SH
from rdflib.collection import Collection
import yaml

BASE = r"E:\中设数字\00-01-个人\02-学习\01-wordbuddy\2026_working_space\城市体检与更新本体研究"
M = os.path.join(BASE, "03-本体模型")
YAMLP = os.path.join(BASE, "04-指标映射", "55项指标.yaml")
MD_CLS = os.path.join(M, "类与层级.md")
MD_PROP = os.path.join(M, "属性与关系.md")
OUT_TTL = os.path.join(M, "城市体检-更新本体.ttl")
OUT_SHACL = os.path.join(M, "城市体检-更新约束.shacl")
OUT_SPARQL = os.path.join(M, "常用查询.sparql")

UR = Namespace("https://ontology.cset-digital.cn/urban-renewal#")
NS = "https://ontology.cset-digital.cn/urban-renewal#"

MDC = open(MD_CLS, encoding="utf-8").read()
MDP = open(MD_PROP, encoding="utf-8").read()

# ---------- 结构声明（来源：类与层级.md / 属性与关系.md） ----------
# 顶层类（类与层级.md §一，16 个）
TOP = [
    ("SpatialUnit", "空间单元"), ("Dimension", "指标维度"), ("IndicatorCategory", "指标分类"),
    ("Indicator", "体检指标"), ("DataObject", "数据对象"), ("ExaminationActivity", "体检活动"),
    ("AssessmentResult", "评估结果"), ("Problem", "问题短板"), ("RemediationSuggestion", "整治建议"),
    ("RenewalObject", "更新对象"), ("RenewalProject", "更新项目"), ("RenewalApproach", "更新方式"),
    ("Actor", "行动主体"), ("Fund", "资金"), ("PolicyStandard", "政策标准"), ("TimePeriod", "时间周期"),
]
# 子类： parent -> [(uri, 中文名), ...]（来源见各小节）
SUB = {
    "SpatialUnit": [("Building", "建筑（楼栋）"), ("ResidentialQuarter", "小区"), ("Community", "社区"),
                    ("Neighborhood", "街区"), ("UrbanDistrict", "城区（城市）")],                      # §2.1
    # 注：Dimension 的 5 个取值（HousingDimension 等）按 ABox 需要序列化为**个体**（见下），此处不作子类声明，避免 class/individual punning。
    "RenewalObject": [("OldResidentialQuarter", "老旧小区"), ("UrbanVillage", "城中村"), ("OldBlock", "老旧街区"),
                      ("OldIndustrialArea", "老旧厂区"), ("Infrastructure", "市政基础设施"),
                      ("CompleteCommunity", "完整社区")],                                            # §2.3
    "OldBlock": [("OldCommercialBlock", "老旧商业街区"), ("OldResidentialBlock", "老旧生活街区")],    # §2.3
    "RenewalApproach": [("Retrofit", "保留改造提升"), ("Renovation", "整治提升"),
                        ("Reconstruction", "拆除重建"), ("MicroRenewal", "微改造")],                  # §2.4
    "Actor": [("Government", "政府/主管部门"), ("Implementer", "实施主体"), ("RightsHolder", "产权人"),
              ("Resident", "居民"), ("SocialCapital", "社会资本")],                                   # §2.5
    "Fund": [("CentralTransfer", "中央财政转移支付"), ("LocalFiscal", "地方财政"),
             ("SocialCapitalFund", "社会资本")],                                                     # §2.6
    "PolicyStandard": [("NationalStandard", "国家标准"), ("IndustryStandard", "行业标准"),
                       ("AssociationStandard", "团体标准"), ("PolicyDocument", "政策文件"),
                       ("TechnicalGuide", "技术导则"), ("LocalRegulation", "地方条例")],               # §2.7
    "DataObject": [("FacilityObject", "设施对象"), ("SpaceObject", "空间对象"), ("LineObject", "线路对象"),
                   ("HeritageObject", "历史文化保护实体"), ("EventObject", "事件对象"),
                   ("ManagementObject", "管理对象"), ("Land", "用地")],                             # §2.9.1 / §2.8.1
    "Land": [("ResidentialLand", "居住用地"), ("ConstructionLand", "建设用地")],                     # §2.8.1
    "EvaluationRule": [("WarningRule", "预警规则"), ("AssessmentRule", "达标评价规则"),
                       ("CrossDomainRule", "跨域规则")],                                            # §2.9.3
    "FacilityObject": [("ElderlyCareFacility", "养老服务设施"), ("InfantCareFacility", "婴幼儿托育设施"),
                       ("MiddleSchool", "中学"), ("ParkingSpace", "停车泊位"), ("EVChargingPile", "新能源汽车充电桩"),
                       ("EbikeChargingFacility", "电动自行车充电设施"), ("CulturalActivityCenter", "文化活动中心"),
                       ("PublicCulturalFacility", "公共文化设施"), ("FireStation", "消防站"),
                       ("DualUseInfrastructure", "平急两用公共基础设施"), ("EmergencyShelter", "应急避难场所"),
                       ("DrainageFacility", "排水防涝设施"), ("EmergencyWaterSource", "应急水源"),
                       ("RailTransitStation", "轨道站点"), ("Bridge", "桥梁"),
                       ("LifelineRiskPoint", "城市生命线风险点")],                                   # §2.8.2 / §2.9.1
    "SpaceObject": [("PublicActivityVenue", "公共活动场地"), ("ParkGreenSpace", "公园绿化活动场地"),
                    ("MultiFunctionSportsGround", "多功能运动场地"), ("SportsVenue", "体育场地")],      # §2.8.2 / §2.9.1
    "LineObject": [("Walkway", "步行道"), ("Road", "道路"), ("Greenway", "绿道"),
                   ("GasPipeline", "老旧市政燃气管网")],                                             # §2.8.2 / §2.9.1
    "HeritageObject": [("HistoricalBuilding", "历史文化街区/历史建筑"), ("HistoricBlockBuilding", "历史街区内建筑物/构筑物"),
                       ("ProtectedObject", "保护对象")],                                             # §2.8.2 / §2.9.1
    "EventObject": [("NegativeEvent", "负面事件"), ("SafetyAccident", "生产安全事故")],                # §2.8.2 / §2.9.1
    "ManagementObject": [("PublicRentalHousing", "公租房轮候记录"), ("RiskyConstructionWorks", "危险性较大分部分项工程"),
                         ("UrbanOperationPlatform", "城市运行管理平台")],                             # §2.8.2 / §2.9.1
}
# ⚠ 2026-10-11 修：此处原有重复键 `"DataObject": None,`，因 Python 字典重复键取末值，
#    把上面 DataObject 一行的 7 个父类（FacilityObject/SpaceObject/LineObject/HeritageObject/
#    EventObject/ManagementObject/Land）整个覆盖掉，导致「被 subClassOf 引用但未声明」的类。
#    已删除该行，并新增反向防漂移断言（见下），此类问题不再静默通过。
# DataObject 下的基础量（§2.8.3）与散件——直接挂 DataObject
BASIC_Q = [("BuiltUpArea", "建成区面积"), ("PermanentPopulation", "常住人口数"), ("CityRoadLength", "城市道路长度"),
           ("RailCommutingVolume", "轨道交通通勤量"), ("TotalCommutingVolume", "城市总通勤量"),
           ("AverageDailyWaterSupply", "平均日供水量"), ("ProjectsUnderConstruction", "在建项目数量"),
           ("VehicleTravelSpeed", "机动车行驶速度")]
# 受控词表 / 规则族 / 问题深化类（§2.9.2–2.9.4 / §2.10.2）——无显式父类，作支撑类
AUX_TOP = [("FormulaType", "公式类型"), ("CollectionMethod", "采集方式"), ("TreatmentType", "整治类型"),
           ("EvaluationRule", "评价规则"), ("ProblemCause", "问题病因"), ("TemporalTrend", "时序趋势"),
           ("ProblemIndicatorMapping", "问题-指标映射")]
# 受控词表实例（owl:oneOf 的成员，同时作为个体）
VOCAB = {
    "FormulaType": ["count", "sum", "avg", "max", "ratio", "ratioPercent", "diff"],
    "CollectionMethod": ["统计年报", "部门填报", "基层填报", "现场调研", "专业检测", "普查数据", "遥感解译", "大数据", "系统对接"],
    "TreatmentType": ["限时解决", "尽力解决"],
}

# 对象属性： uri -> (中文, domain[list], range[list], 特性)
OBJ = {
    "locatedIn": ("位于", ["SpatialUnit", "Land", "Problem"], ["SpatialUnit"], ["Transitive"]),
    "hasPart": ("由…组成", ["SpatialUnit"], ["SpatialUnit"], []),
    "examines": ("针对", ["ExaminationActivity"], ["SpatialUnit"], []),
    "usesIndicator": ("采用指标", ["ExaminationActivity"], ["Indicator"], []),
    "produces": ("产生", ["ExaminationActivity"], ["AssessmentResult"], ["Functional"]),
    "measures": ("度量对象", ["Indicator"], ["SpatialUnit"], []),
    "inDimension": ("指标属于维度", ["Indicator"], ["Dimension"], []),
    "inCategory": ("指标属于分类", ["Indicator"], ["IndicatorCategory"], []),
    "belongsToDimension": ("分类归属维度", ["IndicatorCategory"], ["Dimension"], []),
    "computedFrom": ("由…计算", ["Indicator"], ["__UNION__"], []),
    "feedsInto": ("参与计算", ["__UNION__"], ["Indicator"], []),
    "revealsProblem": ("揭示", ["AssessmentResult"], ["Problem"], []),
    "derivedFrom": ("由…导出", ["Problem"], ["AssessmentResult"], []),
    "proposes": ("提出", ["Problem"], ["RemediationSuggestion"], []),
    "triggers": ("触发（直通兼容）", ["Problem"], ["RenewalProject"], []),
    "leadsTo": ("立项", ["RemediationSuggestion"], ["RenewalProject"], []),
    "assignedTo": ("责任单位", ["RemediationSuggestion"], ["Actor"], []),
    "actsOn": ("作用于", ["RenewalProject", "RemediationSuggestion"], ["RenewalObject", "SpatialUnit"], []),
    "adoptsApproach": ("采用方式", ["RenewalProject"], ["RenewalApproach"], []),
    "implementedBy": ("由…实施", ["RenewalProject"], ["Actor"], []),
    "fundedBy": ("由…出资", ["RenewalProject"], ["Fund"], []),
    "basedOn": ("依据", ["Indicator", "RenewalProject"], ["PolicyStandard"], []),
    "occursIn": ("发生于", ["ExaminationActivity", "RenewalProject"], ["TimePeriod"], []),
    "belongsTo": ("属于", ["DataObject"], ["SpatialUnit"], []),
    "involves": ("涉及", ["NegativeEvent"], ["ProtectedObject", "HistoricalBuilding"], []),
    "physicalCarrier": ("物理载体", ["HistoricalBuilding"], ["SpatialUnit"], []),
    "causedBy": ("病因归因", ["Problem"], ["ProblemCause"], []),
    "hasTrend": ("具有趋势", ["Problem"], ["TemporalTrend"], []),
    "mapsToProblem": ("映射到问题", ["ProblemIndicatorMapping"], ["Problem"], []),
    "mapsToIndicator": ("映射到指标", ["ProblemIndicatorMapping"], ["Indicator"], []),
    "evaluatedBy": ("由…评价", ["Indicator"], ["EvaluationRule"], []),
    "hasFormulaType": ("公式类型", ["Indicator"], ["FormulaType"], []),
    "collectedVia": ("采集方式", ["DataObject"], ["CollectionMethod"], []),
}
OBJ_INVERSE = {"computedFrom": "feedsInto"}

# 数据属性： uri -> (中文, domain[list], xsd 类型)
DATA = {
    "name": ("名称", "__ALL__", "string"), "code": ("编码", ["SpatialUnit", "Indicator", "RenewalProject", "Dimension", "DataObject"], "string"),
    "indicatorValue": ("指标值", ["AssessmentResult"], "decimal"), "unit": ("计量单位", ["Indicator", "AssessmentResult", "DataObject"], "string"),
    "threshold": ("阈值/标准值", ["Indicator"], "decimal"), "grade": ("达标等级", ["AssessmentResult"], "string"),
    "year": ("统计年份", ["ExaminationActivity", "AssessmentResult"], "gYear"),
    "floorArea": ("建筑面积", ["Building", "RenewalObject"], "decimal"), "landArea": ("用地面积", ["Land"], "decimal"),
    "constructionYear": ("建成年代", ["Building"], "gYear"), "investment": ("投资额", ["Fund", "RenewalProject"], "decimal"),
    "duration": ("时序/工期", ["RenewalProject"], "string"), "policyVersion": ("标准版本号", ["PolicyStandard"], "string"),
    "definition": ("口径定义", ["DataObject"], "string"), "collectedAt": ("采集空间层级", ["DataObject"], "string"),
    "dataSource": ("数据来源", ["DataObject"], "string"), "collectionMethod": ("采集/统计方法", ["DataObject"], "string"),
    "formula": ("计算公式", ["Indicator"], "string"), "problemDescription": ("问题描述", ["Problem"], "string"),
    "suggestionText": ("整治建议文本", ["RemediationSuggestion"], "string"), "treatmentType": ("整治类型", ["RemediationSuggestion"], "string"),
    "locationDescription": ("整治区域描述", ["RemediationSuggestion"], "string"),
    "problemCategory": ("问题性质", ["Problem"], "string"), "severity": ("严重程度", ["Problem"], "decimal"),
    "mappingWeight": ("映射权重", ["ProblemIndicatorMapping"], "decimal"), "causeType": ("病因类型", ["ProblemCause"], "string"),
    "trendDirection": ("趋势方向", ["TemporalTrend"], "string"), "referencePeriod": ("参考周期", ["TemporalTrend"], "string"),
    "structureSafetyStatus": ("结构安全状态", ["Building"], "string"), "gasSafetyStatus": ("燃气安全状态", ["Building"], "string"),
    "corridorSafetyStatus": ("楼道安全状态", ["Building"], "string"), "envelopeSafetyStatus": ("围护安全状态", ["Building"], "string"),
    "pipelineStatus": ("管线管道状态", ["Building"], "string"), "agingAdaptationNeed": ("适老化改造需求", ["Building"], "boolean"),
    "energyRetrofitNeed": ("节能改造需求", ["Building"], "boolean"), "digitalRetrofitNeed": ("数字化改造需求", ["Building"], "boolean"),
    "dilapidatedStatus": ("危旧状态", ["Building", "Bridge"], "string"), "wasteSortingStatus": ("生活垃圾分类实施状态", ["ResidentialQuarter"], "boolean"),
    "propertyManagementStatus": ("物业管理实施状态", ["ResidentialQuarter"], "boolean"), "smartRetrofitNeed": ("智慧化改造需求", ["ResidentialQuarter"], "boolean"),
    "complianceStatus": ("配建达标状态", ["ElderlyCareFacility", "InfantCareFacility", "PublicActivityVenue", "MultiFunctionSportsGround", "CulturalActivityCenter"], "string"),
    "configuredStatus": ("配建状态", ["ParkingSpace", "EVChargingPile", "EbikeChargingFacility"], "string"),
    "parkingViolationStatus": ("乱停乱放状态", ["Road"], "boolean"), "renewalNeed": ("改造需求", ["OldBlock", "OldCommercialBlock", "OldResidentialBlock", "OldIndustrialArea"], "boolean"),
    "archiveStatus": ("挂牌建档状态", ["HistoricalBuilding"], "string"), "vacancyStatus": ("空置状态", ["HistoricalBuilding"], "string"),
    "demolishedStatus": ("被擅自拆除状态", ["HistoricBlockBuilding"], "boolean"),
    "renovationStatus": ("改造完成状态", ["GasPipeline", "EmergencyShelter", "UrbanVillage", "Building"], "string"),
    "monitoringStatus": ("监测状态", ["LifelineRiskPoint", "RiskyConstructionWorks"], "string"),
    "smartFireMonitorStatus": ("智能化火灾监测配置状态", ["Building"], "boolean"),
    "remediationStatus": ("整治状态", ["Problem"], "string"), "constructionStage": ("建设阶段", ["Building"], "string"),
    "greenBuildingLevel": ("绿色建筑属性", ["Building"], "string"), "landUseType": ("用地类型", ["Land"], "string"),
    "buildingNature": ("建筑性质", ["Building"], "string"), "floorCount": ("层数", ["Building"], "integer"),
    "orientation": ("指标导向", ["Indicator"], "string"),   # 导出新增【待核】：录入模板 §一 → Indicator 导向属性
}
NO_DRIFT = set()  # 2026-10-10：orientation 已补入 属性与关系.md，无豁免项

XSD_MAP = {"string": XSD.string, "decimal": XSD.decimal, "integer": XSD.integer, "boolean": XSD.boolean, "gYear": XSD.gYear}


def iri(u):
    return UR[u]


# ---------- 防漂移断言（子串存在即可；部分 URI 仅见于 Mermaid 图，无反引号） ----------
miss = []
for u, _ in TOP + AUX_TOP + BASIC_Q:
    if u not in MDC:
        miss.append(("class", u))
for p, lst in SUB.items():
    if lst:
        for u, _ in lst:
            if u not in MDC:
                miss.append(("class", u))
for u in OBJ:
    if u not in MDP:
        miss.append(("objprop", u))
for u in DATA:
    if u not in NO_DRIFT and u not in MDP:
        miss.append(("dataprop", u))
for u in ["HousingDimension", "ResidentialQuarterDimension", "CommunityDimension", "NeighborhoodDimension", "UrbanDistrictDimension"]:
    if u not in MDC:
        miss.append(("dimension", u))
if miss:
    print("!! 防漂移断言失败（源 md 未出现）:")
    for k, u in miss:
        print("   ", k, u)
    raise SystemExit(1)
print("防漂移断言：全部 URI 均见于源 md  ✓")

# ---------- 反向防漂移断言：被引用的类必须已被声明（2026-10-11 新增） ----------
# 教训：上面的断言只查「已声明的 URI 是否见于源 md」，是**单向**的；
# 当 SUB 中出现重复键 `"DataObject": None,` 把 7 个父类挤掉后，无人报错，
# 于是生成了「被 rdfs:subClassOf 引用、却从未声明为 owl:Class」的类。
# 下面把方向反过来查一遍：凡被当作父类、被当作属性定义域/值域引用的类，
# 都必须在脚本里被显式声明，否则直接失败。
declared_cls = {u for u, _ in TOP + AUX_TOP + BASIC_Q} | {"DataObjectRoleUnion"}
for _lst in SUB.values():
    if _lst:
        declared_cls |= {u for u, _ in _lst}

dangling = []
for parent, lst in SUB.items():
    if lst and parent not in declared_cls:
        dangling.append(("SUB 父类未声明", parent))
for p, (_cn, dom, rng, _ch) in OBJ.items():
    for d in list(dom) + list(rng):
        if d != "__UNION__" and d not in declared_cls:
            dangling.append((f"对象属性 {p} 引用未声明类", d))
for p, (_cn, dom, _typ) in DATA.items():
    if dom != "__ALL__":
        for d in dom:
            if d not in declared_cls:
                dangling.append((f"数据属性 {p} 引用未声明类", d))
if dangling:
    print("!! 反向防漂移断言失败（被引用但未声明的类）:")
    for k, u in dangling:
        print("   ", k, u)
    raise SystemExit(1)
print(f"反向防漂移断言：{len(declared_cls)} 个类的引用闭合（无悬挂引用）  ✓")

# ---------- 1. 构建 TTL ----------
g = Graph()
g.bind("ur", UR)
g.bind("owl", OWL)
g.bind("rdfs", RDFS)
g.bind("xsd", XSD)

ont = UR["ontology"]
g.add((ont, RDF.type, OWL.Ontology))
g.add((ont, RDFS.label, Literal("城市体检与更新本体", lang="zh")))
g.add((ont, OWL.versionInfo, Literal("v0.1-export-2026-10-10")))
g.add((ont, RDFS.comment, Literal("由 03-本体模型/_gen_ttl.py 导出；TBox 源 = 类与层级.md / 属性与关系.md；ABox 源 = 04-指标映射/55项指标.yaml。命名空间为占位【待核】。", lang="zh")))


def add_class(u, cn, parent=None):
    g.add((iri(u), RDF.type, OWL.Class))
    g.add((iri(u), RDFS.label, Literal(cn, lang="zh")))
    if parent:
        g.add((iri(u), RDFS.subClassOf, iri(parent)))


for u, cn in TOP + AUX_TOP:
    add_class(u, cn)
for u, cn in BASIC_Q:
    add_class(u, cn, "DataObject")
for parent, lst in SUB.items():
    if not lst:
        continue
    for u, cn in lst:
        add_class(u, cn, parent)

# 对象属性
for u, (cn, dom, rng, chars) in OBJ.items():
    p = iri(u)
    g.add((p, RDF.type, OWL.ObjectProperty))
    g.add((p, RDFS.label, Literal(cn, lang="zh")))
    for d in dom:
        if d == "__UNION__":
            continue
        g.add((p, RDFS.domain, iri(d)))
    for r in rng:
        if r == "__UNION__":
            continue
        g.add((p, RDFS.range, iri(r)))
    if "Transitive" in chars:
        g.add((p, RDF.type, OWL.TransitiveProperty))
    if "Functional" in chars:
        g.add((p, RDF.type, OWL.FunctionalProperty))
# computedFrom/feedsInto 值域 = 角色类并集（owl:unionOf）
union = BNode()
Collection(g, union, [iri("DataObject"), iri("SpatialUnit"), iri("RenewalObject"), iri("Problem"), iri("RenewalProject")])
g.add((UR["DataObjectRoleUnion"], RDF.type, OWL.Class))
g.add((UR["DataObjectRoleUnion"], RDFS.label, Literal("数据对象角色类并集", lang="zh")))
g.add((UR["DataObjectRoleUnion"], OWL.unionOf, union))
g.add((UR.computedFrom, RDFS.range, UR["DataObjectRoleUnion"]))
g.add((UR.feedsInto, RDFS.domain, UR["DataObjectRoleUnion"]))
# 逆属性
g.add((UR.computedFrom, OWL.inverseOf, UR.feedsInto))

# 数据属性
for u, (cn, dom, typ) in DATA.items():
    p = iri(u)
    g.add((p, RDF.type, OWL.DatatypeProperty))
    g.add((p, RDFS.label, Literal(cn, lang="zh")))
    if dom != "__ALL__":
        for d in dom:
            g.add((p, RDFS.domain, iri(d)))
    g.add((p, RDFS.range, XSD_MAP[typ]))

# ABox：维度 / 分类 / 受控词表 个体
DIM_URI = {"住房": "HousingDimension", "小区": "ResidentialQuarterDimension", "社区": "CommunityDimension",
           "街区": "NeighborhoodDimension", "城区": "UrbanDistrictDimension"}
LV_URI = {"住房": "Building", "小区": "ResidentialQuarter", "社区": "Community", "街区": "Neighborhood", "城区": "UrbanDistrict"}

data = yaml.safe_load(open(YAMLP, encoding="utf-8"))
for d in data["dimensions"]:
    u = UR[d["dimension"]]
    g.add((u, RDF.type, UR.Dimension))
    g.add((u, RDFS.label, Literal(d["name"] + "维度", lang="zh")))
for c in data["categories"]:
    u = UR[c["name"]]
    g.add((u, RDF.type, UR.IndicatorCategory))
    g.add((u, RDFS.label, Literal(c["name"], lang="zh")))
    for d in c.get("dimensions", []):
        g.add((u, UR.belongsToDimension, UR[d]))
for vt, vals in VOCAB.items():
    for v in vals:
        u = UR[vt + "_" + v]
        g.add((u, RDF.type, UR[vt]))
        g.add((u, RDFS.label, Literal(v, lang="zh")))

# ABox：政策依据实例（阈值版本绑定用）
pol = UR["Policy_2026_16"]
g.add((pol, RDF.type, UR.PolicyDocument))
g.add((pol, RDFS.label, Literal("建办科〔2026〕16号 附件1《城市体检基础指标体系》", lang="zh")))
g.add((pol, UR.policyVersion, Literal("建办科〔2026〕16号【待核】", lang="zh")))

# ABox：55 个指标实例
for it in data["indicators"]:
    s = UR["Indicator_%d" % it["seq"]]
    g.add((s, RDF.type, UR.Indicator))
    g.add((s, RDFS.label, Literal(it["name"], lang="zh")))
    g.add((s, UR.code, Literal(it["code"])))
    g.add((s, UR.name, Literal(it["name"], lang="zh")))
    g.add((s, UR.unit, Literal(it["unit"], lang="zh")))
    if it["orientation"]:
        g.add((s, UR.orientation, Literal(it["orientation"], lang="zh")))
    g.add((s, UR.measures, UR[it["measures"]]))
    g.add((s, UR.inDimension, UR[it["inDimension"]]))
    if it["inCategory"]:
        g.add((s, UR.inCategory, UR[it["inCategory"]]))
    for o in it["computedFrom"]:
        g.add((s, UR.computedFrom, UR[o]))
        g.add((UR[o], UR.feedsInto, s))
    if it["formula"]:
        g.add((s, UR.formula, Literal(it["formula"], lang="zh")))
    if it["threshold"] and it["threshold"] != "不适用":
        g.add((s, UR.threshold, Literal(it["threshold"], lang="zh")))
    g.add((s, UR.basedOn, pol))
    g.add((s, RDFS.comment, Literal("原始状态：" + it["status"] + "；来源：" + it["basedOn"], lang="zh")))

g.serialize(destination=OUT_TTL, format="turtle")
print("WROTE:", OUT_TTL, "| triples:", len(g))

# ---------- 2. 构建 SHACL ----------
sg = Graph()
sg.bind("sh", SH)
sg.bind("ur", UR)
sg.bind("owl", OWL)

ALLOWED_CF = sorted({o for it in data["indicators"] for o in it["computedFrom"]})


def mk_shape(*, target=None):
    b = BNode()
    if target:
        sg.add((b, RDF.type, SH.NodeShape))
        sg.add((b, SH.targetClass, iri(target)))
    return b


def prop(shape, path, **kw):
    p = BNode()
    sg.add((shape, SH.property, p))
    sg.add((p, SH.path, iri(path)))
    for k, v in kw.items():
        sg.add((p, SH[k], v))
    return p


# S1 Indicator 基本约束
ind = mk_shape(target="Indicator")
lst = BNode(); Collection(sg, lst, [UR[o] for o in ALLOWED_CF])
prop(ind, "computedFrom", minCount=Literal(1), **{"in": lst, "message": Literal("指标须有 ≥1 个数据对象，且取值须在角色类值域内", lang="zh")})
prop(ind, "inCategory", maxCount=Literal(1), message=Literal("指标一级分类 0..1（54、55 无分类）", lang="zh"))
prop(ind, "basedOn", minCount=Literal(1), message=Literal("指标须有依据（basedOn）", lang="zh"))

# S2 measures 与 inDimension 层级匹配（sh:or 五分支撑）
branches = []
for dim, lvl in DIM_URI.items():
    br = BNode()
    p1 = BNode(); sg.add((p1, SH.path, UR.inDimension)); sg.add((p1, SH.hasValue, UR[lvl]))
    p2 = BNode(); sg.add((p2, SH.path, UR.measures)); sg.add((p2, SH.hasValue, UR[LV_URI[dim]]))
    sg.add((br, SH.property, p1)); sg.add((br, SH.property, p2))
    branches.append(br)
orl = BNode(); Collection(sg, orl, branches)
sg.add((ind, SH["or"], orl))
sg.add((ind, SH.message, Literal("measures 须指向其 inDimension 对应的空间层级", lang="zh")))

# S3 多对象指标必带 formula（SPARQL 约束）
sp = BNode()
sg.add((ind, SH.sparql, sp))
sg.add((sp, RDF.type, SH.SPARQLConstraint))
sg.add((sp, SH.message, Literal("computedFrom 指向 ≥2 个数据对象的指标必须带 formula", lang="zh")))
sg.add((sp, SH.select, Literal(
    "SELECT $this WHERE { $this <" + NS + "computedFrom> ?o1, ?o2 . "
    "FILTER(?o1 != ?o2) FILTER NOT EXISTS { $this <" + NS + "formula> ?f } }")))

# S4 PolicyStandard 须带版本号
ps = mk_shape(target="PolicyStandard")
prop(ps, "policyVersion", minCount=Literal(1), message=Literal("政策标准须带 policyVersion（阈值溯源）", lang="zh"))

# S5 小区 locatedIn 社区（1..1，默认从属）
rq = mk_shape(target="ResidentialQuarter")
prop(rq, "locatedIn", minCount=Literal(1), maxCount=Literal(1), **{"class": UR.Community,
     "message": Literal("小区默认 locatedIn 社区（1..1）", lang="zh")})

# S5b IndicatorCategory 须归属 ≥1 个维度（2026-10-10 折中方案）
ic = mk_shape(target="IndicatorCategory")
prop(ic, "belongsToDimension", minCount=Literal(1),
     message=Literal("指标分类须归属 ≥1 个维度（belongsToDimension，允许一对多）", lang="zh"))

# S6 Problem 约束
pb = mk_shape(target="Problem")
prop(pb, "locatedIn", minCount=Literal(1), message=Literal("问题须绑空间单元（locatedIn，不参与传递）", lang="zh"))
prop(pb, "derivedFrom", minCount=Literal(1), maxCount=Literal(1), message=Literal("问题由且仅由一条评估结果导出（derivedFrom 1..1）", lang="zh"))
prop(pb, "severity", minInclusive=Literal(0), maxInclusive=Literal(1), message=Literal("severity ∈ [0,1]（数值化，档位边界【待核】）", lang="zh"))

# S7 阈值版本绑定：带 threshold 的指标须 basedOn（已含 S1）
sg.serialize(destination=OUT_SHACL, format="turtle")
print("WROTE:", OUT_SHACL, "| triples:", len(sg))

# ---------- 3. 示例 SPARQL ----------
PFX = ("PREFIX ur: <" + NS + ">\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
       "PREFIX owl: <http://www.w3.org/2002/07/owl#>\n")
Q = []
Q.append("# 常用查询（示例）—— 城市体检与更新本体\n# 生成：03-本体模型/_gen_ttl.py（2026-10-10）\n# 说明：查询基于 城市体检-更新本体.ttl 的 ABox（55 个 Indicator 实例）。\n")
Q.append(PFX + """
# Q1. 列出全部指标及其维度 / 分类 / 空间层级
SELECT ?seq ?name ?dim ?cat ?level WHERE {
  ?ind a ur:Indicator ; ur:code ?seq ; rdfs:label ?name ;
       ur:inDimension ?dim ; ur:measures ?level .
  OPTIONAL { ?ind ur:inCategory ?cat }
} ORDER BY xsd:integer(?seq)""")
Q.append(PFX + """
# Q2. 反查：某数据对象（如 Building）被哪些指标引用（feedsInto）
SELECT ?ind ?name ?cat WHERE {
  ur:Building ur:feedsInto ?ind .
  ?ind rdfs:label ?name . OPTIONAL { ?ind ur:inCategory ?cat }
} ORDER BY ?name""")
Q.append(PFX + """
# Q3. 按「维度 × 分类」统计指标数
SELECT ?dim (COUNT(?ind) AS ?n) WHERE {
  ?ind a ur:Indicator ; ur:inDimension ?dim .
} GROUP BY ?dim ORDER BY DESC(?n)""")
Q.append(PFX + """
# Q4. 多对象指标（computedFrom ≥2）及其公式
SELECT ?ind ?name ?formula (COUNT(DISTINCT ?o) AS ?n) WHERE {
  ?ind a ur:Indicator ; ur:computedFrom ?o ; rdfs:label ?name .
  OPTIONAL { ?ind ur:formula ?formula }
} GROUP BY ?ind ?name ?formula HAVING (COUNT(DISTINCT ?o) >= 2)""")
Q.append(PFX + """
# Q5. 主干闭环回溯：问题 → 整治建议 → 更新项目（含直通兼容路径）
SELECT ?problem ?sug ?proj WHERE {
  { ?problem a ur:Problem ; ur:proposes ?sug . OPTIONAL { ?sug ur:leadsTo ?proj } }
  UNION
  { ?problem a ur:Problem ; ur:triggers ?proj }  # 直通兼容路径
}""")
Q.append(PFX + """
# Q6. 带阈值的指标及其依据版本（校验 threshold 绑定）
SELECT ?ind ?name ?threshold ?pv WHERE {
  ?ind a ur:Indicator ; ur:threshold ?threshold ; ur:basedOn ?pol ; rdfs:label ?name .
  ?pol ur:policyVersion ?pv
}""")

with open(OUT_SPARQL, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n\n".join(Q) + "\n")
print("WROTE:", OUT_SPARQL)
print("DONE.")
