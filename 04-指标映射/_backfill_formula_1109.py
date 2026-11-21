# -*- coding: utf-8 -*-
"""
回填《指标公式展开表-v1.md》§一 城区 29 项（27-55）的口径与来源。
新增 4 列：统计范围(F1) | 时间基准(F2) | 数据来源(F8) | 依据/阈值(F9)。
批注裁定（大王 2026-11-09）已落：32/33 统计范围→建成区；42 分子→死亡事故项目数；
43 公式=抽排量÷建成区面积；47 取第1种÷计划长度；38/45 标适用性；T系列不含（27-55 已不含）。
"""
import io, os

BASE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(BASE, "指标公式展开表-v1.md")

# 城区 29 项 = 27..55（T5-T14 不在本表，批注⑤剔除）
# 每行: (指标, 范式, 分子, 分母, 统计范围, 时间基准, 数据来源, 依据/阈值, 引用量/实体, 数据)
ROWS = {
27:("绿道服务半径覆盖率","C1","绿道两侧 1 km 覆盖的**建成区居住用地面积**","**建成区总居住用地面积**","建成区","现状","官方/行业调查/遥感","≥70%（国家/生态园林城市）","`GreenwayCoveredResidentialLandArea`、`BuiltUpResidentialLandArea`、`Greenway`","结果✓ 分子✗ 分母✗"),
28:("新增各类体育场地面积","E","Σ 体育场地新增面积（建设年份 = 上一年度）","—","建成区","本年−上年","官方/行业调查","自定；人均≥2.5㎡(2035)","`SportsVenue.facilityArea`、`constructionYear`","结果✓ 明细✗"),
29:("人均公共文化设施面积","D","公共文化设施面积","**常住人口**","建成区","当年","官方/行业调查","≥0.2㎡/人；自定","`PublicCulturalFacility.facilityArea`、`PermanentPopulation`","结果✓ 分子✗ 分母✗"),
30:("城市道路网密度","D","城市道路长度","**建成区面积**","建成区","现状","行业调查/遥感/商业大数据","≥8 km/km²","`CityRoadLength`、`BuiltUpArea`","结果✓ 分子✗ 分母✗"),
31:("新建建筑中绿色建筑占比","C2","Σ 新建绿色建筑面积","Σ 新开工建筑面积","建成区","当年（新开工）","官方/行业调查","新建100%绿建；星级≥30%合格","`Building.floorArea`、`greenBuildingLevel`、`constructionStage`","结果✓ 分子/分母部分可得（楼栋缺面积）"),
32:("历史文化街区、历史建筑挂牌建档率","C2","已挂牌建档数","已认定公布总数","建成区【批注①】","现状","官方/行业调查","100%（应挂尽挂）","`HistoricalBuilding.archiveStatus`","结果✓ 明细✗"),
33:("历史建筑空置率","C2","闲置 ≥ 半年数","公布总数","建成区【批注①】","现状（闲置≥半年）","官方/行业调查","自定（以用促保）","`HistoricalBuilding.vacancyStatus`","结果✓ 明细✗"),
34:("历史文化资源遭受破坏的负面事件数","A1","count(负面事件, 发生时间 ∈ 体检时段)","—","—","体检时段","行业调查","应为 0","`NegativeEvent`","结果✓ 明细✗"),
35:("擅自拆除历史文化街区内建筑物、构筑物数量","A1","count(历史街区内建筑/构筑物, 被擅自拆除)","—","—","体检时段","行业调查/遥感","应为 0","`HistoricBlockBuilding.demolishedStatus`","结果✓ 明细✗"),
36:("各类保护对象增加数量","E","本年认定数 − 上年认定数","—","全市辖区","本年−上年","官方/行业调查","自定","`ProtectedObject`","结果✓ 明细✗"),
37:("城市高峰期机动车平均速度","D","avg(高峰期观测值)","—","建成区","工作日早晚高峰","行业调查/商业大数据","快速路≥30/主干路≥20 km/h","`VehicleTravelSpeed`","结果✓ 观测✗"),
38:("轨道站点周边覆盖通勤比例","C2","800 m 覆盖轨道通勤量","城市总通勤量","建成区（仅轨道城市）【批注⑥】","现状（通勤）","行业调查/商业大数据","超大≥30/特大≥20/大≥10%","`RailCommutingVolume`、`TotalCommutingVolume`","结果空 分子✗ 分母✗"),
39:("公租房保障最长轮候时间","D","max(轮候时间)","—","建成区","当年（已配租）","—","≤36 月","`PublicRentalHousing`","结果✓ 明细✗"),
40:("城中村改造完成率","C2","已完成改造数","需改造总数","城市辖区","当年","官方/行业调查/大数据","自定","`UrbanVillage`、`renovationStatus`","结果✓ 明细✗"),
41:("城市危旧房改造完成率","C2","已完成改造套数","需改造套数","—","上一年度","—","自定","`Building.dilapidatedStatus`、`renovationStatus`","结果✗ 明细✗"),
42:("房屋市政工程生产安全事故死亡率","C2","发生死亡事故的项目数【批注④】","在建项目数","建成区","当年（全年）","—","依《重大事故判定标准》建质规〔2022〕2号","`SafetyAccident`、`ProjectsUnderConstruction`","结果✓ 分子✗ 分母✗"),
43:("城市排水防涝应急抢险能力","D","总排水能力","**建成区面积**","建成区","现状（设施能力）","官方/行业调查","自定；公式=抽排量÷建成区面积【批注③】","`DrainageFacility`、`BuiltUpArea`","结果✓（0.0025 异常【待核】）"),
44:("应急水源供水保障率","C2","应急供水能力","平均日供水量","建成区","现状","官方/行业调查","应急供水≥80L/(人·天)底线","`EmergencyWaterSource`、`AverageDailyWaterSupply`","结果✓（5.90% 异常【待核】）"),
45:("「平急两用」公共基础设施数量","A1","count(存量)","—","—（仅超大特大城市）【批注⑥】","现状","官方/行业调查","仅超大特大城市","`DualUseInfrastructure`","结果✓"),
46:("城市危旧桥梁数量","A1","count(桥梁, 危旧状态 ∈ 不合格级)","—","—","现状","官方/行业调查","自定","`Bridge.dilapidatedStatus`","结果✓"),
47:("老旧市政燃气管网年度改造完成率","C2","年度改造长度","年度计划长度","建成区","年度","官方/行业调查","自定（常态化清零）；取第1种÷计划长度【批注②】","`GasPipeline`","结果✓ 明细✗"),
48:("城市消防站服务半径覆盖率","C1","覆盖建设用地面积","**建成区建设用地面积**","建成区","现状","行业调查/大数据","5分钟到达（消防站建设标准）","`FireStation`、`BuiltUpConstructionLandArea`","结果✓ 分子✗ 分母✗"),
49:("存量应急避难场所改造个数","A1","count(避难场所, 上一年度完成改造)","—","—","上一年度","官方/行业调查/大数据","100%落实（应急〔2023〕126号）","`EmergencyShelter.renovationStatus`","结果✗"),
50:("城市生命线安全工程监测覆盖率","C2","已监测风险点数","较大及以上风险点总数","建成区","现状","官方/行业调查","自定","`LifelineRiskPoint.monitoringStatus`","结果?【待核】"),
51:("危大工程安全监测覆盖率","C2","监测接入项目数","在建工地数","城市辖区","现状（在建）","官方/行业调查","依住建部令37号","`RiskyConstructionWorks.monitoringStatus`","结果✓（25.93%）"),
52:("高层民用建筑智能化火灾监测预警覆盖率","C2","已配置楼栋数","高层民用建筑楼栋总数","建成区","现状","行业调查","100%","`Building.smartFireMonitorStatus`、`buildingNature`、`floorCount`","结果✓（100%）"),
53:("城市运行管理服务智慧化水平","D","按期处置事项数","平台覆盖面积","建成区","上一年度（处置）","官方/行业调查","依住建部「一网统管」通知","`UrbanOperationPlatform`","结果✓（0.00，单位误写「千米」）"),
54:("问题整治率","C2","已整治数","应整治数","—","上一年度（整治）","官方/行业调查","限时类须按期完成","`Problem.remediationStatus`","结果✓（61.00%）"),
55:("城市更新入库项目数","A1","count(更新项目, 入库年份 = 上一年度)","—","—","上一年度（入库）","—","以数量变化评价","`RenewalProject`","结果✗"),
}

HEADER = "| # | 指标 | 范式 | 分子 | 分母 | 统计范围 | 时间基准 | 数据来源 | 依据/阈值 | 引用量/实体 | 数据 |"
SEP    = "| -: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"

def build_table():
    out = [HEADER, SEP]
    for k in range(27, 56):
        ind, fan, fenzi, fenmu, scope, tb, src, std, ref, data = ROWS[k]
        out.append("| %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            k, ind, fan, fenzi, fenmu, scope, tb, src, std, ref, data))
    return out

def main():
    text = io.open(PATH, encoding="utf-8").read()
    lines = text.split("\n")
    # 定位 §一 表头行与末行（55 行）
    start = next(i for i,l in enumerate(lines) if l.strip().startswith("| # | 指标 | 范式"))
    end = next(i for i,l in enumerate(lines) if l.strip().startswith("| 55 |"))
    new_block = build_table()
    lines[start:end+1] = new_block
    # 在「数据」列说明后追加新列说明
    for i,l in enumerate(lines):
        if l.startswith("> 「数据」列"):
            lines.insert(i+1, "> **新增 4 列（手册口径回填）**：`统计范围`(F1，手册计算单元) · `时间基准`(F2) · `数据来源`(F8) · `依据/阈值`(F9，含点值/分档/区间/城市自定)。来源＝《自治区城市体检工作手册（2026 年版）·城区指标抽取计算规则》，引用标【手册口径】。")
            lines.insert(i+2, "> **范围说明**：本表为城区基础指标 27–55（29 项）；自治区特色指标 T5–T14 不在研究范围（大王 2026-11-09 批注⑤）。")
            break
    io.open(PATH, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    # 校验列数一致
    bad = [(i+start, len(l.split("|"))) for i,l in enumerate(new_block) if l.startswith("|") and len(l.split("|"))!=12]
    print("新表行数:", len(new_block), "| 列数异常:", bad)
    print("写入:", PATH)

if __name__ == "__main__":
    main()
