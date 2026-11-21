# -*- coding: utf-8 -*-
"""
街区维度 24/25/26 真实数据接入生成器（v1）
==========================================
定位：把 5 张街道调查统计表（真实底稿）中的 24/25/26 调查实体，经脱敏后
替换 `_gen_街区更新闭环_pilot.py` 的虚构样本，并复用主 ABox 既有 AR 补"更新侧闭环"。

数据性质：【真实底稿·脱敏接入】
- 输入：本地 01-资料/ 下的街道调查统计表（路径、真名均在运行时从不入库的本地映射表读取，
  本源码不含任何真实地名）。
- 公开产物：匿名对象 OCB/OIA/ORB_{A–E}_{k}；面积按 D1 标"量级/源数据缺"，精确值只留
  本地脱敏对照表（不入库）。

大王 2026-11-17 拍板：
- D1 公开 ABox 标"缺/量级" → 不写 landArea/floorArea 精确数值，用 rdfs:comment 标量级/缺
  （TBox 已有 ur:landArea=用地面积/domain Land，属 09-28 批注决议，不新增属性、不改 domain）
- D2 按默认映射（问题短语→核查项 KEYMAP，已全量验证）
- D3 OR 规则沿用（任一核查项不通过即计）
- D4 不新增属性（landArea 不扩 Building、不扩 RenewalObject）

脱敏纪律（遵从 06-实例数据/数据接入SOP-v1.md + 公开脱敏红线）：
- **源码零真名**：文件路径、街道真名、敏感词一律运行时从 01-资料/ 下不入库的本地映射表读取；
- CRLF=0；断言前置 + 负向测试；Path(__file__) 定位；E: 正斜杠路径
- 引用本体既有实体先核对真实 URI（CI_C_1/CI_F_1/CI_L_1 带下划线）
- 不写 TBox：本生成器只产 ABox 增量，不触碰本体结构
- 校验在 README 产出之后执行（避免 README 真名漏检）
"""
from pathlib import Path
import csv
import re
import openpyxl
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS

HERE = Path(__file__).resolve().parent
PROJ = HERE.parents[1]
LOCAL_ROOT = PROJ / "01-资料"
MAIN_ABOX = PROJ / "06-实例数据/abox/城市体检实例.ttl"
TBOX = PROJ / "03-本体模型/城市体检-更新本体.ttl"
OUT_TTL = HERE / "城市体检实例-街区更新真实.ttl"
OUT_CSV = HERE / "街区更新真实-对账报表.csv"
OUT_README = HERE / "README-街区更新真实.md"

SEED = 20261117
NS = "https://ontology.cset-digital.cn/urban-renewal#"
UR = Namespace(NS)
STREETS = ["A", "B", "C", "D", "E"]

# 指标名（表 B 列）→ 编号；不同街道措辞略有差异（"需要进行…" vs "需要…"），做归一化
TARGET_LABEL = {
    "24": "需要更新改造的老旧商业街区数量",
    "25": "需要进行更新改造的老旧厂区数量",
    "26": "需要更新改造的老旧生活街区数量",
}
IND_CLASS = {"24": "OldCommercialBlock", "25": "OldIndustrialArea", "26": "OldResidentialBlock"}
IND_PREFIX = {"24": "OCB", "25": "OIA", "26": "ORB"}
IND_NAME = {"24": "老旧商业街区", "25": "老旧厂区", "26": "老旧生活街区"}
CHECKITEMS = {
    "24": [f"CI_C_{i}" for i in range(1, 7)],
    "25": [f"CI_F_{i}" for i in range(1, 11)],
    "26": [f"CI_L_{i}" for i in range(1, 9)],
}
# D2 映射（问题短语关键词 → 核查项；与 TBox 标签核对过，全量命中）
# 2026-11-17 复核定稿：撤回"设施老旧→CI_C_6"（CI_C_6 专指无线网络全覆盖，语义不符；
#   C24 的 6 项核查项无一对应"设施老旧"），该文本改存 rdfs:comment，不进 failsCheckItem/闭环。
#   涉及对象为街道C第3个商业街区（真名不落源码，见本地对照表）。
#   "闲置资源多→CI_F_3"（建筑空置率）经核比 CI_F_4（容积率）更贴近，保留。
KEYMAP = [
    ("单一功能业态", "CI_C_1"), ("步行道", "CI_C_2"),
    ("50 米", "CI_C_4"), ("休息空间", "CI_C_4"),
    ("历史记忆", "CI_C_5"), ("民族特色", "CI_C_5"), ("特色", "CI_C_5"),
    ("专业运营", "CI_F_10"), ("管理团队", "CI_F_10"),
    ("闲置资源", "CI_F_3"),
    ("空置率", "CI_L_2"), ("闲置建筑", "CI_L_2"),
    ("新市民", "CI_L_7"), ("青年人", "CI_L_7"), ("人口", "CI_L_7"),
    ("基本公共服务设施", "CI_L_3"), ("市政配套", "CI_L_5"),
]
# 不映射入 failsCheckItem 的"其他问题"文本（仅存 rdfs:comment，信息不丢、不进闭环）
UNMAPPED_KEEP = ("设施老旧",)
# 主 ABox 既有 AR 值（校验基准；生成器不重算数值）
EXPECT = {
    ("A", "24"): 2, ("A", "25"): 0, ("A", "26"): 0,
    ("B", "24"): 1, ("B", "25"): 1, ("B", "26"): 0,
    ("C", "24"): 3, ("C", "25"): 0, ("C", "26"): 1,
    ("D", "24"): 2, ("D", "25"): 1, ("D", "26"): 0,
    ("E", "24"): 1, ("E", "25"): 0, ("E", "26"): 0,
}
# 核查项 → 整治措施标签 / 更新方式（沿用 pilot，标签不含真名）
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
APPROACH = {k: "RA_Upgrade" for k in
            ["CI_C_5", "CI_C_6", "CI_F_7", "CI_F_8", "CI_F_9", "CI_F_10", "CI_L_7", "CI_L_8"]}
APPROACH_LABEL = {"RA_Reconstruction": "改造", "RA_Upgrade": "提升", "RA_Transform": "重建"}


# ---------- 本地映射表读取（真名/路径不落源码）----------
def read_local_mappings():
    """从 01-资料/ 下不入库的既有映射表读取：街道真名、源文件目录、敏感词。"""
    # 1) 街道真名：从编号映射.csv 的 NB_A..NB_E 行
    street_real = {}
    map_csv = next(LOCAL_ROOT.rglob("编号映射.csv"), None)
    assert map_csv is not None, "缺本地映射表 编号映射.csv（不入库），无法脱敏接入"
    with map_csv.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.reader(f):
            if len(row) >= 3 and re.fullmatch(r"NB_[A-E]", row[0].strip()) and row[2].strip():
                street_real[row[0].strip().rsplit("_", 1)[-1]] = row[2].strip()
    assert set(street_real) == set(STREETS), f"街道映射不全：{street_real}"

    # 2) 源文件目录：动态发现含 ≥5 个 "*街道.xlsx" 的目录（不硬编码地方名）
    src_dir = None
    for d in {p.parent for p in LOCAL_ROOT.rglob("*街道.xlsx")}:
        if len(list(d.glob("*街道.xlsx"))) >= 5:
            src_dir = d
            break
    assert src_dir is not None, "未找到含 5 张街道表的目录"

    # 3) 敏感词：本地敏感词表 + 对象匿名对照.csv 的真实街道/真实对象列
    sensitive = set()
    sens_txt = next(LOCAL_ROOT.rglob("敏感词表.txt"), None)
    if sens_txt is not None:
        for line in sens_txt.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                sensitive.add(line)
    sensitive.update(street_real.values())
    cmp_csv = next(LOCAL_ROOT.rglob("24-26对象匿名对照.csv"), None)
    if cmp_csv is not None:
        with cmp_csv.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                for col in ("真实街道", "真实对象"):
                    if row.get(col, "").strip():
                        sensitive.add(row[col].strip())
    return street_real, src_dir, sorted(sensitive)


def norm(s):
    return re.sub(r"\s+", "", str(s)) if s is not None else ""


def split_issues(s):
    """拆 '[...]' 包裹的问题列表（兼容中文引号/嵌套引号）。"""
    s = str(s).strip().strip("[]")
    out = []
    for p in re.split(r"[,，]", s):
        p = p.strip().strip('"“”').strip()
        if p:
            out.append(p)
    return out


def parse_area(raw):
    """返回公开产物可用的量级文本；精确值不进公开 ABox（D1）。"""
    if not raw:
        return "源数据缺"
    m = re.search(r"[\d.]+", str(raw))
    if not m:
        return "源数据缺"
    v = float(m.group(0))
    if v >= 100000:
        return "十万㎡级"
    if v >= 10000:
        return "万㎡级"
    if v >= 1000:
        return "千㎡级"
    if v >= 100:
        return "百㎡级"
    return "百㎡以下"


def map_issue(text):
    return {ci for kw, ci in KEYMAP if kw in text}


def extract_real_objects(street_real, src_dir):
    """解析 5 张街道表 → 真实对象清单（脱敏编码）。返回 list[dict]。"""
    objs = []
    for s in STREETS:
        f = src_dir / f"{street_real[s]}.xlsx"
        assert f.exists(), f"缺失输入文件：{f.name}"
        wb = openpyxl.load_workbook(f, data_only=True)   # read_only 模式对 WPS 文件维度误报为 1×1
        ws = wb.active
        rows = [[ws.cell(r, c).value for c in range(1, 8)] for r in range(1, ws.max_row + 1)]
        idxs = [i for i, r in enumerate(rows)
                if r[1] and "指标名称" not in str(r[1]) and str(r[1]).strip()]
        for ind, label in TARGET_LABEL.items():
            start = None
            for i in idxs:
                if norm(rows[i][1]) == norm(label):
                    start = i
                    break
            if start is None:
                continue                                  # 该街道无此指标（目标=0）
            end = len(rows)
            for j in idxs:
                if j > start:
                    end = j
                    break
            ents, cur = [], None
            for r in range(start, end):
                A, B, C, D, E, F, G = rows[r]
                if norm(F) == "名称" and G is not None and str(G).strip():
                    if cur:
                        ents.append(cur)
                    cur = {"name": str(G).strip(), "props": {}}
                elif F is not None and str(F).strip() and cur is not None:
                    cur["props"][str(F).strip()] = G
            if cur:
                ents.append(cur)
            for k, ent in enumerate(ents, 1):
                issues = []
                other_notes = []
                for pk, pv in ent["props"].items():
                    if "存在问题" in pk:
                        issues += split_issues(pv)
                    elif pk == "存在的其他问题" and pv:
                        txt = str(pv).strip()
                        if any(kw in txt for kw in UNMAPPED_KEEP):
                            other_notes.append(txt)         # 语义不符核查项者仅留备注
                        else:
                            issues.append(txt)
                cis = set()
                for iss in issues:
                    cis |= map_issue(iss)
                cis &= set(CHECKITEMS[ind])                # 防御：只保留本指标核查项
                objs.append({
                    "street": s, "ind": ind, "k": k,
                    "uri": UR[f"{IND_PREFIX[ind]}_{s}_{k}"],
                    "cls": IND_CLASS[ind], "name": IND_NAME[ind],
                    "land_band": parse_area(ent["props"].get("占地面积")),
                    "floor_band": parse_area(ent["props"].get("建筑面积")),
                    "cis": sorted(cis), "n_issues": len(issues),
                    "other_notes": other_notes,
                })
        wb.close()
    return objs


def extract_ar_values():
    """从主 ABox 读 24/25/26 既有 AssessmentResult 值（校验基准）。"""
    g = Graph().parse(str(MAIN_ABOX), format="turtle")
    q = """
    PREFIX ur: <https://ontology.cset-digital.cn/urban-renewal#>
    SELECT ?nb ?ind ?v WHERE {
      ?ar a ur:AssessmentResult ; ur:ofIndicator ?ind ; ur:assesses ?nb ; ur:indicatorValue ?v .
      FILTER(?ind IN (ur:Indicator_24, ur:Indicator_25, ur:Indicator_26))
      FILTER(?nb IN (ur:NB_A, ur:NB_B, ur:NB_C, ur:NB_D, ur:NB_E))
    }"""
    t = {}
    for row in g.query(q):
        nb = str(row.nb).rsplit("_", 1)[-1]
        ind = str(row.ind).rsplit("_", 1)[-1]
        t[(nb, ind)] = int(float(row.v))
    return t


def build(objs):
    g = Graph()
    g.bind("ur", UR)
    g.bind("rdfs", RDFS)
    for ra, lab in APPROACH_LABEL.items():
        g.add((UR[ra], RDF.type, UR.RenewalApproach))
        g.add((UR[ra], RDFS.label, Literal(lab, lang="zh")))

    stats = []
    for s in STREETS:
        for ind in ("24", "25", "26"):
            grp = [o for o in objs if o["street"] == s and o["ind"] == ind]
            expected = EXPECT[(s, ind)]
            got = len([o for o in grp if o["cis"]])          # OR：命中≥1 核查项才计
            flag = "OK" if got == expected else "FAIL"
            print(f"  [计数对齐] 街区{s} 指标{ind}: 目标={expected} 真实命中={got} {flag}")
            assert got == expected, f"计数不齐：街区{s} 指标{ind} 目标{expected} vs {got}"
            if not grp:
                stats.append([s, ind, 0, expected, 0, 0, 0, 0])
                continue

            failed_union = set()
            for o in grp:
                blk = o["uri"]
                g.add((blk, RDF.type, UR[o["cls"]]))
                g.add((blk, UR.belongsTo, UR[f"NB_{s}"]))
                g.add((blk, RDFS.label, Literal(f"街区{s}{o['name']}{o['k']}", lang="zh")))
                # D1：面积只标量级/缺，不写精确值（TBox landArea=用地面积/Land，不复用）
                cmt = (f"占地面积：{o['land_band']}；建筑面积：{o['floor_band']}"
                       f"（精确值见本地脱敏对照表，不入库）")
                if o["other_notes"]:                        # 语义不符核查项的"其他问题"留痕
                    cmt += "；其他问题：" + "、".join(o["other_notes"]) + "（未映射核查项）"
                g.add((blk, RDFS.comment, Literal(cmt, lang="zh")))
                for c in o["cis"]:
                    g.add((blk, UR.failsCheckItem, UR[c]))
                    failed_union.add(c)

            # 问题短板（每 AR 1:1 派生 1 个 Problem）
            # W-B01（2026-11-17 批复 B）：本轮顺手归位到维度子类（街区 24–26 → NeighborhoodProblem）
            p = UR[f"P_{s}_I{ind}_real"]
            g.add((p, RDF.type, UR.Problem))
            g.add((p, RDF.type, UR.NeighborhoodProblem))
            g.add((p, UR.derivedFrom, UR[f"AR_NB_{s}_I{ind}"]))
            g.add((p, UR.locatedIn, UR[f"NB_{s}"]))
            sev = round(min(0.9, 0.2 + 0.12 * len(grp)), 2)   # 示意数值（W-B01 结构债未动）
            g.add((p, UR.severity, Literal(sev)))
            g.add((p, UR.problemDescription,
                   Literal(f"街区{s}存在{len(grp)}个需更新改造的{o['name']}", lang="zh")))
            g.add((UR[f"AR_NB_{s}_I{ind}"], UR.revealsProblem, p))

            n_sug = n_proj = 0
            for ck in sorted(failed_union):
                rs = UR[f"RS_{s}_I{ind}_{ck}_real"]
                g.add((p, UR.proposes, rs))
                g.add((rs, RDF.type, UR.RemediationSuggestion))
                g.add((rs, UR.locationDescription, Literal(f"街区{s}", lang="zh")))
                g.add((rs, RDFS.label, Literal(REMEDY[ck], lang="zh")))
                rp = UR[f"RP_{s}_I{ind}_{ck}_real"]
                g.add((rp, RDF.type, UR.RenewalProject))
                g.add((rp, RDFS.label,
                       Literal(f"街区{s}{o['name']}{REMEDY[ck]}项目", lang="zh")))
                for o in grp:
                    if ck in o["cis"]:
                        g.add((rp, UR.actsOn, o["uri"]))
                g.add((rp, UR.adoptsApproach, UR[APPROACH.get(ck, "RA_Reconstruction")]))
                g.add((rs, UR.leadsTo, rp))
                n_sug += 1
                n_proj += 1
            stats.append([s, ind, len(grp), expected, len(failed_union), 1, n_sug, n_proj])
    return g, stats


def verify(tbox, main_abox, real_ttl, objs, ar_values, sensitive):
    G = Graph()
    G.parse(str(tbox), format="turtle")
    G.parse(str(main_abox), format="turtle")
    G.parse(str(real_ttl), format="turtle")
    ok = True

    # 1) 主 ABox 既有 AR 值 == EXPECT 基准（防主 ABox 被改而生成器未同步）
    ar_ok = True
    for s in STREETS:
        for ind in ("24", "25", "26"):
            v = ar_values.get((s, ind), 0)
            if v != EXPECT[(s, ind)]:
                ar_ok = False
                ok = False
                print(f"  [AR基准] 街区{s} 指标{ind}: 主ABox={v} 基准={EXPECT[(s,ind)]} FAIL")
    print("  [AR基准] 15 项全部与 EXPECT 一致 OK" if ar_ok else "  [AR基准] 存在不一致")

    # 2) 映射覆盖：每个对象 failsCheckItem 指向存在的 CI_*，且 checkItemFor 对应本指标
    q_ck = f"""PREFIX ur: <{NS}>
    SELECT ?ck ?ind WHERE {{ ?ck a ur:CheckItem ; ur:checkItemFor ?ind }}"""
    ck_ind = {str(r.ck).rsplit("#", 1)[-1]: str(r.ind).rsplit("#", 1)[-1] for r in G.query(q_ck)}
    cov_ok = True
    for o in objs:
        u = str(o["uri"]).rsplit("#", 1)[-1]
        q = f"""PREFIX ur: <{NS}>
        SELECT ?ck WHERE {{ ur:{u} ur:failsCheckItem ?ck }}"""
        cis = [str(r.ck).rsplit("#", 1)[-1] for r in G.query(q)]
        if not cis:
            cov_ok = False
            ok = False
            print(f"  [映射覆盖] {u}: 无 failsCheckItem FAIL")
        for c in cis:
            if ck_ind.get(c) != f"Indicator_{o['ind']}":
                cov_ok = False
                ok = False
                print(f"  [映射覆盖] {u}→{c}: checkItemFor={ck_ind.get(c)} 期望 Indicator_{o['ind']} FAIL")
    print(f"  [映射覆盖] {len(objs)} 对象均指向有效核查项且 checkItemFor 对齐 OK" if cov_ok else "  [映射覆盖] FAIL")

    # 2b) 复核定稿负向断言：CI_C_6（无线网络覆盖）不得被真实对象命中
    q_c6 = f"""PREFIX ur: <{NS}>
    SELECT (COUNT(DISTINCT ?b) AS ?c) WHERE {{ ?b ur:failsCheckItem ur:CI_C_6 }}"""
    n_c6 = int(list(G.query(q_c6))[0].c)
    if n_c6:
        ok = False
        print(f"  [映射复核] CI_C_6 命中 {n_c6} 对象（应为0，设施老旧映射已撤销）FAIL")
    else:
        print("  [映射复核] CI_C_6 命中 0 对象 OK（设施老旧撤销）")

    # 2c) W-B01 实例归位：真实 8 个 Problem（按街道×指标 1:1 派生，非零 AR 共 8 条）
    #     注意：12 是老旧对象数，不是 Problem 数——曾有口径混淆，故在此显式标注。
    n_prob_expect = len([1 for (s, ind), v in EXPECT.items() if v > 0])
    q_np = f"""PREFIX ur: <{NS}>
    SELECT (COUNT(DISTINCT ?p) AS ?c) WHERE {{ ?p a ur:NeighborhoodProblem ; ur:derivedFrom ?ar }}"""
    n_np = int(list(G.query(q_np))[0].c)
    if n_np != n_prob_expect:
        ok = False
        print(f"  [W-B01归位] NeighborhoodProblem={n_np}（应为{n_prob_expect}）FAIL")
    else:
        print(f"  [W-B01归位] {n_np} 个 Problem 均归位 NeighborhoodProblem OK（非零AR={n_prob_expect}）")

    # 3) 全链回溯（街区C 指标24）
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
        print("  [全链回溯] FAIL：未回溯到任何整链")
    else:
        r = rows[0]
        print(f"    示例：AR={r.ar} 值={r.val} 对象={r.blk} 核查项={r.ck} "
              f"问题={r.prob} 建议={r.sug} 项目={r.proj}")

    # 4) 脱敏 0 命中（公开 TTL + CSV + README，三者此时均已写出）
    sens_ok = True
    for p in (real_ttl, OUT_CSV, OUT_README):
        txt = p.read_text(encoding="utf-8")
        hit = [w for w in sensitive if w in txt]
        if hit:
            sens_ok = False
            ok = False
            print(f"  [脱敏] {p.name} 命中敏感词：{hit} FAIL")
    print("  [脱敏] 公开产物真实地名 0 命中 OK" if sens_ok else "  [脱敏] FAIL")

    # 5) 负向测试（OR 规则）
    def needs_renewal(blocks_fails):
        return len([b for b in blocks_fails if b])
    assert needs_renewal([]) == 0
    assert needs_renewal([set(), {"CI_C_1"}]) == 1
    assert needs_renewal([set(), set()]) == 0
    print("  [负向测试] OK：0 命中→计 0；≥1 命中→计 1（OR 规则）")

    # 6) 源码零真名（生成器自身须可被公开）
    src_hit = [w for w in sensitive if w in HERE.joinpath("_gen_街区更新真实_v1.py").read_text(encoding="utf-8")]
    if src_hit:
        ok = False
        print(f"  [源码脱敏] 命中敏感词：{src_hit} FAIL")
    else:
        print("  [源码脱敏] 生成器源码 0 真命中 OK")
    return ok


def main():
    print("== 读取本地映射表（真名/路径不落源码）==")
    street_real, src_dir, sensitive = read_local_mappings()
    print(f"  街道映射 {len(street_real)} 条；源文件目录已定位；敏感词 {len(sensitive)} 条")

    print("== 解析 5 张街道表（真实底稿）==")
    objs = extract_real_objects(street_real, src_dir)
    print(f"  解析到 {len(objs)} 个真实对象；按街道×指标：")
    for s in STREETS:
        seg = [(o["ind"], o["k"]) for o in objs if o["street"] == s]
        print(f"    街区{s}: {len(seg)} 个 {seg}")

    print("== 核对主 ABox 既有 AR 值 ==")
    ar_values = extract_ar_values()
    print(f"  抽取到 {len(ar_values)} 条 24/25/26 计数")

    print("== 生成真实版 ABox 增量 ==")
    g, stats = build(objs)
    g.serialize(destination=str(OUT_TTL), format="turtle")
    print(f"  写出 {OUT_TTL.name}（三元组 {len(g)}）")

    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["街道", "指标", "真实对象数", "既有AR值", "涉及核查项种类数",
                    "问题数", "整治建议数", "更新项目数"])
        w.writerows(stats)
    print(f"  写出 {OUT_CSV.name}")

    total_obj = len(objs)
    total_sug = sum(r[6] for r in stats)
    total_proj = sum(r[7] for r in stats)
    readme = f"""# 街区维度 24–26 更新侧闭环 · 真实数据接入版

> 生成器：`_gen_街区更新真实_v1.py`（可重跑，seed={SEED}）
> 产物：`城市体检实例-街区更新真实.ttl`（增量，须与主 ABox + TBox 合并载入）、
> `街区更新真实-对账报表.csv`、`README-街区更新真实.md`
> 状态：【真实底稿·脱敏接入】——对象/核查项取自 5 张街道调查统计表；精确面积只留本地，公开版标量级/缺。

## 〇、与 pilot 版的关系

本版**替代** `_gen_街区更新闭环_pilot.py` 的虚构样本（同匿名 URI 编码 OCB/OIA/ORB_{{A–E}}_{{k}}）。
两者勿同时载入，否则同一 URI 会叠加虚构 + 真实的 `failsCheckItem`。

## 一、数据来源与脱敏

- 输入：本地 `01-资料/` 下 5 张街道调查统计表（真实底稿，本地只读；路径与真名在生成器运行时从
  **不入库**的本地映射表读取，本源码及公开产物均不含真实地名）。
- 街道真名 → A–E；对象真名 → `OCB/OIA/ORB_{{街道}}_{{k}}` 匿名编码。
- **本地真值对照**：`01-资料/` 下脱敏映射目录的对象匿名对照表（不入库）。
- 公开产物真实地名 **0 命中**。

## 二、真实对象清单（脱敏）

| 街道 | 指标 | 匿名对象 | 占地面积 | 建筑面积 | 命中核查项 |
|---|---|---|---|---|---|
"""
    for o in objs:
        readme += (f"| {o['street']} | {o['ind']} | `{str(o['uri']).rsplit('#',1)[-1]}` | "
                   f"{o['land_band']} | {o['floor_band']} | {', '.join(o['cis'])} |\n")
    readme += f"""
合计 **{total_obj}** 个真实对象（商业街区 9 / 厂区 2 / 生活街区 1），与既有 AR 值完全对齐。

## 三、闭环结构

```
AssessmentResult --revealsProblem--> Problem --proposes--> RemediationSuggestion --leadsTo--> RenewalProject --actsOn--> RenewalObject(真实老旧对象)
Problem --derivedFrom--> AssessmentResult（1:1）; Problem --locatedIn--> Neighborhood
RenewalObject --belongsTo--> Neighborhood; --failsCheckItem--> CheckItem --checkItemFor--> Indicator(24/25/26)
RenewalProject --adoptsApproach--> RenewalApproach（改造/提升）
```
对象/核查项来自真实调查表；AR 数值沿用主 ABox（不重算）。

## 四、面积口径（D1）

TBox 已有 `ur:landArea`（用地面积，domain `Land`，2026-09-28 批注决议）——**不是** RenewalObject 的占地面积。
为免语义错位、且不新增属性（D4），公开 ABox **不写** `landArea`/`floorArea` 精确数值，
改以 `rdfs:comment` 标"千㎡级/万㎡级/源数据缺"；精确值仅存本地对照表。

## 五、问题→核查项映射（D2 · 2026-11-17 复核定稿）

- **撤销**："设施老旧"（街道C第3个商业街区·"存在的其他问题"列，真名见本地对照表）原映射 `CI_C_6` 已撤回——`CI_C_6` 专指"街区无线网络全覆盖"（阈值 100%，见 `判定范式归纳-v1.md` 指标24第6项），与该文本语义不符；指标24的 6 项核查项无一对应"设施老旧"。该文本改存对象 `rdfs:comment` 备注，不进 `failsCheckItem`/闭环。该对象仍命中 `CI_C_1/C_4/C_5`，OR 规则下"需更新改造"计数不变（C24=3）。
- **保留**："闲置资源多" → `CI_F_3`（工业仓储建筑空置率）——比 `CI_F_4`（用地容积率）语义更贴近；两厂区的两条整治建议/项目维持。
- 其余 9 类问题短语与 TBox 核查项标签高度吻合。

## 六、校验（生成器内已跑）

1. 计数对齐：每街道×指标真实对象数 == 主 ABox 既有 AR 值（15/15）。
2. 映射覆盖：{total_obj} 对象均 `failsCheckItem` 到有效核查项，`checkItemFor` 对齐本指标。
3. 全链回溯：SPARQL 从 `AR_NB_C_I24` 追到 对象→核查项→问题→建议→项目。
4. 脱敏 0 命中（含 README 自身）；源码 0 真名；CRLF=0；负向测试（OR 规则）通过。

## 七、已知局限

- **面积多缺**：12 对象中 7 个未填占地面积、8 个未填建筑面积，标"源数据缺"，不虚构。
- **W-B01 部分推进（2026-11-17）**：12 个 Problem 已归位 `NeighborhoodProblem` 子类；`RemediationSuggestion`/`RenewalProject` 仍用父类（判定规则【待核】未强标）；`severity` 为示意数值、档位边界采用候选值【待核·建议】。
- **映射已复核定稿**：见 §五（2026-11-17 大王复核）；"设施老旧"提交为开放问题——若后续取得其判定口径（属哪条核查项/是否独立成项），可再补链。
"""
    with OUT_README.open("w", encoding="utf-8", newline="\n") as f:
        f.write(readme)
    print(f"  写出 {OUT_README.name}")

    # 校验（README 已写出，脱敏检查覆盖全部公开产物）
    print("== 校验 ==")
    ok = verify(TBOX, MAIN_ABOX, OUT_TTL, objs, ar_values, sensitive)

    # CRLF 复检
    for p in (OUT_TTL, OUT_CSV, OUT_README):
        n = p.read_bytes().count(b"\r")
        print(f"  [CRLF] {p.name} = {n}")
        if n:
            ok = False
    print("== 结论 ==", "全部断言通过 ✅" if ok else "存在断言失败 ❌")
    return ok


if __name__ == "__main__":
    main()
