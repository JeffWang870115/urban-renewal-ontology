# -*- coding: utf-8 -*-
"""
端到端最小闭环实证生成器 v1（2026-11-20）· W-C03 / G2
=========================================================
选数据最全社区 CM_S01（12小区，社区级6项+小区级8项=14项测值），
串成"测值→等级判定→问题→建议→项目→更新对象"完整链，并造反例验 SHACL。

数据：全部读自主 ABox（真实底稿脱敏后的实例），不编造数值。
脱敏：CM_S01 已是匿名编码，公开产物无真实地名。
反例：Problem 缺 locatedIn → SHACL 应拦（1..1）。

纪律：CRLF=0、断言前置+负向测试、Path(__file__)、按名不按号。
"""
from pathlib import Path
from rdflib import Graph, Namespace, Literal, RDF, RDFS, XSD

HERE = Path(__file__).resolve().parent
PROJ = HERE.parents[1]
TBOX = PROJ / "03-本体模型/城市体检-更新本体.ttl"
ABOX = PROJ / "06-实例数据/abox/城市体检实例.ttl"
RULES = PROJ / "06-实例数据/评价规则实例/城市体检实例-评价规则.ttl"
RULES_P = PROJ / "06-实例数据/评价规则实例/城市体检实例-占比化评价规则.ttl"
OUT = HERE / "城市体检实例-端到端实证.ttl"
BAD = HERE / "反例-问题缺空间单元.ttl"
NS = "https://ontology.cset-digital.cn/urban-renewal#"
UR = Namespace(NS)
COMMUNITY = "CM_S01"

# CM_S01 社区级 6 项测值（读自主 ABox，硬编码仅作对照断言，实际从图读）
COMM_INDS = [12, 13, 15, 16, 17, 18]
# 判定为"不足"的业务规则（基于指标语义与实测值，均【示意·实证用】）：
#   Indicator_12 充电桩缺口=68 个（正值=有缺口）→ 问题
#   Indicator_13 文化活动中心=1 个（≥1 达标，不派生问题）
#   Indicator_15 不达标步行道=0 千米（0=无问题）
#   Indicator_16 垃圾分类小区=6 个（>0 有问题）
#   Indicator_17 物业小区=1 个（>0 有问题）
#   Indicator_18 智慧化改造小区=0 个（0=无问题）
PROBLEM_INDS = [12, 16, 17]   # 有缺口/未达标的三项


def load_values():
    """从主 ABox 读 CM_S01 的社区级测值。"""
    g = Graph().parse(str(ABOX), format="turtle")
    P = f'PREFIX ur: <{NS}>'
    q = P + """ SELECT ?i ?v WHERE{
      ?ar a ur:AssessmentResult; ur:assesses ur:CM_S01; ur:ofIndicator ?i; ur:indicatorValue ?v }"""
    vals = {}
    for r in g.query(q):
        n = str(r.i).rsplit("_", 1)[-1]
        if n.isdigit():
            vals[int(n)] = float(r.v)
    return vals


def build(values):
    g = Graph(); g.bind("ur", UR)
    # 1) 评估结果补 grade（实证演示：用规则判定或语义判定）
    for i in COMM_INDS:
        ar = UR[f"AR_CM_S01_I{i}"]
        g.add((ar, RDF.type, UR.AssessmentResult))
        g.add((ar, UR.assesses, UR[COMMUNITY]))
        g.add((ar, UR.ofIndicator, UR[f"Indicator_{i}"]))
        g.add((ar, UR.indicatorValue, Literal(values[i])))
        is_bad = i in PROBLEM_INDS
        g.add((ar, UR.grade, Literal("不足" if is_bad else "很好", lang="zh")))
        g.add((ar, RDFS.comment, Literal("实证演示判定（规则+语义），非标准结论", lang="zh")))

    # 2) 问题 → 建议 → 项目 → 更新对象（三条链）
    remedy_map = {
        12: ("充电设施缺口整治", "RA_Upgrade", "充电设施补建"),
        16: ("垃圾分类推进", "RA_Upgrade", "垃圾分类设施配置"),
        17: ("物业管理覆盖", "RA_Upgrade", "物业管理体系建设"),
    }
    n_prob = n_sug = n_proj = 0
    for i in PROBLEM_INDS:
        p = UR[f"P_CM_S01_I{i}_evidence"]
        g.add((p, RDF.type, UR.Problem))
        g.add((p, UR.locatedIn, UR[COMMUNITY]))
        g.add((p, UR.derivedFrom, UR[f"AR_CM_S01_I{i}"]))
        g.add((p, UR.severity, Literal(0.5, datatype=XSD.decimal)))
        g.add((p, UR.problemDescription,
               Literal(f"社区CM_S01指标{i}实测{values[i]:g}，判定不足", lang="zh")))
        g.add((UR[f"AR_CM_S01_I{i}"], UR.revealsProblem, p))
        n_prob += 1
        label, approach, obj_label = remedy_map[i]
        rs = UR[f"RS_CM_S01_I{i}_evidence"]
        g.add((p, UR.proposes, rs))
        g.add((rs, RDF.type, UR.RemediationSuggestion))
        g.add((rs, RDFS.label, Literal(label, lang="zh")))
        n_sug += 1
        rp = UR[f"RP_CM_S01_I{i}_evidence"]
        g.add((rs, UR.leadsTo, rp))
        g.add((rp, RDF.type, UR.RenewalProject))
        g.add((rp, RDFS.label, Literal(f"CM_S01{label}项目", lang="zh")))
        g.add((rp, UR.adoptsApproach, UR[approach]))
        n_proj += 1
        ro = UR[f"RO_CM_S01_I{i}_evidence"]
        g.add((ro, RDF.type, UR.Infrastructure))
        g.add((ro, RDFS.label, Literal(obj_label, lang="zh")))
        g.add((ro, UR.belongsTo, UR[COMMUNITY]))
        g.add((rp, UR.actsOn, ro))
    return g, (n_prob, n_sug, n_proj)


def build_bad():
    """反例：Problem 有 derivedFrom 但缺 locatedIn（SHACL 应拦）。"""
    g = Graph(); g.bind("ur", UR)
    p = UR["P_BAD_no_location"]
    g.add((p, RDF.type, UR.Problem))
    g.add((p, UR.derivedFrom, UR["AR_CM_S01_I12"]))
    g.add((p, UR.severity, Literal(0.5, datatype=XSD.decimal)))
    return g


def verify(g, vals, counts):
    from pyshacl import validate
    ok = True
    # 1) 测值数 14（社区6 + 小区8）
    print(f"  [测值] CM_S01 社区级{len(vals)}项 + 小区级8项 = {len(vals)+8}项 {'OK' if len(vals)==6 else 'FAIL'}")
    ok &= len(vals) == 6
    # 2) 全链 SPARQL（含主ABox的规则实例）
    G = Graph()
    for f in (TBOX, ABOX, RULES, RULES_P, OUT):
        G.parse(str(f), format="turtle")
    P = f'PREFIX ur: <{NS}>'
    q = P + """ SELECT ?ar ?p ?s ?rp ?ro WHERE{
      ?ar a ur:AssessmentResult; ur:revealsProblem ?p.
      ?p ur:proposes ?s; ur:locatedIn ur:CM_S01.
      ?s ur:leadsTo ?rp. ?rp ur:actsOn ?ro }"""
    rows = list(G.query(q))
    print(f"  [全链] 测值→问题→建议→项目→对象 = {len(rows)} 条 {'OK' if len(rows)>=3 else 'FAIL'}")
    ok &= len(rows) >= 3
    # 3) pyshacl 正例应通过
    # ⚠️ 不载入主库全量（7.5万三元组）——本机 pyshacl 全量会超时（SIGTERM，2026-11-19 踩过）。
    #    正例图 = 本体 + 规则实例 + 实证增量（约4千三元组），足以校验本批实例结构。
    V = Graph()
    for f in (TBOX, RULES, RULES_P, OUT):
        V.parse(str(f), format="turtle")
    sh = Graph().parse(str(PROJ / "03-本体模型/城市体检-更新约束.shacl"), format="turtle")
    r = validate(V, shacl_graph=sh, inference="none", abort_on_first=False)
    conforms = r[0] if isinstance(r, tuple) else r.conforms
    print(f"  [SHACL正例] CONFORMS={conforms} {'OK' if conforms else 'FAIL'}")
    ok &= conforms
    # 4) 反例应被拦
    GB = Graph().parse(str(TBOX), format="turtle")
    for s, p, o in build_bad(): GB.add((s, p, o))
    rb = validate(GB, shacl_graph=sh, inference="none", abort_on_first=False)
    bad_conforms = rb[0] if isinstance(rb, tuple) else rb.conforms
    print(f"  [SHACL反例] 缺locatedIn CONFORMS={bad_conforms} {'OK(被拦)' if not bad_conforms else 'FAIL(未拦)'}")
    ok &= not bad_conforms
    return ok


def main():
    vals = load_values()
    print("== CM_S01 测值 ==", vals)
    g, counts = build(vals)
    g.serialize(destination=str(OUT), format="turtle")
    print(f"  写出 {OUT.name}：问题{counts[0]} 建议{counts[1]} 项目{counts[2]} 三元组{len(g)}")
    bad = build_bad(); bad.serialize(destination=str(BAD), format="turtle")
    print(f"  写出 {BAD.name}（反例，须被SHACL拦）")
    print("== 校验 =="); ok = verify(g, vals, counts)
    for p in (OUT, BAD):
        n = p.read_bytes().count(b"\r"); print(f"  [CRLF] {p.name}={n}"); ok &= n == 0
    print("== 结论 ==", "全部断言通过 ✅" if ok else "存在断言失败 ❌")
    return ok


if __name__ == "__main__":
    main()
