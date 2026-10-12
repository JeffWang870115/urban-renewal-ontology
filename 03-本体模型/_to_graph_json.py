# -*- coding: utf-8 -*-
"""城市体检-更新本体 → 前端图谱 JSON 导出器（阶段一数据管道）

输入（同源）：
  03-本体模型/城市体检-更新本体.ttl      类 / 属性 / ABox 个体的权威机读源
  03-本体模型/类与层级.md                16 个顶层类（§一）+ 支撑父类（§2.9、§三）
  04-指标映射/55项指标.yaml              55 项指标的详情

输出：
  05-产出/原型方案/原型/data/ontology.json   机读数据
  05-产出/原型方案/原型/data/ontology.js     同上，包成 window.__ONTOLOGY__（供 file:// 直接打开）

设计约定：
  - 节点与边一律以 ttl 为准；md 只提供中文名与“说明 / 来源”文字。
  - 带**防漂移断言**：md 顶层类须与 ttl 对得上、指标数须与 yaml 对齐、
    每个类须有中文标签、六域映射须覆盖全部顶层类、
    **tsl 中“被 subClassOf 引用但未声明”的类必须能全部在 md 里找到中文名**。
  - 写文件一律 newline='\\n'（Windows 下防 CRLF 污染）。

⚠ 已知数据缺口（脚本会报出，不掩盖）：
  ttl 中有若干类被 rdfs:subClassOf 引用，但自身没有 owl:Class 声明
  （见 warnings.undeclaredParents）。本脚本按 md 中文名补齐为 declared=false 的节点，
  使前端树完整；**根因需修 03-本体模型/_gen_ttl.py，属结构性变更，待决议**。
"""
import json
import re
import sys
from pathlib import Path

from rdflib import Graph, RDF, RDFS, OWL, URIRef
import yaml

ROOT = Path(__file__).resolve().parent.parent
TTL = ROOT / "03-本体模型" / "城市体检-更新本体.ttl"
MD_CLASS = ROOT / "03-本体模型" / "类与层级.md"
YAML = ROOT / "04-指标映射" / "55项指标.yaml"
OUT_DIR = ROOT / "05-产出" / "原型方案" / "原型" / "data"

NS = "https://ontology.cset-digital.cn/urban-renewal#"

# 语义域（视觉约定，2026-10-11 大王认可）—— 顶层类 → 域
DOMAIN_OF = {
    "ExaminationActivity": "core", "AssessmentResult": "core", "Problem": "core",
    "RemediationSuggestion": "core", "RenewalProject": "core",
    "Indicator": "metric", "DataObject": "metric",
    "Dimension": "axis", "IndicatorCategory": "axis",
    "SpatialUnit": "space",
    "RenewalObject": "renew", "RenewalApproach": "renew", "Actor": "renew", "Fund": "renew",
    "PolicyStandard": "policy",
    "TimePeriod": "neutral",
}
DOMAIN_CN = {
    "core": "主干闭环", "metric": "指标内核", "axis": "指标双轴",
    "space": "空间主轴", "renew": "更新要素", "policy": "政策依据", "neutral": "通用",
}
# 技术构件：owl:unionOf 包装类，非概念类，前端图谱默认隐藏
TECHNICAL = {"DataObjectRoleUnion"}

BACKBONE = [
    ("ExaminationActivity", "AssessmentResult", "produces", "产生"),
    ("AssessmentResult", "Problem", "revealsProblem", "揭示"),
    ("Problem", "RemediationSuggestion", "proposes", "提出"),
    ("RemediationSuggestion", "RenewalProject", "leadsTo", "立项"),
    ("Problem", "RenewalProject", "triggers", "直通"),
]


def die(msg: str):
    print(f"[FAIL] {msg}", file=sys.stderr)
    sys.exit(1)


def split_uri(u) -> str:
    s = str(u)
    return s.split("#", 1)[1] if "#" in s else s


def parse_md():
    """返回 (顶层类, 支撑父类中文名)。全部取自 类与层级.md，保证同源。"""
    text = MD_CLASS.read_text(encoding="utf-8")
    lines = text.splitlines()

    # §一 顶层类表
    top, inside = {}, False
    for line in lines:
        if line.startswith("## 一、顶层类"):
            inside = True
            continue
        if inside and line.startswith("## 二、"):
            break
        if not inside or re.match(r"^\|\s*-+", line):
            continue
        m = re.match(
            r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*`([^`]+)`\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$",
            line)
        if m:
            cn, en, uid, desc, src, status = (x.strip() for x in m.groups())
            top[uid] = {"cn": cn, "en": en, "desc": desc, "source": src, "status": status}
    if len(top) != 16:
        die(f"类与层级.md §一 解析到 {len(top)} 个顶层类，期望 16")

    # §2.9 支撑类表（对象分类父类 / 受控词表 / 规则族）
    support, inside = {}, False
    for line in lines:
        if line.startswith("### 2.9"):
            inside = True
            continue
        if inside and line.startswith("### 2.10"):
            break
        if not inside:
            continue
        m = re.match(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*`([A-Za-z][A-Za-z0-9]*)`", line)
        if m:
            cn, en, uid = (x.strip() for x in m.groups())
            support[uid] = {"cn": cn, "en": en}

    # §三 决议块中的「用地」Land
    m = re.search(r"「([^」]+)」独立成类\s*`Land`", text)
    if m:
        support["Land"] = {"cn": m.group(1), "en": "Land"}
    return top, support


def main():
    if not TTL.exists():
        die(f"找不到本体文件：{TTL}")
    g = Graph()
    g.parse(TTL, format="turtle")

    md_top, md_support = parse_md()

    # ---------- 类（ttl 声明） ----------
    classes = {}
    for c in set(g.subjects(RDF.type, OWL.Class)):
        cid = split_uri(c)
        label = g.value(c, RDFS.label)
        if label is None:
            die(f"类 {cid} 缺 rdfs:label（中文标签）")
        parent = None
        for p in g.objects(c, RDFS.subClassOf):
            if isinstance(p, URIRef) and str(p).startswith(NS):
                parent = split_uri(p)
                break
        classes[cid] = {"id": cid, "cn": str(label), "parent": parent,
                        "children": [], "declared": True}

    # ---------- ⚠ 被引用但未声明的父类 ----------
    referenced = {c["parent"] for c in classes.values() if c["parent"]}
    undeclared = sorted(referenced - set(classes))
    for uid in undeclared:
        if uid not in md_support:
            die(f"未声明的类 `{uid}` 在 类与层级.md 中找不到中文名，无法补齐")
        classes[uid] = {"id": uid, "cn": md_support[uid]["cn"], "parent": None,
                        "children": [], "declared": False}

    # ---------- 父子关系 ----------
    for cid, c in classes.items():
        if c["parent"] and c["parent"] in classes:
            classes[c["parent"]]["children"].append(cid)
    for c in classes.values():
        c["children"].sort()

    # ---------- 防漂移断言 ①：md 顶层类 ↔ ttl ----------
    for cid in md_top:
        if cid not in classes:
            die(f"类与层级.md 顶层类 `{cid}` 在 ttl 中不存在")
    # ---------- 防漂移断言 ②：六域映射覆盖 16 顶层类 ----------
    for cid in md_top:
        if cid not in DOMAIN_OF:
            die(f"顶层类 `{cid}` 未纳入六域映射（DOMAIN_OF）")

    # ---------- 角色标注 ----------
    declared_top = [cid for cid, c in classes.items() if c["declared"] and not c["parent"]]
    support_ids = sorted([cid for cid in declared_top if cid not in md_top])
    for cid, meta in md_top.items():
        classes[cid].update(en=meta["en"], desc=meta["desc"], source=meta["source"],
                            status=meta["status"], domain=DOMAIN_OF[cid],
                            role="top", top=True)
    for cid in support_ids:
        sup = md_support.get(cid, {})
        classes[cid].update(en=sup.get("en", ""), desc="", source="", status="建模稿",
                            domain=None, role="technical" if cid in TECHNICAL else "support",
                            top=False)
    for cid, c in classes.items():
        if not c.get("role"):
            c.update(en="", desc="", source="", status="建模稿",
                     domain=None, role="sub" if c["declared"] else "undeclared", top=False)

    # ---------- 属性 ----------
    props = {}
    for ptype, kind in ((OWL.ObjectProperty, "object"), (OWL.DatatypeProperty, "datatype")):
        for p in set(g.subjects(RDF.type, ptype)):
            pid = split_uri(p)
            label = g.value(p, RDFS.label)
            if label is None:
                die(f"属性 {pid} 缺 rdfs:label")
            dom = [split_uri(d) for d in g.objects(p, RDFS.domain)
                   if isinstance(d, URIRef) and str(d).startswith(NS)]
            rng = [split_uri(r) if str(r).startswith(NS) else str(r)
                   for r in g.objects(p, RDFS.range) if isinstance(r, URIRef)]
            props[pid] = {"id": pid, "cn": str(label), "type": kind,
                          "domain": sorted(set(dom)), "range": sorted(set(rng))}
    for cid, c in classes.items():
        c["props"] = sorted([pid for pid, p in props.items() if cid in p["domain"]])

    # ---------- ABox 个体 ----------
    # 动态枚举：凡“有实例声明”的本体类，其非类主体即为个体。
    # （原写死 5 个类，漏掉了 TreatmentType 2 个、PolicyDocument 1 个 —— 2026-10-11 修）
    individuals = {}
    abox_classes = []
    for c in sorted(set(g.subjects(RDF.type, OWL.Class)), key=split_uri):
        cid = split_uri(c)
        insts = [s for s in g.subjects(RDF.type, c) if split_uri(s) not in classes]
        if not insts:
            continue
        abox_classes.append(cid)
        for s in insts:
            sid = split_uri(s)
            individuals[sid] = {"id": sid, "cn": str(g.value(s, RDFS.label) or sid), "cls": cid}

    # ---------- 指标（yaml 详情 × ttl 个体） ----------
    y = yaml.safe_load(YAML.read_text(encoding="utf-8"))
    indicators = []
    for ind in y["indicators"]:
        code = str(ind["code"])
        uid = f"Indicator_{code}"
        indicators.append({
            "seq": ind["seq"], "code": code, "name": ind["name"],
            "dimension": ind["inDimension"], "category": ind.get("inCategory") or "",
            "measures": ind["measures"], "unit": ind["unit"],
            "orientation": ind["orientation"], "computedFrom": ind["computedFrom"],
            "formula": ind.get("formula", ""), "threshold": str(ind.get("threshold", "")),
            "basedOn": ind.get("basedOn", ""), "status": ind.get("status", ""),
            "uri": NS + uid, "inTtl": uid in individuals,
        })
    # ---------- 防漂移断言 ③：指标数 / 序号 ----------
    ttl_ind = [i for i in individuals.values() if i["cls"] == "Indicator"]
    if len(ttl_ind) != len(indicators):
        die(f"ttl 中 Indicator 个体 {len(ttl_ind)} 个 ≠ yaml 指标 {len(indicators)} 项")
    missing = [i["code"] for i in indicators if not i["inTtl"]]
    if missing:
        die(f"指标 {missing} 在 ttl 中无对应个体")
    if sorted(i["seq"] for i in indicators) != list(range(1, 56)):
        die("指标序号不是 1..55 的连续集合")

    dims = [{"cn": d["name"], "id": d["dimension"], "measures": d["measures"]} for d in y["dimensions"]]
    cats = [{"cn": c["name"], "dims": c["dimensions"], "seqs": c["seqs"]} for c in y["categories"]]

    counts = {
        "classesDeclared": sum(1 for c in classes.values() if c["declared"]),
        "classesUndeclaredParents": len(undeclared),
        "classesTotal": len(classes),
        "topClasses": len(md_top),
        "supportClasses": len(support_ids),
        "objectProps": sum(1 for p in props.values() if p["type"] == "object"),
        "datatypeProps": sum(1 for p in props.values() if p["type"] == "datatype"),
        "individuals": len(individuals),
        "indicators": len(indicators),
    }
    payload = {
        "meta": {
            "generated": "2026-10-11",
            "namespace": NS,
            "source": "城市体检-更新本体.ttl + 类与层级.md + 55项指标.yaml",
            "generator": "03-本体模型/_to_graph_json.py",
            "counts": counts,
            "warnings": {
                "undeclaredParents": undeclared,
                "technicalClasses": sorted(TECHNICAL),
                "note": "以下类被 rdfs:subClassOf 引用但未在 ttl 中声明为 owl:Class；"
                        "本脚本按 类与层级.md 补齐中文名，标 declared=false。根因在 _gen_ttl.py，待修订。",
            },
        },
        "domains": DOMAIN_CN,
        "domainOf": DOMAIN_OF,
        "backbone": [{"from": a, "to": b, "pred": p, "cn": cn} for a, b, p, cn in BACKBONE],
        "classes": [classes[cid] for cid in sorted(classes)],
        "properties": [props[pid] for pid in sorted(props)],
        "individuals": [individuals[i] for i in sorted(individuals)],
        "indicators": indicators,
        "dimensions": dims,
        "categories": cats,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "ontology.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    (OUT_DIR / "ontology.js").write_text(
        "window.__ONTOLOGY__=" + json.dumps(payload, ensure_ascii=False) + ";\n",
        encoding="utf-8", newline="\n")

    print(f"[OK] 声明类 {counts['classesDeclared']} + 未声明父类 {counts['classesUndeclaredParents']} "
          f"= 节点类 {counts['classesTotal']}（其中顶层 {counts['topClasses']} / 支撑 {counts['supportClasses']}）")
    print(f"[OK] 对象属性 {counts['objectProps']} | 数据属性 {counts['datatypeProps']} "
          f"| 个体 {counts['individuals']} | 指标 {counts['indicators']}")
    print(f"[WARN] ttl 未声明的父类：{', '.join(undeclared)}" if undeclared else "[OK] 未声明父类：无 ✓")
    print("[OK] ABox 个体明细：" + " | ".join(
        f"{c} {sum(1 for i in individuals.values() if i['cls'] == c)}" for c in abox_classes))
    print(f"[OK] 输出 → {OUT_DIR}")
    for cid in sorted(md_top, key=lambda k: (DOMAIN_OF[k], k)):
        c = classes[cid]
        print(f"     {DOMAIN_OF[cid]:8s} {c['cn']:9s} {cid:22s} 子类{len(c['children']):3d} 属性{len(c['props']):3d}")


if __name__ == "__main__":
    main()
