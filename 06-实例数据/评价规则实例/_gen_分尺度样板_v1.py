# -*- coding: utf-8 -*-
"""
分尺度评级样板生成器 v2（2026-11-20，D4：只做指标1四级）
============================================================
改动 v2：数据源切换为大王 11-20 指定的权威表 楼栋数据.xlsx（原 楼栋数据汇总表.xlsx 作废）；
         统计逻辑下沉到共享模块 _shared_楼栋台账.py（街道5/社区53/小区404/楼栋3599，无支油区）。
级别：城区/街道/社区/小区各建一条 EvaluationReference + EvaluationRule，档次共用 ERef_P1。
楼栋级暂缓（布尔隐患 vs 四档百分比不同构，大王 11-20 确认）。

纪律：分子分母同尺度同源；源码零真名；公开TTL只标量级、真值留本地；断言前置+负向测试+CRLF=0。
"""
import sys
from pathlib import Path
from rdflib import Graph, Namespace, Literal, RDF, RDFS

HERE = Path(__file__).resolve().parent
PROJ = HERE.parents[1]
sys.path.insert(0, str(PROJ / "06-实例数据"))
from _shared_楼栋台账 import read_scopes  # noqa: E402

NS = "https://ontology.cset-digital.cn/urban-renewal#"
UR = Namespace(NS)
OUT = HERE / "城市体检实例-分尺度样板.ttl"
LOCAL_TRUTH = sorted(PROJ.glob("01-资料/*/_脱敏映射"))[0] / "分尺度样板真值对照.csv"

LEVELS = [("district", "DistrictScale", "城区"),
          ("street", "NeighborhoodScale", "街道"),
          ("community", "CommunityScale", "社区"),
          ("quarter", "QuarterScale", "小区")]


def magnitude(n):
    """量级标注（脱敏：不写真值）"""
    if n == 0:
        return "零"
    if n < 10:
        return "个位数"
    if n < 100:
        return "十级"
    if n < 1000:
        return "百级"
    return "千级"


def main():
    stats, rows, haz = read_scopes()
    print("权威表统计：楼栋", stats["district"]["den"], "街道", len(stats["street"]),
          "社区", len(stats["community"]), "小区", len(stats["quarter"]))
    print("  结构隐患分子(城区) =", stats["district"]["num"], "（与自评表255一致）")

    g = Graph()
    n_ref = n_rule = 0
    for key, scale_uri, cn in LEVELS:
        ref = UR[f"SC_ERef_I1_{key}"]
        rule = UR[f"SC_ER_I1_{key}"]
        if key == "district":
            den, num = stats["district"]["den"], stats["district"]["num"]
        else:
            vals = list(stats[key].values())
            den = max(v[0] for v in vals)
            num = sum(v[1] for v in vals)
        g.add((ref, RDF.type, UR.EvaluationReference))
        g.add((ref, RDFS.label, Literal(f"指标1结构隐患·{cn}尺度四档参考（档次共用ERef_P1）", lang="zh")))
        g.add((ref, UR.forIndicator, UR.Indicator_1))
        g.add((ref, UR.sourceScope, Literal("档次共用·地方自评表口径【待核】", lang="zh")))
        g.add((ref, UR.appliesToScale, UR[f"SpatialScale_{scale_uri}"]))
        g.add((ref, UR.validPeriod, Literal("2025", lang="zh")))
        g.add((ref, UR.direction, Literal("逆向", lang="zh")))
        g.add((ref, UR.reusesBandsOf, UR.ERef_P1))
        g.add((ref, RDFS.comment,
               Literal(f"{cn}尺度：分母{magnitude(den)}、分子{magnitude(num)}"
                       f"（精确值见本地脱敏对照表，不入库）；占比=该单元隐患数÷同层级住宅总栋数", lang="zh")))
        n_ref += 1

        g.add((rule, RDF.type, UR.EvaluationRule))
        g.add((rule, RDFS.label, Literal(f"指标1结构隐患·{cn}尺度评价规则", lang="zh")))
        g.add((rule, UR.evaluates, UR.Indicator_1))
        g.add((rule, UR.evaluationMethod, UR.EvaluationMethod_占比化))
        g.add((rule, UR.evaluationOutput, UR.EvaluationOutput_四级等级))
        g.add((rule, UR.usesReference, ref))
        n_rule += 1
    print(f"生成 {n_ref} 参考值 + {n_rule} 规则（档次共用 ERef_P1，不复制档位）")

    # 本地真值对照（不入库）
    import csv
    LOCAL_TRUTH.parent.mkdir(parents=True, exist_ok=True)
    with LOCAL_TRUTH.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["尺度", "单元名称", "分母(真值)", "分子(真值)"])
        for key, _s, _cn in LEVELS:
            if key == "district":
                w.writerow([key, "全市", stats["district"]["den"], stats["district"]["num"]])
            else:
                for name, (den, num) in sorted(stats[key].items()):
                    w.writerow([key, name, den, num])
    print("本地真值写出", LOCAL_TRUTH.name, "(不入库)")

    # ---- 断言 ----
    ok = True
    def chk(cond, msg):
        nonlocal ok
        print(("  [OK] " if cond else "  [FAIL] ") + msg)
        ok = ok and cond

    chk(n_ref == 4 and n_rule == 4, "四级尺度样板=4 参考值+4 规则")
    for key, scale_uri, cn in LEVELS:
        chk((UR[f"SC_ERef_I1_{key}"], UR.appliesToScale, UR[f"SpatialScale_{scale_uri}"]) in g,
            f"{cn}尺度 appliesToScale 指向正确")
        chk((UR[f"SC_ERef_I1_{key}"], UR.reusesBandsOf, UR.ERef_P1) in g,
            f"{cn}尺度 档次共用 ERef_P1")
    # 权威口径断言
    chk(stats["district"]["num"] == 255, "城区结构隐患分子=255（权威表, 与自评表一致）")
    chk(len(stats["community"]) == 53, "社区数=53（无支油区）")
    chk(len(stats["quarter"]) == 404, "小区数=404")
    txt = g.serialize(format="turtle")
    # 脱敏断言
    maps = sorted(PROJ.glob("01-资料/*/_脱敏映射/编号映射.csv"))
    import csv as _csv
    real_names = set()
    with maps[0].open(encoding="utf-8-sig") as f:
        for row in _csv.DictReader(f):
            v = str(row.get("原名（本地，不入库）", ""))
            if v:
                real_names.add(v.split("/")[-1].strip())
    chk(not [n for n in real_names if n and n in txt], "公开TTL零真名")
    chk(not [n for n in real_names if n and n in Path(__file__).read_text(encoding="utf-8")], "源码零真名")
    chk("\r" not in txt, "CRLF=0")

    assert ok, "断言失败，不写盘"
    with OUT.open("w", encoding="utf-8", newline="\n") as f:
        f.write(txt)
    print("写出", OUT.name, "三元组", len(g))


if __name__ == "__main__":
    main()
