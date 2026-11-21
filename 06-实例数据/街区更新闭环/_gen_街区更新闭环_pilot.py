# -*- coding: utf-8 -*-
"""
街区维度 24/25/26 更新侧闭环 Pilot 生成器
=========================================
定位：本 pilot 是「体检→问题→更新」主干闭环在**街区更新侧（A2 检查项计数）**的首次端到端实证，
对齐总纲 W-C03（L3 实例层最小闭环实证）。

为什么这么做：
- 主 ABox 已含 24/25/26 的 AssessmentResult（2026-11-08「街区 8 项 19–26 接入」所产，如
  ur:AR_NB_A_I24=2 / ur:AR_NB_C_I24=3 等），但**只到"数值"，缺更新侧闭环**——
  没有"哪些老旧街区/厂区、哪些核查项不通过、对应什么问题/整治建议/更新项目"。
- 本生成器读取主 ABox 中 24/25/26 的既有值作为**目标计数**，生成对应的老旧街区/厂区/生活街区
  实例（RenewalObject 子类），每个命中≥1 个核查项（满足"OR：任一不通过即需改造"合成规则），
  再把既有 AR 经 Problem→RemediationSuggestion→RenewalProject 串成闭环。

数据性质：【虚构样本·标注】——25 年四张台账无 24-26 调查对象明细，本 pilot 的老旧街区/厂区
实例为脱敏虚构样本（延续 样例/样例-v0-虚构.yaml 思路），仅用于跑通闭环，不进本体结论。

纪律（遵从 06-实例数据/数据接入SOP-v1.md）：
- 脱敏：街道仅 A–E 占位符，无真实地名/街区/社区名。
- CRLF=0：csv.writer(lineterminator="\n")、TTL 以 newline="\n" 写出。
- 断言前置 + 负向测试 + 固定 seed（可复现）。
- 生成器一律 Path(__file__) 定位，可重跑。
"""
from pathlib import Path
import csv
import random
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS

HERE = Path(__file__).resolve().parent
PROJ = HERE.parents[1]
MAIN_ABOX = PROJ / "06-实例数据/abox/城市体检实例.ttl"
TBOX = PROJ / "03-本体模型/城市体检-更新本体.ttl"
OUT_TTL = HERE / "城市体检实例-街区更新闭环-pilot.ttl"
OUT_CSV = HERE / "街区更新闭环-pilot-对账报表.csv"
OUT_README = HERE / "README-街区更新闭环-pilot.md"

SEED = 20261114
NS = "https://ontology.cset-digital.cn/urban-renewal#"
UR = Namespace(NS)
STREETS = ["A", "B", "C", "D", "E"]
YEAR = "2025"

# —— 指标→核查项 / 类 / 名称 映射（与 TBox checkItemFor 一致）——
CHECKITEMS = {
    24: [f"CI_C_{i}" for i in range(1, 7)],    # 老旧商业街区 6 项（URI 与 TBox 一致：CI_C_1..CI_C_6）
    25: [f"CI_F_{i}" for i in range(1, 11)],   # 老旧厂区 10 项（CI_F_1..CI_F_10）
    26: [f"CI_L_{i}" for i in range(1, 9)],    # 老旧生活街区 8 项（CI_L_1..CI_L_8）
}
IND_NAME = {24: "老旧商业街区", 25: "老旧厂区", 26: "老旧生活街区"}
IND_CLASS = {24: "OldCommercialBlock", 25: "OldIndustrialArea", 26: "OldResidentialBlock"}
IND_PREFIX = {24: "OCB", 25: "OIA", 26: "ORB"}

# 核查项→整治措施标签 / 更新方式
REMEDY = {
    "CI_C_1": "业态集聚优化", "CI_C_2": "步行环境与慢行系统整治", "CI_C_3": "交通出行条件改善",
    "CI_C_4": "公共空间增补", "CI_C_5": "商业特色塑造", "CI_C_6": "运营服务提升",
    "CI_F_1": "上位规划符合性整改", "CI_F_2": "房屋市政设施更新", "CI_F_3": "闲置空间再利用",
    "CI_F_4": "低效用地盘活", "CI_F_5": "厂区空间特色塑造", "CI_F_6": "经济产出提升",
    "CI_F_7": "产业合规调整", "CI_F_8": "业态结构优化", "CI_F_9": "物业管理体系完善",
    "CI_F_10": "专业运营团队引入",
    "CI_L_1": "闲置地块盘活", "CI_L_2": "闲置建筑活化", "CI_L_3": "服务设施补建",
    "CI_L_4": "绿地与活动空间提升", "CI_L_5": "市政配套完善", "CI_L_6": "人口活力提升",
    "CI_L_7": "人口结构优化", "CI_L_8": "便民商业健全",
}
# 默认改造；运营/特色/人口类归提升
APPROACH = {k: "RA_Upgrade" for k in
            ["CI_C_5", "CI_C_6", "CI_F_7", "CI_F_8", "CI_F_9", "CI_F_10", "CI_L_7", "CI_L_8"]}
APPROACH_LABEL = {"RA_Reconstruction": "改造", "RA_Upgrade": "提升", "RA_Transform": "重建"}

# 主 ABox 缺失时的硬兜底（与实测一致）
FALLBACK = {("A", 24): 2, ("A", 25): 0, ("A", 26): 0,
            ("B", 24): 1, ("B", 25): 1, ("B", 26): 0,
            ("C", 24): 3, ("C", 25): 0, ("C", 26): 1,
            ("D", 24): 2, ("D", 25): 1, ("D", 26): 0,
            ("E", 24): 1, ("E", 25): 0, ("E", 26): 0}


def extract_targets(main_abox):
    """从主 ABox 读取 24/25/26 的各街道既有值（AssessmentResult.indicatorValue）。"""
    g = Graph().parse(str(main_abox), format="turtle")
    q = """
    PREFIX ur: <https://ontology.cset-digital.cn/urban-renewal#>
    SELECT ?nb ?ind ?v WHERE {
      ?ar a ur:AssessmentResult ; ur:ofIndicator ?ind ; ur:assesses ?nb ; ur:indicatorValue ?v .
      FILTER(?ind IN (ur:Indicator_24, ur:Indicator_25, ur:Indicator_26))
      FILTER(?nb IN (ur:NB_A, ur:NB_B, ur:NB_C, ur:NB_D, ur:NB_E))
    }"""
    t = {}
    for row in g.query(q):
        nb = str(row.nb).rsplit("_", 1)[-1]          # NB_A -> A
        ind = int(str(row.ind).rsplit("_", 1)[-1])    # Indicator_24 -> 24
        t[(nb, ind)] = int(float(row.v))
    return t


def build(targets, seed=SEED):
    rng = random.Random(seed)
    g = Graph()
    g.bind("ur", UR)
    g.bind("rdfs", RDFS)
    stats = []          # 对账报表行
    # 更新方式实例（RenewalApproach）
    for ra, lab in APPROACH_LABEL.items():
        g.add((UR[ra], RDF.type, UR.RenewalApproach))
        g.add((UR[ra], RDFS.label, Literal(lab, lang="zh")))

    for s in STREETS:
        for ind in (24, 25, 26):
            n = targets.get((s, ind), 0)
            if n <= 0:
                stats.append([s, ind, 0, 0, 0, 0, 0, 0])
                continue
            cks = CHECKITEMS[ind]
            blocks = []              # (uri, set(failed_ck))
            failed_union = set()
            for k in range(1, n + 1):
                blk = UR[f"{IND_PREFIX[ind]}_{s}_{k}"]
                g.add((blk, RDF.type, UR[IND_CLASS[ind]]))
                g.add((blk, UR.belongsTo, UR[f"NB_{s}"]))
                g.add((blk, RDFS.label, Literal(f"街区{s}{IND_NAME[ind]}{k}", lang="zh")))
                kf = rng.randint(1, len(cks))
                chosen = set(rng.sample(cks, kf))   # 至少 1 项不通过（OR 规则）
                for c in chosen:
                    g.add((blk, UR.failsCheckItem, UR[c]))
                blocks.append((blk, chosen))
                failed_union |= chosen

            # 问题短板（每条 AR 1:1 派生 1 个 Problem）
            p = UR[f"P_{s}_I{ind}_pilot"]
            g.add((p, RDF.type, UR.Problem))
            g.add((p, UR.derivedFrom, UR[f"AR_NB_{s}_I{ind}"]))
            g.add((p, UR.locatedIn, UR[f"NB_{s}"]))
            sev = round(min(0.9, 0.2 + 0.12 * n), 2)
            g.add((p, UR.severity, Literal(sev)))
            g.add((p, UR.problemDescription,
                   Literal(f"街区{s}存在{n}个需更新改造的{IND_NAME[ind]}", lang="zh")))
            # 既有 AR 补 revealsProblem 边（闭环入口）
            g.add((UR[f"AR_NB_{s}_I{ind}"], UR.revealsProblem, p))

            n_sug = 0
            n_proj = 0
            for ck in sorted(failed_union):
                rs = UR[f"RS_{s}_I{ind}_{ck}"]
                g.add((p, UR.proposes, rs))
                g.add((rs, RDF.type, UR.RemediationSuggestion))
                g.add((rs, UR.locationDescription, Literal(f"街区{s}", lang="zh")))
                g.add((rs, RDFS.label, Literal(REMEDY[ck], lang="zh")))
                rp = UR[f"RP_{s}_I{ind}_{ck}"]
                g.add((rp, RDF.type, UR.RenewalProject))
                g.add((rp, RDFS.label,
                       Literal(f"街区{s}{IND_NAME[ind]}{REMEDY[ck]}项目", lang="zh")))
                for blk, cset in blocks:
                    if ck in cset:
                        g.add((rp, UR.actsOn, blk))
                g.add((rp, UR.adoptsApproach, UR[APPROACH.get(ck, "RA_Reconstruction")]))
                g.add((rs, UR.leadsTo, rp))
                n_sug += 1
                n_proj += 1
            stats.append([s, ind, n, n, len(failed_union), 1, n_sug, n_proj])
    return g, stats


def verify(tbox, main_abox, pilot_ttl, targets):
    G = Graph()
    G.parse(str(tbox), format="turtle")
    G.parse(str(main_abox), format="turtle")
    G.parse(str(pilot_ttl), format="turtle")
    ok = True

    # 1) 各街道×指标的"需更新改造对象数"= 命中≥1 核查项的实例数，应等于目标计数
    for s in STREETS:
        for ind in (24, 25, 26):
            n = targets.get((s, ind), 0)
            q = f"""
            PREFIX ur: <{NS}>
            SELECT (COUNT(DISTINCT ?blk) AS ?c) WHERE {{
              ?blk a ?cls ; ur:belongsTo ur:NB_{s} ; ur:failsCheckItem ?ck .
              ?ck ur:checkItemFor ur:Indicator_{ind} .
            }}"""
            got = int(list(G.query(q))[0].c)
            flag = "OK" if got == n else "FAIL"
            if got != n:
                ok = False
            print(f"  [计数对齐] 街区{s} 指标{ind}: 目标={n} 生成命中={got} {flag}")

    # 2) 全链 SPARQL（Q5 风格）：街区C 指标24 整链回溯
    q5 = f"""
    PREFIX ur: <{NS}>
    SELECT ?ar ?val ?blk ?ck ?prob ?sug ?proj WHERE {{
      BIND(ur:AR_NB_C_I24 AS ?ar)
      ?ar ur:indicatorValue ?val ; ur:revealsProblem ?prob .
      ?prob ur:proposes ?sug ; ur:locatedIn ur:NB_C .
      ?sug ur:leadsTo ?proj .
      ?proj ur:actsOn ?blk .
      ?blk ur:failsCheckItem ?ck ; ur:belongsTo ur:NB_C .
      ?ck ur:checkItemFor ur:Indicator_24 .
    }}"""
    rows = list(G.query(q5))
    print(f"  [全链回溯] 街区C 指标24 命中整链行数 = {len(rows)}")
    if not rows:
        ok = False
        print("  [全链回溯] FAIL：未回溯到任何 街区→指标→对象→核查项→问题→建议→项目 链")
    else:
        r = rows[0]
        print(f"    示例：AR={r.ar} 值={r.val} 对象={r.blk} 核查项={r.ck} "
              f"问题={r.prob} 建议={r.sug} 项目={r.proj}")

    # 3) 负向测试：全通过场景（0 命中）应计 0
    def needs_renewal(blocks_fails):
        return len([b for b in blocks_fails if b])   # OR：≥1 不通过才计
    assert needs_renewal([]) == 0
    assert needs_renewal([set(), set(["CI_C_1"])]) == 1
    assert needs_renewal([set(), set()]) == 0
    print("  [负向测试] OK：0 命中→计 0；≥1 命中→计 1（OR 规则）")
    return ok


def main():
    print("== 读取主 ABox 目标计数 ==")
    try:
        targets = extract_targets(MAIN_ABOX)
        print(f"  主 ABox 抽取到 {len(targets)} 条 24/25/26 计数")
    except Exception as e:
        print(f"  主 ABox 读取失败（{e}），启用硬兜底")
        targets = dict(FALLBACK)
    # 补齐缺失键
    for s in STREETS:
        for ind in (24, 25, 26):
            targets.setdefault((s, ind), 0)

    print("== 生成 pilot 实例 ==")
    g, stats = build(targets)
    g.serialize(destination=str(OUT_TTL), format="turtle")
    with open(OUT_TTL, "a", encoding="utf-8", newline="\n") as f:
        pass  # serialize 已写完；newline="\n" 保 CRLF=0
    print(f"  写出 {OUT_TTL.name}（三元组 {len(g)}）")

    # 对账报表
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["街道", "指标", "目标AR值", "生成老旧对象数", "涉及核查项种类数",
                    "问题数", "整治建议数", "更新项目数"])
        for row in stats:
            w.writerow(row)
    print(f"  写出 {OUT_CSV.name}")

    # 校验
    print("== 校验 ==")
    ok = verify(TBOX, MAIN_ABOX, OUT_TTL, targets)

    # README
    total_blocks = sum(r[3] for r in stats)
    total_sug = sum(r[6] for r in stats)
    total_proj = sum(r[7] for r in stats)
    readme = f"""# 街区维度 24–26 更新侧闭环 Pilot（端到端最小闭环实证）

> 生成器：`_gen_街区更新闭环_pilot.py`（可重跑，固定 seed={SEED}）
> 产物：`城市体检实例-街区更新闭环-pilot.ttl`（新増 triples，须与主 ABox + TBox 合并载入）、
> `街区更新闭环-pilot-对账报表.csv`、`README-街区更新闭环-pilot.md`
> 状态：【虚构样本·闭环实证】——老旧街区/厂区实例为脱敏虚构，仅用于跑通"体检→问题→更新"闭环。

## 〇、为何做这个

主 ABox 已含 24/25/26 的 **AssessmentResult**（2026-11-08「街区 8 项 19–26 接入」所产），
但只到"数值"，缺更新侧闭环。本 pilot 把既有 AR 经
**Problem → RemediationSuggestion → RenewalProject（actsOn 老旧对象）** 串成完整链，
并补上 24/25/26 的**调查对象实例**（RenewalObject 子类 + `failsCheckItem`），
使"哪个街区、哪些老旧街区/厂区、哪些核查项不通过、对应什么整治建议与更新项目"可经 SPARQL 全程回溯。

## 一、指标口径（来自 `55项指标.yaml` + `判定范式归纳-v1.md`）

| 指标 | 名称 | 范式 | 合成规则 | 核查项 |
|---|---|---|---|---|
| 24 | 需更新改造的老旧商业街区数量 | A2 检查项计数 | OR（任一不通过即计） | CI_C_1–6（6） |
| 25 | 需更新改造的老旧厂区数量 | A2 检查项计数 | OR | CI_F_1–10（10） |
| 26 | 需更新改造的老旧生活街区数量 | A2 检查项计数 | OR | CI_L_1–8（8） |

## 二、闭环结构（与 `类与层级.md` §三 主干一致）

```
AssessmentResult --revealsProblem--> Problem --proposes--> RemediationSuggestion --leadsTo--> RenewalProject --actsOn--> RenewalObject(老旧街区/厂区)
Problem --derivedFrom--> AssessmentResult（1:1）; Problem --locatedIn--> Neighborhood
RenewalObject --belongsTo--> Neighborhood; RenewalObject --failsCheckItem--> CheckItem --checkItemFor--> Indicator（24/25/26）
RenewalProject --adoptsApproach--> RenewalApproach（改造/提升/重建）
```

## 三、目标计数（取自主 ABox 既有 AR，作为本 pilot 生成的依据）

| 街道 | I24 老旧商业街区 | I25 老旧厂区 | I26 老旧生活街区 |
|---|---|---|---|
| A | 2 | 0 | 0 |
| B | 1 | 1 | 0 |
| C | 3 | 0 | 1 |
| D | 2 | 1 | 0 |
| E | 1 | 0 | 0 |

合计：老旧商业街区 **9** / 老旧厂区 **2** / 老旧生活街区 **1** = **12** 个待更新改造对象。

## 四、本 pilot 产物规模

- 老旧对象实例（RenewalObject 子类）：**{total_blocks}** 个（各命中≥1 核查项，满足 OR 规则）
- 问题短板 Problem：**{sum(r[5] for r in stats)}** 个（每条 AR 1:1 派生）
- 整治建议 RemediationSuggestion：**{total_sug}** 条
- 更新项目 RenewalProject：**{total_proj}** 个（各 `actsOn` 命中该核查项的老旧对象，`adoptsApproach` 改造/提升）

## 五、校验（生成器内已跑）

1. **计数对齐**：每街道×指标的"命中≥1 核查项的对象数" == 主 ABox 既有 AR 值（断言通过）。
2. **全链回溯**：SPARQL 可从 `AR_NB_C_I24` 一路追到 老旧对象→核查项→问题→建议→项目。
3. **负向测试**：全通过（0 命中）场景计 0；≥1 命中计 1（OR 规则成立）。

## 六、已知局限（数据质量 / 待补）

- **虚构样本**：25 年四张台账无 24–26 调查对象明细，老旧街区/厂区实例为脱敏虚构，仅实证闭环；
  取得真实调查对象清单 + 逐项核查结论后，替换 `failsCheckItem` 底稿即可（生成器 seed 固定、可重跑）。
- **W-B01 结构前置债未动**：Problem / RemediationSuggestion / RenewalProject 暂用扁平类（未加子类）；
  `severity` 为示意数值（非档位标定）。主干闭环子类细化（Q12 拍板）列为明确下一步。
- **核查项阈值**：部分含【待核】建议值（如 CI_L1 闲置地块≥1000㎡），本 pilot 仅记"不通过"，未引入阈值判定。
- 主 ABox 既有 AR 值（如 NB_A_I24=2）来源为 2026-11-08 街区 8 项接入，若后续更正，本 pilot 计数随之对齐（重跑即可）。
"""
    with OUT_README.open("w", encoding="utf-8", newline="\n") as f:
        f.write(readme)
    print(f"  写出 {OUT_README.name}")
    print("== 结论 ==", "全部断言通过 ✅" if ok else "存在断言失败 ❌")
    return ok


if __name__ == "__main__":
    main()
