# -*- coding: utf-8 -*-
"""
导出前端诊断视图所需的规则与测值数据（2026-11-20）
====================================================
从 TTL 实例导出 window.__DIAG__ 数据：
- rules: 指标 -> 方法/方向/四档边界（来自 EvaluationReference + RatingBand）
- values: CM_S01 的 14 项测值（来自主 ABox）
- chains: 已实证的 3 条问题链（来自端到端实证 TTL）
用途：阶段一原型在浏览器内执行"测值→等级"比较，零依赖、file:// 可用。
纪律：导出值已是公开口径或脱敏值（CM_S01 匿名、不含地方真值）。
"""
import sys
from pathlib import Path
from rdflib import Graph, Namespace

HERE = Path(__file__).resolve().parent
PROJ = HERE.parents[1]
sys.path.insert(0, str(PROJ / "06-实例数据"))
from _shared_楼栋台账 import read_scopes, HAZARD_KEYS  # noqa: E402

NS = "https://ontology.cset-digital.cn/urban-renewal#"
UR = Namespace(NS)
OUT = PROJ / "05-产出/原型方案/原型/data/diagnosis.js"

def q(g, s):
    return g.query("PREFIX ur: <"+NS+">\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"+s)

# 指标(2026编号) -> 楼栋表隐患旗标列段（按第4行表头实测，硬编码列号非真名）
# 数据源：大王 11-20 指定权威表 楼栋数据.xlsx，经共享模块 _shared_楼栋台账 读取
# 社区真名 -> 匿名代号（运行时从脱敏映射读，源码零真名）
def _name2code():
    import csv
    maps = sorted(PROJ.glob("01-资料/*/_脱敏映射/编号映射.csv"))
    assert maps, "找不到脱敏映射表"
    d = {}
    with maps[0].open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if str(row.get("层级", "")).strip() == "社区":
                full = str(row.get("原名（本地，不入库）", ""))
                d[full.split("/")[-1].strip()] = str(row.get("编号", "")).strip()
    return d


def community_ratio(values):
    """CM_S01 社区尺度占比：分子分母同源取权威台账（社区53/楼栋3599/无支油区）。"""
    stats, rows, haz = read_scopes()
    name2code = _name2code()
    cname = next(k for k, v in name2code.items() if v == "CM_S01")
    den, num1 = stats["community"][cname]
    src = Path(__file__).read_text(encoding="utf-8")
    assert cname not in src, "源码泄漏社区真名（脱敏红线）"
    # 8 项隐患分子按社区从逐栋行复算（同尺度同源）
    counts = {ind: 0 for ind in HAZARD_KEYS}
    for s, c, q, b, flags in rows:
        if c != cname:
            continue
        for ind, bad in flags.items():
            if bad:
                counts[ind] += 1
    for ind, cnt in counts.items():
        old = values.get(ind)
        if old is not None and abs(old - cnt) > 0.01:
            print("  [口径差异·待核] 指标%s 主库=%g 权威台账=%d → 以台账为准" % (ind, old, cnt))
        values[ind] = float(cnt)
    print("社区楼栋分母 =", den, " 台账隐患栋数(分子) =", counts)
    ratios = {ind: round(values[ind] / den * 100, 2) for ind in HAZARD_KEYS if ind in values}
    return den, ratios


def community_percentile():
    """D3：社区级分位——权威台账算全部 53 社区指标1占比，给 CM_S01 排名。
    只导出匿名代号+占比，真名不写出。"""
    stats, rows, haz = read_scopes()
    name2code = _name2code()
    ranked = []
    for cname, (den, num) in stats["community"].items():
        code = name2code.get(cname)
        if not code or den == 0:
            continue
        ranked.append({"code": code, "pct": round(num / den * 100, 2)})
    ranked.sort(key=lambda x: x["pct"])
    n = len(ranked)
    target = next((i for i, x in enumerate(ranked) if x["code"] == "CM_S01"), None)
    assert target is not None, "分位中找不到 CM_S01"
    pct_rank = round(target / (n - 1) * 100, 1) if n > 1 else 0
    print(f"社区分位：CM_S01 占比={ranked[target]['pct']}% 在 {n} 社区中排第 {target+1}（百分位 {pct_rank}%）")
    out = [{"code": x["code"], "pct": x["pct"]} for x in ranked]
    return {"indicator": "1", "target": "CM_S01", "target_pct": ranked[target]["pct"],
            "rank": target + 1, "total": n, "percentile": pct_rank,
            "lower_is_better": True, "all": out}


def main():
    g = Graph()
    for f in ("03-本体模型/城市体检-更新本体.ttl",
              "06-实例数据/评价规则实例/城市体检实例-评价规则.ttl",
              "06-实例数据/评价规则实例/城市体检实例-占比化评价规则.ttl",
              "06-实例数据/abox/城市体检实例.ttl",
              "06-实例数据/端到端实证/城市体检实例-端到端实证.ttl"):
        g.parse(str(PROJ / f), format="turtle")
    print("合并图三元组 =", len(g))

    # 1) 规则：indicator -> {method, direction, bands[(label,lower,upper)]}
    rules = {}
    for r in q(g, """SELECT ?i ?m ?d ?ref WHERE{
      ?rule a ur:EvaluationRule ; ur:evaluates ?i ; ur:usesReference ?ref .
      OPTIONAL{ ?rule ur:evaluationMethod ?m } OPTIONAL{ ?ref ur:direction ?d } }"""):
        ind = str(r.i).rsplit("_", 1)[-1]
        if not ind.isdigit(): continue
        bands = []
        for b in q(g, f"""SELECT ?lab ?lo ?hi WHERE{{
          <{r.ref}> ur:hasRatingBand ?b . ?b ur:bandLabel ?lab .
          OPTIONAL{{ ?b ur:bandLower ?lo }} OPTIONAL{{ ?b ur:bandUpper ?hi }} }}"""):
            bands.append({"label": str(r_band) if False else str(b.lab),
                          "lo": float(b.lo) if b.lo is not None else None,
                          "hi": float(b.hi) if b.hi is not None else None})
        if bands:
            rules[ind] = {
                "method": str(r.m).split("#")[-1] if r.m else "直接比较",
                "direction": str(r.d) if r.d else "正向",
                "bands": bands,
            }
    print("规则数 =", len(rules))

    # 2) CM_S01 测值：社区级 6 项 + 小区级 8 项（12小区求和）= 14 项
    values = {}
    for r in q(g, """SELECT ?i ?v WHERE{
      ?ar a ur:AssessmentResult ; ur:assesses ur:CM_S01 ;
          ur:ofIndicator ?i ; ur:indicatorValue ?v }"""):
        ind = str(r.i).rsplit("_", 1)[-1]
        if ind.isdigit(): values[ind] = float(r.v)
    quarters = {}
    for r in q(g, """SELECT ?i (SUM(?v) AS ?sum) WHERE{
      ?ar a ur:AssessmentResult ; ur:assesses ?rq ; ur:ofIndicator ?i ; ur:indicatorValue ?v .
      ?rq a ur:ResidentialQuarter ; ur:locatedIn ur:CM_S01 } GROUP BY ?i"""):
        ind = str(r.i).rsplit("_", 1)[-1]
        if ind.isdigit() and ind not in values:
            quarters[ind] = float(r["sum"])
    values.update(quarters)   # 社区级优先，小区级聚合补全
    print("CM_S01 测值(社区6+小区8) =", values, "共", len(values), "项")

    # ⚠️ 尺度对齐（2026-11-20 大王指正的逻辑错，取代首版"分母3599"做法）：
    # 占比化指标的分子是 CM_S01 社区的隐患栋数（社区尺度），分母也必须是
    # 该社区的住宅总栋数（社区尺度），不能用全市 3599——否则分子分母尺度错配。
    # 正确：占比 = 社区隐患栋数 / 社区住宅总栋数 × 100，再与四档区间比较。
    # 分母从权威表 楼栋数据.xlsx 按社区动态统计（共享模块）；社区真名运行时从脱敏映射读（源码零真名）。
    DENOM, ratios = community_ratio(values)

    # 社区级 12/15/16/17/18 设施类指标的占比口径未结构化（分母是社区总数/小区总数），
    # 前端对无 ratio 者不做档位判定（标"占比口径待补"），不强行套楼栋尺度。
    print("派生占比(指标1-8, 社区分母=%d) =" % DENOM, ratios)

    # 3) 实证链：indicator -> {problem, suggestion, project, object, desc}
    chains = {}
    for r in q(g, """SELECT ?i ?p ?s ?rp ?ro ?desc WHERE{
      ?ar a ur:AssessmentResult ; ur:ofIndicator ?i ; ur:revealsProblem ?p .
      ?p ur:proposes ?s ; ur:problemDescription ?desc .
      ?s ur:leadsTo ?rp . ?rp ur:actsOn ?ro }"""):
        ind = str(r.i).rsplit("_", 1)[-1]
        if ind.isdigit():
            chains[ind] = {"problem": str(r.p).split("#")[-1],
                           "suggestion": str(r.s).split("#")[-1],
                           "project": str(r.rp).split("#")[-1],
                           "object": str(r.ro).split("#")[-1],
                           "desc": str(r.desc)}
    print("实证链数 =", len(chains))

    # 4) 社区级分位（D3，指标1）
    percentile = community_percentile()
    # 脱敏断言：分位全量列表只能含 CM_Sxx 匿名代号，不得含真名
    import csv
    maps = sorted(PROJ.glob("01-资料/*/_脱敏映射/编号映射.csv"))
    real_names = set()
    with maps[0].open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            v = str(row.get("原名（本地，不入库）", ""))
            if v:
                real_names.add(v.split("/")[-1].strip())
    import json
    plist_txt = json.dumps(percentile, ensure_ascii=False)
    leaked_pct = [n for n in real_names if n and n in plist_txt]
    assert not leaked_pct, "分位数据泄漏社区真名：%s" % leaked_pct[:3]
    codes_ok = all(str(x["code"]).startswith("CM_S") for x in percentile["all"])
    assert codes_ok, "分位列表含非匿名代号"
    print("分位脱敏断言 OK：", percentile["total"], "个社区均匿名代号")

    data = {"rules": rules, "values": values, "chains": chains, "ratios": ratios,
            "percentile": percentile,
            "denominator": DENOM, "denominator_scope": "community",
            "community": "CM_S01",
            "note": "档位来自公开标准与地方自评表【地方实操】；测值为脱敏后社区级值；"
                    "占比化指标(1-8)用同尺度占比=社区隐患栋数÷社区住宅总栋数(%d栋)×100 与档位比较，"
                    "分子分母均为 CM_S01 社区尺度（非全市3599）；社区级设施类指标占比口径待补不判级" % DENOM}
    js = "window.__DIAG__=" + json.dumps(data, ensure_ascii=False, indent=1) + ";\n"
    with OUT.open("w", encoding="utf-8", newline="\n") as f:
        f.write(js)
    print("写出", OUT.name, "字符数", len(js), "CRLF", OUT.read_bytes().count(b"\r"))

if __name__ == "__main__":
    main()
