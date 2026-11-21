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
from pathlib import Path
import os
import itertools
from rdflib import Graph, Namespace, BNode, Literal, RDF, RDFS, OWL, XSD
from rdflib.namespace import SH
from rdflib.collection import Collection
import yaml

BASE = str(Path(__file__).resolve().parent.parent)
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
# 顶层类（类与层级.md §一，17 个）
TOP = [
    ("SpatialUnit", "空间单元"), ("Dimension", "指标维度"), ("IndicatorCategory", "指标分类"),
    ("Indicator", "体检指标"), ("DataObject", "数据对象"), ("ExaminationActivity", "体检活动"),
    ("AssessmentResult", "评估结果"), ("IndicatorJudgement", "指标判断"),
    ("Problem", "问题短板"), ("RemediationSuggestion", "整治建议"),
    ("RenewalObject", "更新对象"), ("RenewalProject", "更新项目"), ("RenewalApproach", "更新方式"),
    ("Actor", "行动主体"), ("Fund", "资金"), ("PolicyStandard", "政策标准"), ("TimePeriod", "时间周期"),
]
# 子类： parent -> [(uri, 中文名), ...]（来源见各小节）
SUB = {
    "SpatialUnit": [("Building", "建筑（楼栋）"), ("ResidentialQuarter", "小区"), ("Community", "社区"),
                    ("Neighborhood", "街区"), ("UrbanDistrict", "城区（城市）")],                      # §2.1
    "AssessmentResult": [("ExtremeValueAssessmentResult", "极值/周期评估结果"),
                         ("WeightedAssessmentResult", "加权/复合评估结果"),
                         # W-B01（2026-11-17 批复）：按**等级**分类的第二组子类（与前两者按算法分类正交，非互斥非完备）
                         ("CompliantResult", "达标结果"), ("BasicCompliantResult", "基本达标结果"),
                         ("NonCompliantResult", "不达标结果")],  # §2.12 R5/R6 + W-B01
    # W-B01（2026-11-17 批复 Q12=③）：Problem 按维度一等分型；severity 保留为属性不做子类
    "Problem": [("HousingProblem", "住房问题"), ("QuarterProblem", "小区/社区问题"),
                ("NeighborhoodProblem", "街区问题"), ("UrbanDistrictProblem", "城区问题")],
    # W-B01（2026-11-17 批复）：建议二分结构；判定规则【待核】留 W-B02
    "RemediationSuggestion": [("TimeLimitedRemedy", "限时解决类整治建议"),
                              ("BestEffortRemedy", "尽力解决类整治建议")],
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
    # W-B01b（2026-11-19 甲-精简版）：删 WarningRule/AssessmentRule/CrossDomainRule 三个空壳类，
    # 职责并入唯一 EvaluationRule；算法/输出改受控词表（见 VOCAB），档位改 RatingBand 实例。
    # EvaluationRule 不再有子类（SUB 中移除该键）。
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
           ("ProblemIndicatorMapping", "问题-指标映射"), ("CheckItem", "核查项"),
           # 2026-11-19 评价规则重构（甲-精简版）
           ("EvaluationMethod", "评价方法"), ("EvaluationOutput", "评价输出"),
           ("EvaluationReference", "评价参考值"), ("RatingBand", "评价档位"),
           ("DerivedRatio", "派生比值"),
           # 2026-11-20 分尺度评级（独立词表 A，大王 D1–D4 全批）
           ("SpatialScale", "空间尺度")]
# 受控词表实例（owl:oneOf 的成员，同时作为个体）
VOCAB = {
    "FormulaType": ["count", "sum", "avg", "max", "ratio", "ratioPercent", "diff"],
    "CollectionMethod": ["统计年报", "部门填报", "基层填报", "现场调研", "专业检测", "普查数据", "遥感解译", "大数据", "系统对接"],
    "TreatmentType": ["限时解决", "尽力解决"],
    # 2026-11-19 评价规则重构：算法/输出维度词表（未来加方式只加成员，不动类/属性）
    "EvaluationMethod": ["直接比较", "占比化", "均值化", "跨域组合"],
    "EvaluationOutput": ["四级等级", "二元预警"],
    # 2026-11-20 分尺度评级：英文 URI + 中文 label（D1 批复）
    "SpatialScale": [("BuildingScale", "建筑尺度"), ("QuarterScale", "小区尺度"),
                     ("CommunityScale", "社区尺度"), ("NeighborhoodScale", "街道尺度"),
                     ("DistrictScale", "城区尺度")],
}

# 对象属性： uri -> (中文, domain[list], range[list], 特性)
OBJ = {
    "locatedIn": ("位于", ["SpatialUnit", "Land", "Problem"], ["SpatialUnit"], ["Transitive"]),
    "hasPart": ("由…组成", ["SpatialUnit"], ["SpatialUnit"], []),
    "examines": ("针对", ["ExaminationActivity"], ["SpatialUnit"], []),
    "usesIndicator": ("采用指标", ["ExaminationActivity"], ["Indicator"], []),
    "produces": ("产生", ["ExaminationActivity"], ["AssessmentResult"], ["Functional"]),
    "assesses": ("评估", ["AssessmentResult", "IndicatorJudgement"], ["SpatialUnit"], []),
    "aggregatedFrom": ("聚合自", ["AssessmentResult"], ["IndicatorJudgement"], []),
    "basedOnEvidence": ("证据", ["IndicatorJudgement"], ["FacilityObject", "SpaceObject"], []),
    "ofIndicator": ("针对指标", ["AssessmentResult", "IndicatorJudgement"], ["Indicator"], []),
    "failsCheckItem": ("核查项未通过", ["Building", "RenewalObject"], ["CheckItem"], []),
    "checkItemFor": ("核查项适用指标", ["CheckItem"], ["Indicator"], []),
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
    "basedOn": ("依据", ["Indicator", "RenewalProject", "CheckItem"], ["PolicyStandard"], []),
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
    # 2026-11-19 评价规则重构（甲-精简版）
    "evaluates": ("评价…指标", ["EvaluationRule"], ["Indicator"], []),
    "evaluationMethod": ("采用评价方法", ["EvaluationRule"], ["EvaluationMethod"], []),
    "evaluationOutput": ("评价输出类型", ["EvaluationRule"], ["EvaluationOutput"], []),
    "usesReference": ("使用参考值", ["EvaluationRule"], ["EvaluationReference"], []),
    "forIndicator": ("针对指标", ["EvaluationReference"], ["Indicator"], []),
    "hasRatingBand": ("具有档位", ["EvaluationReference"], ["RatingBand"], []),
    # 2026-11-20 分尺度评级：参考值适用的空间层级
    "appliesToScale": ("适用空间尺度", ["EvaluationReference"], ["SpatialScale"], []),
    "reusesBandsOf": ("档次复用于", ["EvaluationReference"], ["EvaluationReference"], []),
}
OBJ_INVERSE = {"computedFrom": "feedsInto"}

# 数据属性： uri -> (中文, domain[list], xsd 类型)
DATA = {
    "name": ("名称", "__ALL__", "string"), "code": ("编码", ["SpatialUnit", "Indicator", "RenewalProject", "Dimension", "DataObject"], "string"),
    "indicatorValue": ("指标值", ["AssessmentResult"], "decimal"), "unit": ("计量单位", ["Indicator", "AssessmentResult", "DataObject"], "string"),
    "threshold": ("阈值/标准值", ["Indicator"], "decimal"), "grade": ("达标等级", ["AssessmentResult"], "string"),
    "year": ("统计年份", ["ExaminationActivity", "AssessmentResult"], "gYear"),
    "floorArea": ("建筑面积", ["Building", "RenewalObject"], "decimal"), "landArea": ("用地面积", ["Land"], "decimal"),
    "constructionYear": ("建成年代", ["Building", "ResidentialQuarter", "PublicActivityVenue"], "gYear"), "investment": ("投资额", ["Fund", "RenewalProject"], "decimal"),
    "duration": ("时序/工期", ["RenewalProject"], "string"), "policyVersion": ("标准版本号", ["PolicyStandard"], "string"),
    "definition": ("口径定义", ["DataObject"], "string"), "collectedAt": ("采集空间层级", ["DataObject"], "string"),
    "dataSource": ("数据来源", ["DataObject"], "string"), "collectionMethod": ("采集/统计方法", ["DataObject"], "string"),
    "formula": ("计算公式", ["Indicator"], "string"), "problemDescription": ("问题描述", ["Problem"], "string"),
    "suggestionText": ("整治建议文本", ["RemediationSuggestion"], "string"), "treatmentType": ("整治类型", ["RemediationSuggestion"], "string"),
    "locationDescription": ("整治区域描述", ["RemediationSuggestion"], "string"),
    # 2026-11-19 评价规则重构（甲-精简版）
    "referenceValue": ("参考值", ["EvaluationReference"], "decimal"),
    "validPeriod": ("适用时期", ["EvaluationReference"], "string"),
    "sourceScope": ("来源口径", ["EvaluationReference"], "string"),
    "direction": ("方向", ["EvaluationReference"], "string"),
    "bandLabel": ("档位名", ["RatingBand"], "string"),
    "bandLower": ("档位下界", ["RatingBand"], "decimal"),
    "bandUpper": ("档位上界", ["RatingBand"], "decimal"),
    "includeLower": ("含下界", ["RatingBand"], "boolean"),
    "includeUpper": ("含上界", ["RatingBand"], "boolean"),
    "ratioValue": ("比值", ["DerivedRatio"], "decimal"),
    "ratioOf": ("比值口径", ["DerivedRatio"], "string"),
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
    # ---- 2026-11-08 实例数据接入属性（属性与关系.md §2.2，保留 29 项） ----
    "areaKm2": ("面积（平方千米）", ["SpatialUnit"], "decimal"),
    "residentPopulation": ("常住人口", ["SpatialUnit"], "integer"),
    "householdCount": ("户数", ["SpatialUnit"], "integer"),
    "unitCount": ("单元数量", ["Building"], "integer"),
    "elderlyPopulation": ("老年人口", ["SpatialUnit"], "integer"),
    "rqType": ("小区类型", ["ResidentialQuarter"], "string"),
    "buildingCount": ("建筑数量", ["ResidentialQuarter"], "integer"),
    "totalFloorArea": ("总建筑面积", ["ResidentialQuarter"], "decimal"),
    "housingUnitCount": ("住宅套数", ["ResidentialQuarter"], "integer"),
    "parkingDemand": ("停车位需求", ["ResidentialQuarter", "Community"], "integer"),
    "parkingSupply": ("停车位供给", ["ResidentialQuarter", "Community"], "integer"),
    "evChargerDemand": ("充电桩需求", ["ResidentialQuarter"], "integer"),
    "evChargerSupply": ("充电桩供给", ["ResidentialQuarter"], "integer"),
    "ebikeFacilityBuilt": ("配建电动自行车设施", ["ResidentialQuarter"], "boolean"),
    "ebikeFacilityCount": ("电动自行车设施数量", ["ResidentialQuarter"], "integer"),
    "publicVenueBuilt": ("配建公共活动场地", ["ResidentialQuarter"], "boolean"),
    "publicVenueArea": ("公共活动场地面积", ["ResidentialQuarter"], "decimal"),
    "publicGreenBuilt": ("配建公共绿地", ["ResidentialQuarter"], "boolean"),
    "publicGreenArea": ("公共绿地面积", ["ResidentialQuarter"], "decimal"),
    "nonCompliantWalkwayLength": ("不达标步行道长度", ["ResidentialQuarter"], "decimal"),
    "wasteSortingStationCount": ("垃圾分类点数量", ["ResidentialQuarter"], "integer"),
    "smartParcelLocker": ("智能信包箱", ["ResidentialQuarter"], "boolean"),
    "smartSecurity": ("智能安防", ["ResidentialQuarter"], "boolean"),
    "rqCount": ("小区数量", ["Community"], "integer"),
    "carOwnership": ("小汽车拥有量", ["Community"], "integer"),
    "evCount": ("新能源汽车数量", ["Community"], "integer"),
    "communityCount": ("社区数量", ["Neighborhood"], "integer"),
    "enterpriseCount": ("企业数量", ["Neighborhood"], "integer"),
    "employmentCount": ("就业人数", ["Neighborhood"], "integer"),
    # ---- 2026-11-08 指标判断层（属性与关系.md §2.3） ----
    "judgementValue": ("指标判断值", ["IndicatorJudgement"], "string"),
    "facilityArea": ("设施占地面积", ["FacilityObject", "SpaceObject"], "decimal"),
    "checkItemType": ("核查项判定类型", ["CheckItem"], "string"),
    "checkItemThreshold": ("核查项阈值", ["CheckItem"], "string"),
    "checkItemUnit": ("核查项单位", ["CheckItem"], "string"),
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
g.add((ont, OWL.versionInfo, Literal("v0.2-export-2026-11-08")))
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

def add_union_class(key, members, label):
    """多定义域/多值域属性：生成 owl:unionOf 并集类，避免 RDFS 推理的类型爆炸。

    教训（2026-11-08）：若直接写多条 rdfs:domain，RDFS 语义是「交」——
    `Indicator_1 ur:unit ?x`，而 unit 的 domain 含 {Indicator, AssessmentResult, DataObject}，
    推理器会把 Indicator_1 同时判为 AssessmentResult 的实例，导致 SHACL 的
    sh:targetClass 全线错位（评估结果的约束打到了指标上）。改用 owl:unionOf 后，
    实例只会被推成「并集类」的成员，不再污染具体类。
    """
    u = UR["Union_" + key]
    g.add((u, RDF.type, OWL.Class))
    g.add((u, RDFS.label, Literal(label + "·定义域/值域并集", lang="zh")))
    b = BNode()
    Collection(g, b, [iri(m) for m in members])
    g.add((u, OWL.unionOf, b))
    return u


# 对象属性
for u, (cn, dom, rng, chars) in OBJ.items():
    p = iri(u)
    g.add((p, RDF.type, OWL.ObjectProperty))
    g.add((p, RDFS.label, Literal(cn, lang="zh")))
    ds = [d for d in dom if d != "__UNION__"]
    if len(ds) == 1:
        g.add((p, RDFS.domain, iri(ds[0])))
    elif len(ds) > 1:
        g.add((p, RDFS.domain, add_union_class(u + "_dom", ds, cn)))
    rs = [r for r in rng if r != "__UNION__"]
    if len(rs) == 1:
        g.add((p, RDFS.range, iri(rs[0])))
    elif len(rs) > 1:
        g.add((p, RDFS.range, add_union_class(u + "_rng", rs, cn)))
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
        if len(dom) == 1:
            g.add((p, RDFS.domain, iri(dom[0])))
        elif len(dom) > 1:
            g.add((p, RDFS.domain, add_union_class(u + "_dom", dom, cn)))
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
        # 2026-11-20：成员可为 str（URI后缀=label，向后兼容）或 (英文URI名, 中文label) 元组
        if isinstance(v, tuple):
            vname, vlabel = v
        else:
            vname, vlabel = v, v
        u = UR[vt + "_" + vname]
        g.add((u, RDF.type, UR[vt]))
        g.add((u, RDFS.label, Literal(vlabel, lang="zh")))

# ABox：核查项 CheckItem（57 个，2026-11-08）
# 结构：(前缀, 指标序号, [(子项号, 中文名, 判定类型, 阈值, 单位), ...])
# 住房按 2026 编号：1 结构 / 2 燃气 / 3 楼道 / 4 围护 / 5 管线 / 6 适老化 / 7 节能 / 8 数字化
CI_GROUPS = [
    ("H1", 1, [
        ("1", "混凝土结构构件裂缝（承重墙体/楼板/结构梁）", "是否型", "", ""),
        ("2", "违规拆除结构承重构件", "是否型", "", ""),
        ("3", "砖混结构主体砖体缺棱掉角、砂浆饱满度差", "是否型", "", ""),
        ("4", "违规拆除外窗窗下墙体加建阳台", "是否型", "", ""),
    ]),
    ("H2", 2, [
        ("1", "燃气立管/引入管/水平管锈蚀泄漏", "是否型", "", ""),
        ("2", "户内燃气橡胶软管硬化老化", "是否型", "", ""),
        ("3", "私改私接燃气管道", "是否型", "", ""),
    ]),
    ("H3", 3, [
        ("1", "楼梯踏步缺损松动", "是否型", "", ""),
        ("2", "通风井道、排风烟道堵塞", "是否型", "", ""),
        ("3", "消防门缺失损坏或无法关闭", "是否型", "", ""),
        ("4", "高层住宅消火栓无日常维护", "是否型", "", ""),
        ("5", "灭火器缺失或未设置", "是否型", "", ""),
        ("6", "消防安全出口指示灯损坏", "是否型", "", ""),
        ("7", "占用消防楼梯或楼道", "是否型", "", ""),
        ("8", "公共楼道停放自行车电动车", "是否型", "", ""),
    ]),
    ("H4", 4, [
        ("1", "外墙装饰与保温材料开裂脱落", "是否型", "", ""),
        ("2", "外墙悬挂设施不规范", "是否型", "", ""),
        ("3", "门窗玻璃破损脱落", "是否型", "", ""),
        ("4", "屋面排水不畅或漏水", "是否型", "", ""),
        ("5", "外墙内侧或地下室渗水漏水", "是否型", "", ""),
    ]),
    ("H5", 5, [
        ("1", "给水管线跑冒滴漏", "是否型", "", ""),
        ("2", "采暖季室温不达标", "是否型", "", ""),
        ("3", "电力电信管线老化破损", "是否型", "", ""),
    ]),
    ("H6", 6, [
        ("1", "建成时未安装电梯的多层住宅", "是否型", "", ""),
        ("2", "单元出入口与通道未适老化改造", "是否型", "", ""),
        ("3", "楼梯间未沿墙加装扶手", "是否型", "", ""),
        ("4", "特殊困难老年人家庭未适老化改造", "是否型", "", ""),
    ]),
    ("H7", 7, [
        ("1", "具备节能改造价值但尚未改造", "是否型", "", ""),
    ]),
    ("H8", 8, [
        ("1", "不具备光纤入户条件", "是否型", "", ""),
        ("2", "公共空间未安装楼宇门禁", "是否型", "", ""),
        ("3", "高层楼梯间或走道未覆盖", "是否型", "", ""),
        ("4", "未安装家庭健康紧急呼叫系统", "是否型", "", ""),
    ]),
    ("C", 24, [
        ("1", "业态聚集（核心功能区占比与单一业态占比）", "阈值型", "核心功能区空间占比≥60%；单一功能业态占比≤70%（按经营面积计）", "%"),
        ("2", "步行环境（慢行系统与步道宽度）", "阈值型", "步道宽度≥1.5；慢行系统与无障碍按 3 个必查点全满足", "m"),
        ("3", "交通出行（站点与停靠点距离）", "阈值型", "500 m 内有地铁站或公交站；100 m 内有出租车与非机动车停靠点", "m"),
        ("4", "公共空间（休憩空间密度）", "阈值型", "每 50 m 1 处休憩空间及设施", "m"),
        ("5", "商业特色（历史记忆与民族文化景观）", "是否型", "有≥1 处体现历史/民族/文化的景观或设施（建议口径·待核）", ""),
        ("6", "运营服务（无线网络覆盖）", "是否型", "街区公共区域 100% 覆盖（建议口径·待核）", ""),
    ]),
    ("F", 25, [
        ("1", "上位规划（用地合规）", "是否型", "以片区控规/上位规划为准，符合用地要求（判据建议·待核）", ""),
        ("2", "房屋设施利用（房屋与市政设施老化）", "是否型", "房屋或市政设施需修缮即视为老化（建议口径·待核）", ""),
        ("3", "空间利用（工业仓储建筑空置率）", "比率型", "空置率≥30%（建议值·待核）", "%"),
        ("4", "低效情况（工业仓储用地容积率）", "比率型", "容积率<0.6（建议值·待核）", ""),
        ("5", "空间特色（厂区环境特色）", "是否型", "有≥1 处体现厂区空间特色的要素（建议口径·待核）", ""),
        ("6", "经济产出（工业仓储用地单位产出）", "比率型", "低于地方产业用地标准（标准值待核·建议以万元/亩计）", "万元/亩"),
        ("7", "产业业态合规（禁止类淘汰类或导向不符）", "是否型", "属国家产业政策禁止类/淘汰类，或与片区产业导向不符即不通过（目录版本待核）", ""),
        ("8", "产业业态结构（经营性业态占比）", "比率型", "阈值按地方口径（建议值·待核）", "%"),
        ("9", "运营管理（物业管理组织体系）", "是否型", "有完备的物业管理组织体系", ""),
        ("10", "运营管理（专业运营管理团队）", "是否型", "有专业的运营管理团队", ""),
    ]),
    ("L", 26, [
        ("1", "闲置空间资源（低效闲置地块面积）", "阈值型", "低效闲置地块面积≥1000（建议值·待核）", "㎡"),
        ("2", "闲置空间资源（低效闲置老旧建筑数量与产权）", "阈值型", "低效闲置老旧建筑≥1 处（建议值·待核），并明确产权及经营权", "处"),
        ("3", "服务设施（A 类用地与建筑面积/千人）", "阈值型", "A 类用地 1250–2360 ㎡/千人；建筑面积 1130–1380 ㎡/千人（按常住人口、取区间下限）", "㎡/千人"),
        ("4", "服务设施（人均公共绿地与公共活动空间）", "阈值型", "人均公共绿地≥2.0 ㎡/人；并满足完整居住社区“公共活动空间充足”（原 L4 与 L9 合并）", "㎡/人"),
        ("5", "基础设施配置（设施配置与独立用地）", "是否型", "满足“居住区配套设施”设施配置与独立用地标准（标准号待核）", ""),
        ("6", "人口活力（迁入迁出比例）", "比率型", "净迁出率>5% 视为活力不足（建议值·待核）", "%"),
        ("7", "人口活力（新市民与青年人占比）", "比率型", "新市民与青年人占比<20% 视为结构失衡（建议值·待核）", "%"),
        ("8", "便民商业（便民商业服务设施健全）", "是否型", "满足“便民商业服务设施健全”标准（出处待核）", ""),
    ]),
]
_ci_n = 0
for pref, seq, items in CI_GROUPS:
    for sub, cn, typ, thr, unit in items:
        u = UR["CI_%s_%s" % (pref, sub)]
        g.add((u, RDF.type, UR.CheckItem))
        g.add((u, RDFS.label, Literal(cn, lang="zh")))
        g.add((u, UR.checkItemType, Literal(typ, lang="zh")))
        g.add((u, UR.checkItemFor, UR["Indicator_%d" % seq]))
        if thr:
            g.add((u, UR.checkItemThreshold, Literal(thr, lang="zh")))
        if unit:
            g.add((u, UR.checkItemUnit, Literal(unit, lang="zh")))
        g.add((u, UR.basedOn, UR["Policy_2026_16"]))
        _ci_n += 1
print("核查项 CheckItem:", _ci_n)

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

# 确定性 blank node（2026-10-12 修）：
# rdflib 的 BNode() 默认取随机 uuid 作节点 id，导致同一张图每次序列化出的
# 三元组顺序都不同 —— shacl 产物会反复变动、diff 全是噪音，无法判断真实改动。
# 这里改用固定 id 计数器，并自建 rdf:List（rdflib.Collection 内部同样用随机 BNode）。
_bn = itertools.count()


def BN():
    return BNode("b%d" % next(_bn))


def mlist(items):
    prev = RDF.nil
    for it in reversed(list(items)):
        node = BN()
        sg.add((node, RDF.first, it))
        sg.add((node, RDF.rest, prev))
        prev = node
    return prev


def mk_shape(*, target=None):
    b = BN()
    if target:
        sg.add((b, RDF.type, SH.NodeShape))
        sg.add((b, SH.targetClass, iri(target)))
    return b


def prop(shape, path, **kw):
    p = BN()
    sg.add((shape, SH.property, p))
    sg.add((p, SH.path, iri(path)))
    for k, v in kw.items():
        sg.add((p, SH[k], v))
    return p


# S1 Indicator 基本约束
ind = mk_shape(target="Indicator")
lst = mlist([UR[o] for o in ALLOWED_CF])
prop(ind, "computedFrom", minCount=Literal(1), **{"in": lst, "message": Literal("指标须有 ≥1 个数据对象，且取值须在角色类值域内", lang="zh")})
prop(ind, "inCategory", maxCount=Literal(1), message=Literal("指标一级分类 0..1（54、55 无分类）", lang="zh"))
prop(ind, "basedOn", minCount=Literal(1), message=Literal("指标须有依据（basedOn）", lang="zh"))

# S2 measures 与 inDimension 层级匹配（sh:or 五分支撑）
branches = []
for dim, lvl in DIM_URI.items():
    br = BN()
    p1 = BN(); sg.add((p1, SH.path, UR.inDimension)); sg.add((p1, SH.hasValue, UR[lvl]))
    p2 = BN(); sg.add((p2, SH.path, UR.measures)); sg.add((p2, SH.hasValue, UR[LV_URI[dim]]))
    sg.add((br, SH.property, p1)); sg.add((br, SH.property, p2))
    branches.append(br)
orl = mlist(branches)
sg.add((ind, SH["or"], orl))
sg.add((ind, SH.message, Literal("measures 须指向其 inDimension 对应的空间层级", lang="zh")))

# S3 多对象指标必带 formula（SPARQL 约束）
sp = BN()
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

# ---------- S8–S11 指标判断层（2026-11-08，指标 14 拆解驱动） ----------
JV = ["未配建", "配建不达标", "达标"]
ij = mk_shape(target="IndicatorJudgement")
lst_jv = mlist([Literal(v, lang="zh") for v in JV])
prop(ij, "judgementValue", minCount=Literal(1), maxCount=Literal(1),
     **{"in": lst_jv, "message": Literal("判断值取 未配建 / 配建不达标 / 达标（三值，不可合并）", lang="zh")})
prop(ij, "assesses", minCount=Literal(1), maxCount=Literal(1), **{"class": UR.SpatialUnit,
     "message": Literal("指标判断须绑定恰好 1 个空间单元", lang="zh")})
prop(ij, "ofIndicator", minCount=Literal(1), maxCount=Literal(1), **{"class": UR.Indicator,
     "message": Literal("指标判断须指明针对哪个指标（ofIndicator 1..1）", lang="zh")})

# S9 判断唯一性：(指标, 空间单元) 不重复
sp_u = BN()
sg.add((ij, SH.sparql, sp_u))
sg.add((sp_u, RDF.type, SH.SPARQLConstraint))
sg.add((sp_u, SH.message, Literal("同一指标在同一空间单元上不得有重复判断", lang="zh")))
sg.add((sp_u, SH.select, Literal(
    "SELECT $this ?other WHERE { $this <" + NS + "ofIndicator> ?i ; <" + NS + "assesses> ?u . "
    "?other <" + NS + "ofIndicator> ?i ; <" + NS + "assesses> ?u . FILTER(?other != $this) }")))

# S10 证据基数：未配建=0 条证据；达标/配建不达标 ≥1 条
sp_e = BN()
sg.add((ij, SH.sparql, sp_e))
sg.add((sp_e, RDF.type, SH.SPARQLConstraint))
sg.add((sp_e, SH.message, Literal("未配建→无证据；达标/配建不达标→至少 1 条证据", lang="zh")))
sg.add((sp_e, SH.select, Literal(
    "SELECT $this WHERE { $this <" + NS + "judgementValue> ?j . "
    "OPTIONAL { $this <" + NS + "basedOnEvidence> ?e } "
    "FILTER( (STR(?j) = \"未配建\" && BOUND(?e)) || (STR(?j) != \"未配建\" && !BOUND(?e)) ) }")))

# S11 聚合一致：结果值 = 该单元下「判断≠达标」的条数
ar = mk_shape(target="AssessmentResult")
prop(ar, "ofIndicator", minCount=Literal(1), maxCount=Literal(1),
     message=Literal("评估结果须指明针对哪个指标（ofIndicator 1..1）", lang="zh"))
sp_a = BN()
sg.add((ar, SH.sparql, sp_a))
sg.add((sp_a, RDF.type, SH.SPARQLConstraint))
sg.add((sp_a, SH.message, Literal("评估结果值须等于其单元范围内「判断≠达标」的条数", lang="zh")))
sg.add((sp_a, SH.select, Literal(
    "SELECT $this ?v ?expected WHERE { "
    "$this <" + NS + "ofIndicator> ?ind ; <" + NS + "assesses> ?ud ; <" + NS + "indicatorValue> ?v . "
    "?anyj a <" + NS + "IndicatorJudgement> ; <" + NS + "ofIndicator> ?ind . "
    "{ SELECT $this (COUNT(DISTINCT ?ij) AS ?expected) WHERE { "
    "$this <" + NS + "ofIndicator> ?ind2 ; <" + NS + "assesses> ?ud2 . "
    "OPTIONAL { ?ij <" + NS + "ofIndicator> ?ind2 ; <" + NS + "judgementValue> ?jv ; <" + NS + "assesses> ?cm . "
    "FILTER(STR(?jv) != \"达标\") ?cm <" + NS + "locatedIn>+ ?ud2 } } GROUP BY $this } "
    "FILTER(STR(?v) != STR(?expected)) }")))

# S11b R5 极值/周期评估结果（2026-11-09 新增）
ev = mk_shape(target="ExtremeValueAssessmentResult")
prop(ev, "ofIndicator", minCount=Literal(1), maxCount=Literal(1),
     message=Literal("极值/周期评估结果须指明针对哪个指标（ofIndicator 1..1）", lang="zh"))
prop(ev, "assesses", minCount=Literal(1), maxCount=Literal(1), **{"class": UR.SpatialUnit,
     "message": Literal("极值/周期评估结果须落到具体空间单元（assesses 1..1）", lang="zh")})
prop(ev, "indicatorValue", minCount=Literal(1),
     message=Literal("极值/周期评估结果须有指标值（数值型，极值取自观测）", lang="zh"))

# S11c R6 加权/复合评估结果（2026-11-09 新增）
wr = mk_shape(target="WeightedAssessmentResult")
prop(wr, "ofIndicator", minCount=Literal(1), maxCount=Literal(1),
     message=Literal("加权/复合评估结果须指明针对哪个指标（ofIndicator 1..1）", lang="zh"))
prop(wr, "assesses", minCount=Literal(1), maxCount=Literal(1), **{"class": UR.SpatialUnit,
     "message": Literal("加权/复合评估结果须落到具体空间单元（assesses 1..1）", lang="zh")})
prop(wr, "indicatorValue", minCount=Literal(1),
     message=Literal("加权/复合评估结果须有指标值（数值型，加权汇总）", lang="zh"))

# S12 设施面积非负（SpaceObject / FacilityObject 共用）
fa = BN()
sg.add((fa, RDF.type, SH.NodeShape))
sg.add((fa, SH.targetClass, UR.SpaceObject))
sg.add((fa, SH.targetClass, UR.FacilityObject))
prop(fa, "facilityArea", minInclusive=Literal(0),
     message=Literal("设施占地面积须 ≥ 0（单位 ㎡）", lang="zh"))

# S13 核查项必备三要素（2026-11-08）
ci = mk_shape(target="CheckItem")
prop(ci, "checkItemType", minCount=Literal(1),
     message=Literal("核查项须标判定类型（是否型/阈值型/比率型）", lang="zh"))
prop(ci, "checkItemFor", minCount=Literal(1), maxCount=Literal(1), **{"class": UR.Indicator,
     "message": Literal("核查项须指明服务哪个指标（checkItemFor 1..1）", lang="zh")})

# S8 分尺度评级：参考值须声明适用空间尺度（2026-11-20）
refsh = mk_shape(target="EvaluationReference")
prop(refsh, "appliesToScale", minCount=Literal(1), maxCount=Literal(1),
     **{"class": UR.SpatialScale,  # sh:class：取值须为 SpatialScale 实例（词表类无 owl:oneOf，不能用 sh:in）
        "message": Literal("评价参考值须声明适用空间尺度（1..1，取自 SpatialScale）", lang="zh")})

# S9 整治类型二者择一（2026-11-20 大王拍板：限时解决/尽力解决互斥，不可多选）
rs_shape = mk_shape(target="RemediationSuggestion")
lst_tt = mlist([Literal(v, lang="zh") for v in ("限时解决", "尽力解决")])
# 注：不设 minCount——现有25条建议实例均无此字段（地方实操字段可选）；
#     只约束"若标则唯一且合法"，既落实互斥又不破坏既有数据。
prop(rs_shape, "treatmentType", maxCount=Literal(1),
     **{"in": lst_tt, "message": Literal("整治类型若标，须在 限时解决/尽力解决 中二选一、互斥（大王2026-11-20定）", lang="zh")})

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

Q.append(PFX + """
# Q7. 指标判断分布（2026-11-08 新增）：按「指标 × 判断值」统计单元数
SELECT ?ind ?name ?jv (COUNT(?ij) AS ?n) WHERE {
  ?ij a ur:IndicatorJudgement ; ur:ofIndicator ?ind ; ur:judgementValue ?jv .
  ?ind rdfs:label ?name
} GROUP BY ?ind ?name ?jv ORDER BY ?name ?jv""")
Q.append(PFX + """
# Q8. 聚合对账（2026-11-08 新增）：评估结果值 vs 「判断≠达标」条数，不一致的列出
SELECT ?ar ?name ?unit ?value ?expected WHERE {
  ?ar a ur:AssessmentResult ; ur:ofIndicator ?ind ; ur:assesses ?unit ; ur:indicatorValue ?value .
  ?ind rdfs:label ?name .
  { SELECT ?ind ?unit (COUNT(?ij) AS ?expected) WHERE {
      ?ij a ur:IndicatorJudgement ; ur:ofIndicator ?ind ; ur:judgementValue ?jv ; ur:assesses ?cm .
      FILTER(STR(?jv) != "达标") ?cm ur:locatedIn+ ?unit
    } GROUP BY ?ind ?unit }
  FILTER(STR(?value) != STR(?expected))
} ORDER BY ?name""")

with open(OUT_SPARQL, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n\n".join(Q) + "\n")
print("WROTE:", OUT_SPARQL)
print("DONE.")
