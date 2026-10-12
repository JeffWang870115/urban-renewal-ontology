# -*- coding: utf-8 -*-
"""「全量类清单」附录生成器 —— 写进 `类与层级.md` 的**受控区块**

背景：`类与层级.md` 是**分层叙述**（§一只列 16 个顶层类，其余类分散在 §2.1–§2.10），
      单看该文档不易拼出全貌。本脚本把 107 个类一次列全，作为**附录 A** 并入该文档。

⚠ 重要设计：**只维护受控区块，绝不重写人工正文**。
   区块以 HTML 注释为界：
     <!-- AUTO-GEN:BEGIN 附录A 全量类清单 ... -->
     ...（本脚本全权负责这段）...
     <!-- AUTO-GEN:END 附录A 全量类清单 -->
   - 首次运行 → 在文档末尾追加标记块；
   - 之后运行 → 只替换块内内容，块外（§〇–§四 人工正文）逐字节不动。

数据来源：`05-产出/原型方案/原型/data/ontology.json`（由 03-本体模型/_to_graph_json.py 从 ttl 生成）
          + `类与层级.md` 正文（用于对账「哪些类在正文里被点名」）

用法：python 03-本体模型/_gen_class_list.py
       （前置：先跑 _gen_ttl.py 与 _to_graph_json.py）
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "05-产出" / "原型方案" / "原型" / "data" / "ontology.json"
MD = ROOT / "03-本体模型" / "类与层级.md"

BEGIN = "<!-- AUTO-GEN:BEGIN 附录A 全量类清单"
END = "<!-- AUTO-GEN:END 附录A 全量类清单 -->"

DOM_ORDER = ["core", "metric", "axis", "space", "renew", "policy", "neutral"]


def main():
    if not DATA.exists():
        print(f"[FAIL] 缺少 {DATA}，请先运行 _to_graph_json.py", file=sys.stderr)
        sys.exit(1)

    d = json.loads(DATA.read_text(encoding="utf-8"))
    raw = MD.read_text(encoding="utf-8")

    # ---- 对账基准：只取「受控区块之前」的人工正文 ----
    main_text = raw[:raw.index(BEGIN)] if BEGIN in raw else raw

    CL = {c["id"]: c for c in d["classes"]}
    DCN = d["domains"]
    DOM_OF = d["domainOf"]

    IND_BY_CLASS = {}
    for i in d["indicators"]:
        ks = set()
        if i["measures"]:
            ks.add(i["measures"])
        ks |= set(i["computedFrom"] or [])
        for k in ks:
            IND_BY_CLASS.setdefault(k, []).append(i["seq"])

    INST = {}
    for x in d["individuals"]:
        INST[x["cls"]] = INST.get(x["cls"], 0) + 1

    tops = [c["id"] for c in d["classes"] if c["role"] == "top"]
    tops.sort(key=lambda x: (DOM_ORDER.index(CL[x].get("domain") or "neutral"), x))

    def subtree(cid):
        out, stack = [], [(cid, 0)]
        while stack:
            cur, depth = stack.pop()
            out.append((cur, depth))
            for k in reversed(sorted(CL[cur]["children"])):
                stack.append((k, depth + 1))
        return out

    def marks(cid):
        m = []
        if INST.get(cid):
            m.append(f"实例×{INST[cid]}")
        if IND_BY_CLASS.get(cid):
            m.append(f"指标×{len(IND_BY_CLASS[cid])}")
        if CL[cid].get("declared") is False:
            m.append("⚠未声明")
        return ("   [" + " · ".join(m) + "]") if m else ""

    counts = d["meta"]["counts"]
    total = len(CL)

    L = [
        BEGIN + " — 由 03-本体模型/_gen_class_list.py 生成，请勿手工编辑 -->",
        "",
        "## 附录 A、全量类清单（107 个 `owl:Class`）",
        "",
        "> 本附录由机读产物（`城市体检-更新本体.ttl`）反向生成，与正文（§〇–§四）互为补充：",
        "> **正文**负责分层叙述与来源说明，**本附录**负责「一次列全、可核对」。重跑命令：",
        "> `python 03-本体模型/_gen_class_list.py`（前置 `_gen_ttl.py` → `_to_graph_json.py`）。",
        "",
        "### A.1 口径",
        "",
        f"- **类（`owl:Class` 声明）共 {total} 个** = **{total - 1} 个概念类** + **1 个技术构件**"
        "（`DataObjectRoleUnion`，`computedFrom` 值域的 `owl:unionOf` 包装类，非概念）。",
        f"- **类 ≠ 实例**：ABox 个体另计 **{counts['individuals']} 个**，与类集合**无交集**（无 punning）。",
        "- **业务实体当前为 0**：空间单元 / 建筑 / 问题短板 / 更新项目等均无实例，待「样本市样例数据」接入。",
        f"- 结构：顶层类 **{counts['topClasses']}** ｜ 支撑类 **{counts['supportClasses']}** ｜ 子类 "
        f"**{total - counts['topClasses'] - counts['supportClasses']}**。",
        "",
        "| 语义域 | 类数（含子树） |",
        "|---|---|",
    ]
    def subtree_size(cid):
        n, stack = 1, [cid]
        while stack:
            cur = stack.pop()
            for k in CL[cur]["children"]:
                n += 1
                stack.append(k)
        return n

    bydom = {k: 0 for k in DOM_ORDER}
    for c in d["classes"]:
        if c["role"] == "top":
            bydom[DOM_OF[c["id"]]] += subtree_size(c["id"])
    aux_n = sum(subtree_size(c["id"]) for c in d["classes"]
                if c["role"] in ("support", "technical"))
    for k in DOM_ORDER:
        if bydom[k]:
            L.append(f"| {DCN[k]} | {bydom[k]} |")
    L.append(f"| 支撑类 / 技术构件 | {aux_n} |")
    L.append(f"| **合计** | **{sum(bydom.values()) + aux_n}** |")

    L += ["", "### A.2 统计（按顶层类）", "",
          "| 顶层类 | 域 | 子树规模（含自身） | 直接子类 | 实例 |", "|---|---|---|---|---|"]
    for cid in tops:
        rows = subtree(cid)
        n_inst = sum(INST.get(r[0], 0) for r in rows)
        L.append(f"| **{CL[cid]['cn']}** `{cid}` | {DCN[DOM_OF[cid]]} | {len(rows)} | "
                 f"{len(CL[cid]['children'])} | {n_inst if n_inst else '—'} |")
    L.append(f"| **合计** | — | **{total}** | — | **{counts['individuals']}** |")

    L += ["", "### A.3 全量清单（按语义域 / 顶层类分组）", "",
          "> 每个类后 `[实例×n]` = 该类 ABox 个体数；`[指标×n]` = 直接引用该类的体检指标数"
          "（含 `measures` 层级与 `computedFrom` 数据对象两路）。", ""]

    sec = 0
    for cid in tops:
        sec += 1
        rows = subtree(cid)
        n_inst = sum(INST.get(r[0], 0) for r in rows)
        L.append(f"#### A.3.{sec} {CL[cid]['cn']} `{cid}` — {DCN[DOM_OF[cid]]}"
                 f"｜子类 {len(rows) - 1}｜实例 {n_inst}")
        if CL[cid].get("desc"):
            src = (CL[cid].get("source") or "—").strip()
            if src.startswith("（") and src.endswith("）"):
                src = src[1:-1]
            L.append(f"> {CL[cid]['desc']}　｜ 来源：{src}")
        L.append("")
        L.append("```")
        for cur, depth in rows:
            if depth == 0:
                head = f"{CL[cur]['cn']}  {cur}"
            else:
                head = ("│  " * (depth - 1)) + "├─ " + f"{CL[cur]['cn']}  {cur}"
            L.append(head + marks(cur))
        L.append("```")
        L.append("")

    sup = [c["id"] for c in d["classes"] if c["role"] == "support"]
    tec = [c["id"] for c in d["classes"] if c["role"] == "technical"]
    if sup:
        sec += 1
        L += [f"#### A.3.{sec} 支撑类（无上位、非顶层） — {len(sup)} 个根 + 其子类", "", "```"]
        for cur in sorted(sup):
            L.append(f"{CL[cur]['cn']}  {cur}" + marks(cur))
            for k in sorted(CL[cur]["children"]):
                L.append(f"├─ {CL[k]['cn']}  {k}" + marks(k))
        L += ["```", ""]
    if tec:
        sec += 1
        L += [f"#### A.3.{sec} 技术构件（非概念类） — {len(tec)} 个", "", "```"]
        for cur in sorted(tec):
            L.append(f"{CL[cur]['cn']}  {cur}")
        L += ["```", ""]

    # ---- 对账（只比对人工正文） ----
    named = [cid for cid in CL if cid in main_text]
    unnamed = sorted(set(CL) - set(named))
    L += ["### A.4 对账：正文（§〇–§四）覆盖情况", "",
          f"- 正文中被点名的类：**{len(named)} / {total}**（{len(named) * 100 // total}%）。"]
    if unnamed:
        L.append(f"- 正文未点名 **{len(unnamed)}** 个："
                 + "、".join(f"`{u}`" for u in unnamed) + "。")
    else:
        L.append("- 全部类均在正文中被点名。")
    L += ["",
          "> **「未点名」不等于「缺定义」**：正文多数以「一批子类」的方式列举，未逐个回写 URI 名。",
          "> 逐类的定义与来源仍以正文为准；本附录只负责**不遗漏、可核对**。",
          "",
          END]

    body = "\n".join(L) + "\n"

    # ---- 组装：只替换受控区块，块外逐字节不动 ----
    if BEGIN in raw:
        pre = raw[:raw.index(BEGIN)]
        after = raw[raw.index(END) + len(END):] if END in raw else ""
        new = pre + body + after.lstrip("\n")
        action = "替换受控区块"
    else:
        new = raw.rstrip("\n") + "\n\n---\n\n" + body
        action = "追加受控区块"

    MD.write_text(new, encoding="utf-8", newline="\n")

    print(f"[OK] {action} → {MD.name}")
    print(f"[OK] 类 {total} ｜ 顶层 {counts['topClasses']} ｜ 支撑 {counts['supportClasses']} "
          f"｜ 子类 {total - counts['topClasses'] - counts['supportClasses']} ｜ 个体 {counts['individuals']}")
    print(f"[OK] 正文点名覆盖：{len(named)}/{total}；未点名 {len(unnamed)} 个")


if __name__ == "__main__":
    main()
