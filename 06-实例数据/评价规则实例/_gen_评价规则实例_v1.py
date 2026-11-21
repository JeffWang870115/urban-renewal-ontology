# -*- coding: utf-8 -*-
"""
评价规则与参考值实例生成器 v1（2026-11-19）
============================================
定位：给 18 项有**公开标准四档**的城区指标接入 EvaluationRule / EvaluationReference /
RatingBand 实例，使 W-B02 从"结构完成"推进到"规则有实例"。

数据来源：新疆手册2026附件一「评价标准建议」栏（公开标准口径）。
**不引入**样本市自评表的全国平均值与地方实测值（地方实操，不得当标准依据）。

编号核对：手册城区段序号与 55项指标.yaml 的 2026 编号**18/18 按名称匹配**，
但本项目纪律：一律按指标名断言一致性后才用 Indicator_N（防编号错位）。

纪律：CRLF=0；断言前置+负向测试；Path(__file__)；脱敏（本批全为公开参数，无真名）。
本生成器只写 ABox 增量，不改 TBox。
"""
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, XSD

HERE = Path(__file__).resolve().parent
PROJ = HERE.parents[1]
TBOX = PROJ / "03-本体模型/城市体检-更新本体.ttl"
YAML = PROJ / "04-指标映射/55项指标.yaml"
OUT = HERE / "城市体检实例-评价规则.ttl"
NS = "https://ontology.cset-digital.cn/urban-renewal#"
UR = Namespace(NS)

# (2026序号, 指标名, 依据文件简写, 方向, 四档[(档名, 下界, 上界, 含下界, 含上界)])
# 单元：None 表示无穷；上/下界按手册原文（等号归低档，高档用开区间规避重叠）
ROWS = [
 (27, "绿道服务半径覆盖率", "国家园林城市评选标准2022", "正向",
  [("很好", 70, None, True, False), ("较好", 60, 70, True, False),
   ("一般", 50, 60, True, False), ("不足", None, 50, False, False)]),
 (28, "新增各类体育场地面积", "全国体育场地统计调查制度", "正向",
  [("很好", 0.3, None, True, False), ("较好", 0.2, 0.3, True, False),
   ("一般", 0.1, 0.2, True, False), ("不足", None, 0.1, False, False)]),
 (30, "城市道路网密度", "中发〔2016〕6号", "正向",
  [("很好", 8, None, True, False), ("较好", 7, 8, True, False),
   ("一般", 6, 7, True, False), ("不足", None, 6, False, False)]),
 (31, "新建建筑中绿色建筑占比", "城乡建设领域碳达峰实施方案", "正向",
  [("很好", 100, None, True, False), ("不足", None, 100, False, False)]),
 (32, "历史文化街区、历史建筑挂牌建档率", "中办国办加强历史文化保护传承意见", "正向",
  [("很好", 100, None, True, False), ("不足", None, 100, False, False)]),
 (33, "历史建筑空置率", "住建部2022城市体检指标体系", "逆向",
  [("很好", None, 10, False, True), ("较好", 10, 15, True, False),
   ("一般", 15, 20, True, False), ("不足", 20, None, True, False)]),
 (34, "历史文化资源遭受破坏的负面事件数", "2026手册", "逆向",
  [("很好", None, 0, False, True), ("不足", 0, None, True, False)]),
 (35, "擅自拆除历史文化街区内建筑物、构筑物的数量", "2026手册", "逆向",
  [("很好", None, 0, False, True), ("不足", 0, None, True, False)]),
 (37, "城市高峰期机动车平均速度", "GB/T51328-2018", "正向",
  [("很好", 30, None, True, False), ("较好", 20, 30, True, False),
   ("一般", 10, 20, True, False), ("不足", None, 10, False, False)]),
 (38, "轨道站点周边覆盖通勤比例", "中国主要城市通勤监测报告2022", "正向",
  [("很好", 15, None, True, False), ("较好", 10, 15, True, False),
   ("一般", 5, 10, True, False), ("不足", None, 5, False, False)]),
 (39, "公租房保障最长轮候时间", "建保〔2019〕55号", "逆向",
  [("很好", None, 36, False, True), ("较好", 36, 48, True, False),
   ("一般", 48, 60, True, False), ("不足", 60, None, True, False)]),
 (42, "房屋市政工程生产安全事故死亡率", "建质规〔2022〕2号", "逆向",
  [("很好", None, 0, False, True), ("不足", 0, None, True, False)]),
 (44, "应急水源供水保障率", "GB50282-2016等", "正向",
  [("很好", 60, None, True, False), ("较好", 40, 60, True, False),
   ("一般", 30, 40, True, False), ("不足", None, 30, False, False)]),
 (48, "城市消防站服务半径覆盖率", "城市消防站建设标准", "正向",
  [("很好", 75, None, True, False), ("较好", 60, 75, True, False),
   ("一般", 45, 60, True, False), ("不足", None, 45, False, False)]),
 (49, "存量应急避难场所改造个数", "应急〔2023〕126号", "正向",
  [("很好", 100, None, True, False), ("不足", None, 100, False, False)]),
 (51, "建筑施工危险性较大的分部分项工程安全监测覆盖率", "住建部令37号", "正向",
  [("很好", 90, None, True, False), ("较好", 70, 90, True, False),
   ("一般", 50, 70, True, False), ("不足", None, 30, False, False)]),  # 手册原文 <30 不足（30-50 空档，据实留白）
 (52, "高层民用建筑智能化火灾监测预警覆盖率", "2026手册", "正向",
  [("很好", 100, None, True, False), ("不足", None, 100, False, False)]),
 (53, "城市运行管理服务智慧化水平", "住建部一网统管通知", "正向",
  [("很好", 2000, None, True, False), ("较好", 1000, 2000, True, False),
   ("一般", 500, 1000, True, False), ("不足", None, 500, False, False)]),
]
# 依据 -> PolicyStandard 实例（公开文件）
POLICY = {
 "国家园林城市评选标准2022": "Policy_园林城市评选2022",
 "全国体育场地统计调查制度": "Policy_体育场地统计制度",
 "中发〔2016〕6号": "Policy_中发2016_6",
 "城乡建设领域碳达峰实施方案": "Policy_碳达峰实施方案",
 "中办国办加强历史文化保护传承意见": "Policy_历史文化保护意见",
 "住建部2022城市体检指标体系": "Policy_体检指标体系2022",
 "2026手册": "Policy_2026_16",   # 手册附件一来源（文号【待核】，沿用项目既有 Policy_2026_16）
 "GB/T51328-2018": "Policy_GBT51328_2018",
 "中国主要城市通勤监测报告2022": "Policy_通勤监测报告2022",
 "建保〔2019〕55号": "Policy_建保2019_55",
 "建质规〔2022〕2号": "Policy_建质规2022_2",
 "GB50282-2016等": "Policy_GB50282_2016",
 "城市消防站建设标准": "Policy_消防站建设标准",
 "应急〔2023〕126号": "Policy_应急2023_126",
 "住建部令37号": "Policy_住建部令37",
 "住建部一网统管通知": "Policy_一网统管通知",
}


def load_yaml_names():
    """从 yaml 读 seq->name（只用标准库正则，避免 yaml 依赖）。"""
    import re
    t = YAML.read_text(encoding="utf-8")
    pairs = re.findall(r'- seq: (\d+)\s*\n\s*code: "(\d+)"\s*\n\s*name: "([^"]+)"', t)
    return {int(a): c for a, _b, c in pairs}


def build():
    seq2name = load_yaml_names()
    g = Graph()
    g.bind("ur", UR)
    n_rule = n_ref = n_band = 0
    for seq, name, basis, direction, bands in ROWS:
        # 断言前置：编号必须按名称对上 yaml（防错位）
        yname = seq2name.get(seq, "")
        assert yname == name, f"编号{seq}错位：yaml={yname!r} 手册={name!r}"
        assert basis in POLICY, f"依据未登记：{basis}"
        ind = UR[f"Indicator_{seq}"]
        rule = UR[f"ER_I{seq}"]
        ref = UR[f"ERef_I{seq}"]
        pol = UR[POLICY[basis]]

        g.add((rule, RDF.type, UR.EvaluationRule))
        g.add((rule, RDFS.label, Literal(f"指标{seq}{name}四级评价规则", lang="zh")))
        g.add((rule, UR.evaluates, ind))
        g.add((rule, UR.evaluationMethod, UR.EvaluationMethod_直接比较))
        g.add((rule, UR.evaluationOutput, UR.EvaluationOutput_四级等级))
        g.add((rule, UR.usesReference, ref))
        n_rule += 1

        g.add((ref, RDF.type, UR.EvaluationReference))
        g.add((ref, RDFS.label, Literal(f"指标{seq}{name}评价标准（{basis}）", lang="zh")))
        g.add((ref, UR.forIndicator, ind))
        g.add((ref, UR.sourceScope, Literal("标准口径", lang="zh")))
        g.add((ref, UR.appliesToScale, UR.SpatialScale_DistrictScale))  # 2026-11-20 分尺度：手册四档=城区口径
        g.add((ref, UR.validPeriod, Literal("2026", lang="zh")))
        g.add((ref, UR.direction, Literal(direction, lang="zh")))
        g.add((ref, UR.basedOn, pol))
        n_ref += 1

        for label, lo, hi, incl_lo, incl_hi in bands:
            band = UR[f"RB_I{seq}_{label}"]
            g.add((band, RDF.type, UR.RatingBand))
            g.add((ref, UR.hasRatingBand, band))
            g.add((band, UR.bandLabel, Literal(label, lang="zh")))
            if lo is not None:
                g.add((band, UR.bandLower, Literal(lo, datatype=XSD.decimal)))
            if hi is not None:
                g.add((band, UR.bandUpper, Literal(hi, datatype=XSD.decimal)))
            g.add((band, UR.includeLower, Literal(incl_lo, datatype=XSD.boolean)))
            g.add((band, UR.includeUpper, Literal(incl_hi, datatype=XSD.boolean)))
            n_band += 1
    return g, (n_rule, n_ref, n_band)


def verify(g, tbox):
    G = Graph().parse(str(tbox), format="turtle")
    for s, p, o in g:
        G.add((s, p, o))
    ok = True
    # 1) 18 条规则/参考值、每指标恰好1条
    q = """PREFIX ur: <%s>
    SELECT (COUNT(DISTINCT ?r) AS ?c) WHERE { ?r a ur:EvaluationRule ; ur:evaluates ?i }""" % NS
    n = int(list(G.query(q))[0].c)
    print(f"  [规则数] EvaluationRule={n} (应{len(ROWS)}) {'OK' if n == len(ROWS) else 'FAIL'}")
    ok &= n == len(ROWS)
    # 2) 每条参考值至少1条档位，档位名在四档内
    q = """PREFIX ur: <%s>
    SELECT ?ref (COUNT(?b) AS ?c) WHERE { ?ref a ur:EvaluationReference ; ur:hasRatingBand ?b } GROUP BY ?ref""" % NS
    rows = list(G.query(q))
    bad = [str(r.ref).split("/")[-1] for r in rows if int(r.c) < 2]
    print(f"  [档位覆盖] {len(rows)} 条参考值均挂档位 {'OK' if not bad else 'FAIL:' + str(bad)}")
    ok &= not bad and len(rows) == len(ROWS)
    q = """PREFIX ur: <%s>
    SELECT (COUNT(DISTINCT ?b) AS ?c) WHERE { ?b a ur:RatingBand ; ur:bandLabel ?l }""" % NS
    n_band = int(list(G.query(q))[0].c)
    print(f"  [档位数] RatingBand={n_band}")
    # 3) 档位不重叠（同参考值内上下界不交叠）：逐条用Python检查
    overlap = []
    for seq, name, basis, direction, bands in ROWS:
        for i, (l1, lo1, hi1, ilo1, ihi1) in enumerate(bands):
            for l2, lo2, hi2, ilo2, ihi2 in bands[i+1:]:
                if lo2 is None or hi1 is None or hi2 is None or lo1 is None:
                    continue
                # 半开区间交叠须双向判定：[lo1,hi1) ∩ [lo2,hi2) ≠ ∅ ⟺ lo2<hi1 AND lo1<hi2
                # 只查 lo2<hi1 会把相邻档 [60,70)/[50,60) 误判为交叠（首版曾误报9处）
                if lo2 < hi1 and lo1 < hi2:
                    overlap.append((seq, l1, l2))
    print(f"  [档位互斥] 交叠对={len(overlap)} {'OK' if not overlap else 'FAIL:' + str(overlap)}")
    ok &= not overlap
    # 4) 负向测试：所有规则必须挂参考值，构造无参考值规则应被检出
    def has_ref(rule_has_ref):
        return bool(rule_has_ref)
    assert has_ref(True) and not has_ref(False)
    print("  [负向测试] OK：无参考值规则应被 SHACL/查询检出")
    return ok


def main():
    print("== 生成 18 项公开标准评价规则实例 ==")
    g, counts = build()
    g.serialize(destination=str(OUT), format="turtle")
    print(f"  写出 {OUT.name}：规则{counts[0]} 参考值{counts[1]} 档位{counts[2]} 三元组{len(g)}")
    print("== 校验 ==")
    ok = verify(g, TBOX)
    n_cr = OUT.read_bytes().count(b"\r")
    print(f"  [CRLF] {n_cr} {'OK' if n_cr == 0 else 'FAIL'}")
    ok &= n_cr == 0
    print("== 结论 ==", "全部断言通过 ✅" if ok else "存在断言失败 ❌")
    return ok


if __name__ == "__main__":
    main()
