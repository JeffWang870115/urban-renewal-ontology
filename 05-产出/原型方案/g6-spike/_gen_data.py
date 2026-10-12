# -*- coding: utf-8 -*-
"""
g6-spike 数据导出器

读 `../原型/data/ontology.json`（由 03-本体模型/_to_graph_json.py 产出）
→ 生成 `data.js`（G6 可直接消费的 107 类 + 83 条 subClassOf + 7 个语义域）。

用法（项目根目录下）：
    python 05-产出/原型方案/g6-spike/_gen_data.py

改完本体后重跑链：_gen_ttl.py → _to_graph_json.py → 本脚本
"""
import collections
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE.parent / "原型" / "data" / "ontology.json"
OUT = HERE / "data.js"


def top_of(cid, CL):
    """回溯到顶层类（域归属以顶层类为准）"""
    seen = set()
    while cid in CL and CL[cid]["parent"] and CL[cid]["parent"] in CL and cid not in seen:
        seen.add(cid)
        cid = CL[cid]["parent"]
    return cid


def main():
    d = json.loads(SRC.read_text(encoding="utf-8"))
    CL = {c["id"]: c for c in d["classes"]}
    DOM = d["domains"]
    DOF = d["domainOf"]

    nodes, edges, dom = [], [], collections.Counter()
    for c in d["classes"]:
        t = top_of(c["id"], CL)
        dd = DOF.get(t) or "neutral"
        if dd not in DOM:
            dd = "neutral"
        dom[dd] += 1
        nodes.append({
            "id": c["id"],
            "combo": dd,
            "data": {
                "cn": c["cn"],
                "en": c.get("en") or c["id"],
                "dom": dd,
                "nc": len(c.get("children") or []),   # 子类数（用于节点大小/标签分级）
                "top": 1 if c.get("top") else 0,
                "st": c.get("status") or "",
            },
        })
        if c["parent"] and c["parent"] in CL:
            edges.append({"source": c["parent"], "target": c["id"]})

    combos = [{"id": k, "data": {"cn": v}} for k, v in DOM.items()]

    # ---- 断言：与本体口径对齐，防漂移 ----
    total = len(d["classes"])
    assert len(nodes) == total, (len(nodes), total)
    assert len(edges) == len([c for c in d["classes"] if c["parent"] and c["parent"] in CL])
    assert sum(dom.values()) == total, dict(dom)
    assert sum(n["data"]["top"] for n in nodes) == 16, "顶层类应为 16"
    assert set(dom) <= set(DOM), set(dom) - set(DOM)
    named = [n for n in nodes if n["data"]["nc"] >= 1]
    print("防漂移断言通过：节点 %d | 边 %d | 域 %s" % (len(nodes), len(edges), dict(dom)))
    print("标签分级候选（总览）：顶层 16 + 有子类 %d，去重后 %d"
          % (len(named), len({n["id"] for n in nodes if n["data"]["top"] or n["data"]["nc"] >= 1})))

    payload = {"nodes": nodes, "edges": edges, "combos": combos, "domNames": DOM}
    OUT.write_text("window.G6DATA=" + json.dumps(payload, ensure_ascii=False) + ";",
                   encoding="utf-8", newline="\n")
    print("已写出 %s（%d bytes）" % (OUT.name, len(OUT.read_bytes())))


if __name__ == "__main__":
    main()
