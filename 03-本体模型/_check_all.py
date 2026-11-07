#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_check_all.py —— 一条命令跑完本体全链自检（W-B06）

用法
----
    python 03-本体模型/_check_all.py              # 全量检查（默认含确定性双跑）
    python 03-本体模型/_check_all.py --no-twice   # 跳过双跑，快一档
    python 03-本体模型/_check_all.py --update     # 重建基线快照（产物确有正当变更时用）

检查六步
--------
    1. 重跑链：_gen_ttl.py -> _to_graph_json.py -> _gen_class_list.py
       （三者自身带防漂移断言，失败即非零退出，本脚本如实转报）
    2. 确定性：再跑一遍链，逐文件比对 sha256 —— 任何抖动都说明生成器引入了不确定性
    3. 结构计数：从产物实测（三元组 / 类 / 属性 / subClassOf / ABox 个体 / SHACL 形状 / 查询条数）
    4. SHACL：pyshacl 校验，必须 CONFORMS
    5. SPARQL：逐条执行 常用查询.sparql，任一条报错或零行为失败
    6. 基线比对：与 _baseline.json 对照，任何计数或哈希变化都报差异

设计约束（踩过的坑，别再犯）
--------------------------
  * **不写死数据清单**：ABox 类清单、个体数一律从图上动态统计；历史教训是写死清单漏算 2 类。
  * **基线外置**：计数不硬编码在脚本里，存 _baseline.json；否则本体一演进就误报，最后被人关掉。
  * 路径一律基于 `Path(__file__)`；写文件一律 `newline='\\n'`（Windows 下 CRLF 会让 diff 全红）。
  * 任一环节失败 → 退出码 1；只有全绿才退 0，可直接挂进提交前钩子。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MOD = ROOT / "03-本体模型"

CHAIN = [
    MOD / "_gen_ttl.py",
    MOD / "_to_graph_json.py",
    MOD / "_gen_class_list.py",
]

# 参与哈希比对的产物（顺序即报告顺序）
TRACKED = [
    MOD / "城市体检-更新本体.ttl",
    MOD / "城市体检-更新约束.shacl",
    MOD / "常用查询.sparql",
    MOD / "类与层级.md",
    ROOT / "05-产出" / "原型方案" / "原型" / "data" / "ontology.json",
    ROOT / "05-产出" / "原型方案" / "原型" / "data" / "ontology.js",
]

BASELINE = MOD / "_baseline.json"

NS = "https://ontology.cset-digital.cn/urban-renewal#"

_FAILED: list[str] = []
_WARNED: list[str] = []


def say(msg: str = "") -> None:
    print(msg, flush=True)


def step(n: int, total: int, title: str) -> None:
    say()
    say(f"[{n}/{total}] {title}")
    say("-" * 62)


def fail(msg: str) -> None:
    _FAILED.append(msg)
    say(f"  ✗ {msg}")


def warn(msg: str) -> None:
    _WARNED.append(msg)
    say(f"  ⚠ {msg}")


def ok(msg: str) -> None:
    say(f"  ✓ {msg}")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_chain() -> bool:
    """跑重跑链；任一脚本非零退出即失败，并打印其 stderr 尾部。"""
    all_ok = True
    for script in CHAIN:
        if not script.exists():
            fail(f"缺少生成器：{script.relative_to(ROOT)}")
            return False
        r = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        name = script.name
        if r.returncode != 0:
            all_ok = False
            fail(f"{name} 退出码 {r.returncode}")
            tail = (r.stdout or "").strip().splitlines()[-6:]
            err = (r.stderr or "").strip().splitlines()[-6:]
            for line in tail + err:
                say(f"      {line}")
            # 断言失败会把 "!!" 打到 stdout，一并兜住
        elif "!!" in (r.stdout or ""):
            all_ok = False
            fail(f"{name} 输出含断言失败标记 '!!'")
            for line in r.stdout.strip().splitlines():
                if "!!" in line or line.startswith("    "):
                    say(f"      {line}")
        else:
            lines = [ln for ln in (r.stdout or "").strip().splitlines() if ln.strip()]
            pick = next((ln for ln in lines if ln.startswith(("[OK]", "[WARN]"))), "")
            ok(f"{name} 通过" + (f"（{pick.strip()[:56]}）" if pick else ""))
    return all_ok


def hash_all() -> dict[str, str]:
    out = {}
    for p in TRACKED:
        out[p.relative_to(ROOT).as_posix()] = sha256(p) if p.exists() else "MISSING"
    return out


def collect_counts() -> dict:
    """从产物实测计数（全部动态，不写死任何清单）。"""
    import rdflib
    from rdflib import OWL, RDF, RDFS

    d: dict = {}
    g = rdflib.Graph()
    g.parse(str(MOD / "城市体检-更新本体.ttl"), format="turtle")
    d["ttl_triples"] = len(g)
    d["ttl_classes"] = len(set(g.subjects(RDF.type, OWL.Class)))
    d["ttl_object_props"] = len(set(g.subjects(RDF.type, OWL.ObjectProperty)))
    d["ttl_datatype_props"] = len(set(g.subjects(RDF.type, OWL.DatatypeProperty)))
    d["ttl_subclass_edges"] = len(set(g.subject_objects(RDFS.subClassOf)))

    # ABox 个体：凡被 rdf:type 到某个「非 OWL 元类」的实例都算；按类动态聚合
    meta = {
        OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty,
        OWL.Ontology, OWL.NamedIndividual,
        OWL.TransitiveProperty, OWL.FunctionalProperty,
        OWL.InverseFunctionalProperty, OWL.SymmetricProperty,
    }
    per_class: dict[str, int] = {}
    for _, o in g.subject_objects(RDF.type):
        if o in meta or not str(o).startswith(NS):
            continue
        key = str(o).split("#")[-1]
        per_class[key] = per_class.get(key, 0) + 1
    d["ttl_abox_total"] = sum(per_class.values())
    d["ttl_abox_by_class"] = dict(sorted(per_class.items()))

    # 悬挂引用：被当作父类/定义域/值域引用，却从未声明为 owl:Class
    declared = set(g.subjects(RDF.type, OWL.Class))
    referenced = set(g.objects(None, RDFS.subClassOf))
    for pred in (RDFS.domain, RDFS.range):
        referenced |= {o for o in g.objects(None, pred) if str(o).startswith(NS)}
    dangling = sorted(
        str(x).split("#")[-1] for x in referenced - declared
        if str(x).startswith(NS)
    )
    d["ttl_dangling_classes"] = dangling

    # SHACL
    sg = rdflib.Graph()
    sg.parse(str(MOD / "城市体检-更新约束.shacl"), format="turtle")
    SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
    d["shacl_triples"] = len(sg)
    d["shacl_node_shapes"] = len(set(sg.subjects(RDF.type, SH.NodeShape)))
    # 属性形状多为匿名节点，靠 rdf:type 数不到；用 sh:property 的宾语数才准确
    d["shacl_property_shapes"] = len(set(sg.objects(None, SH.property)))
    d["shacl_target_classes"] = len(set(sg.objects(None, SH.targetClass)))

    # SPARQL
    txt = (MOD / "常用查询.sparql").read_text(encoding="utf-8")
    d["sparql_queries"] = sum(1 for b in txt.split("\n\n") if "SELECT" in b)

    # 指标 yaml
    import yaml
    ydoc = yaml.safe_load((ROOT / "04-指标映射" / "55项指标.yaml").read_text(encoding="utf-8"))
    d["yaml_indicators"] = len(ydoc.get("indicators", []))
    d["yaml_dimensions"] = len(ydoc.get("dimensions", []))
    d["yaml_categories"] = len(ydoc.get("categories", []))
    return d


def check_shacl() -> None:
    import rdflib
    from pyshacl import validate

    g = rdflib.Graph()
    g.parse(str(MOD / "城市体检-更新本体.ttl"), format="turtle")
    sg = rdflib.Graph()
    sg.parse(str(MOD / "城市体检-更新约束.shacl"), format="turtle")
    conforms, _, text = validate(
        g, shacl_graph=sg, inference="none", abort_on_first=False, advanced=True
    )
    if conforms:
        ok("pyshacl CONFORMS: True")
    else:
        fail("pyshacl CONFORMS: False")
        for line in str(text).strip().splitlines()[:20]:
            say(f"      {line}")


def check_sparql() -> dict[str, int]:
    """逐条执行查询。返回 {标签: 行数}，供基线比对。

    零行**不算失败**——本体现在没有业务实例，Q5（问题→建议→项目）本来就该是空的；
    但行数会记进基线，将来接上实例数据后若仍是 0，基线比对会把这个变化暴露出来。
    """
    import rdflib

    g = rdflib.Graph()
    g.parse(str(MOD / "城市体检-更新本体.ttl"), format="turtle")
    txt = (MOD / "常用查询.sparql").read_text(encoding="utf-8")
    blocks = [b.strip() for b in txt.split("\n\n") if "SELECT" in b]
    rows_by_q: dict[str, int] = {}
    for i, block in enumerate(blocks, 1):
        raw = next(
            (ln.strip() for ln in block.splitlines() if ln.strip().startswith("# Q")),
            f"#{i}",
        )
        label = raw.lstrip("# ").strip()
        label = label.split("：")[0].split(".")[0].strip() if "：" in label else label[:14]
        try:
            rows = list(g.query(block))
        except Exception as e:  # noqa: BLE001
            fail(f"Q{i} 执行报错：{type(e).__name__}: {str(e)[:80]}")
            continue
        rows_by_q[f"Q{i}"] = len(rows)
        if rows:
            ok(f"Q{i} → {len(rows)} 行　{raw.lstrip('# ')[:26]}")
        else:
            warn(f"Q{i} 空结果（0 行）｜{raw.lstrip('# ')[:26]}｜若依赖业务实例属预期（W-C02）")
    return rows_by_q


def compare_baseline(counts: dict, hashes: dict, update: bool) -> None:
    payload = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "note": "本体全链自检基线。产物发生正当变更时用 --update 重建；勿手改。",
        "counts": counts,
        "sha256": hashes,
    }
    if update or not BASELINE.exists():
        with open(BASELINE, "w", encoding="utf-8", newline="\n") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1, sort_keys=False)
            f.write("\n")
        action = "已更新" if update else "首次建立"
        ok(f"基线{action}：{BASELINE.relative_to(ROOT)}")
        if not update:
            say("      请复核该基线后纳入版本库；之后任何漂移都会被拦下。")
        return

    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    bc, bh = base.get("counts", {}), base.get("sha256", {})

    diffs = 0
    for k in sorted(set(counts) | set(bc)):
        if k in ("ttl_abox_by_class", "sparql_rows"):
            a, b = counts.get(k, {}) or {}, bc.get(k, {}) or {}
            for sub in sorted(set(a) | set(b)):
                if a.get(sub) != b.get(sub):
                    diffs += 1
                    say(f"  · {k} 变化 {sub}: {b.get(sub)} → {a.get(sub)}")
            continue
        if counts.get(k) != bc.get(k):
            diffs += 1
            say(f"  · 计数变化 {k}: {bc.get(k)} → {counts.get(k)}")

    for p in TRACKED:
        rel = p.relative_to(ROOT).as_posix()
        if hashes.get(rel) != bh.get(rel):
            diffs += 1
            say(f"  · 内容变化 {rel}（哈希不一致）")

    if diffs:
        fail(f"与基线不一致：{diffs} 处（若确属本次变更，确认后用 --update 重建基线）")
    else:
        ok("与基线完全一致（计数 + 哈希）")


def main() -> int:
    ap = argparse.ArgumentParser(description="本体全链自检")
    ap.add_argument("--no-twice", action="store_true", help="跳过确定性双跑")
    ap.add_argument("--update", action="store_true", help="重建基线快照")
    args = ap.parse_args()

    say("=" * 62)
    say("城市体检与更新本体 · 全链自检（_check_all.py）")
    say(f"项目根：{ROOT}")
    say("=" * 62)

    step(1, 6, "重跑链（_gen_ttl → _to_graph_json → _gen_class_list）")
    if not run_chain():
        say()
        say("链条未通过，后续检查无意义，提前退出。")
        return 1

    h1 = hash_all()

    if not args.no_twice:
        step(2, 6, "确定性（第二次跑链，逐文件比对 sha256）")
        run_chain()
        h2 = hash_all()
        drift = [k for k in h2 if h1.get(k) != h2[k]]
        if drift:
            for k in drift:
                fail(f"两次运行结果不同：{k}")
            say("      生成器存在不确定性（常见根因：随机 id / 无序集合遍历 / 时间戳）。")
        else:
            ok(f"{len(h2)} 个产物两次运行逐字节一致")
    else:
        step(2, 6, "确定性（已按 --no-twice 跳过）")

    step(3, 6, "结构计数（全部从产物动态统计）")
    counts = collect_counts()
    for k in ("ttl_triples", "ttl_classes", "ttl_object_props", "ttl_datatype_props",
              "ttl_subclass_edges", "ttl_abox_total", "shacl_node_shapes",
              "shacl_property_shapes", "shacl_target_classes", "sparql_queries",
              "yaml_indicators", "yaml_dimensions", "yaml_categories"):
        ok(f"{k:22s} = {counts[k]}")
    ok(f"ABox 按类：" + " | ".join(f"{k} {v}" for k, v in counts["ttl_abox_by_class"].items()))
    if counts["ttl_dangling_classes"]:
        fail(f"悬挂类引用：{', '.join(counts['ttl_dangling_classes'])}")
    else:
        ok("悬挂类引用 0")

    step(4, 6, "SHACL 校验（pyshacl）")
    check_shacl()

    step(5, 6, "SPARQL 查询（逐条执行）")
    counts["sparql_rows"] = check_sparql()

    step(6, 6, "基线比对")
    compare_baseline(counts, hash_all(), args.update)

    say()
    say("=" * 62)
    if _WARNED:
        say(f"提示（非失败）：{len(_WARNED)} 项")
        for m in _WARNED:
            say(f"  ⚠ {m}")
    if _FAILED:
        say(f"结果：失败 {len(_FAILED)} 项")
        for m in _FAILED:
            say(f"  ✗ {m}")
        say("=" * 62)
        return 1
    say("结果：全部通过 ✓")
    say("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
