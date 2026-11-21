# -*- coding: utf-8 -*-
"""属性与关系.md：补 CheckItem 相关属性（2026-11-08）"""
from pathlib import Path
import unicodedata

P = str(Path(__file__).resolve().parent / "属性与关系.md")


def w(s):
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)


def pad(s, n):
    return s + " " * max(0, n - w(s))


def is_sep(r):
    return all(set(c) <= set("-: ") for c in r)


def render(rows):
    ncol = max(len(r) for r in rows)
    widths = [0] * ncol
    for r in rows:
        if is_sep(r):
            continue
        for j, c in enumerate(r):
            widths[j] = max(widths[j], w(c))
    out = []
    for r in rows:
        if is_sep(r):
            out.append("|" + "|".join("-" * (widths[j] + 2) for j in range(len(r))) + "|")
        else:
            out.append("|" + "|".join(" " + pad(c, widths[j]) + " " for j, c in enumerate(r)) + "|")
    return out


lines = open(P, encoding="utf-8", newline="").read().replace("\r\n", "\n").split("\n")

# ---- 1) 对象属性表 ----
start = next(k for k, l in enumerate(lines) if l.startswith("| 关系"))
end = start
while end < len(lines) and lines[end].startswith("|"):
    end += 1
rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in lines[start:end]]
assert not any(len(r) > 2 and r[2] == "`failsCheckItem`" for r in rows), "已存在"

NEW = [
    ["核查项未通过", "fails check item", "`failsCheckItem`", "Building / RenewalObject → CheckItem",
     "**2026-11-08 新增**：实体**命中的核查项**——**只记未通过、不记通过**（避免 3597×57 的噪声）。指标值 = 命中该指标核查项的实体去重计数；旗标不另存",
     "建模稿（本轮新增）"],
    ["核查项适用指标", "check item for", "`checkItemFor`", "CheckItem → Indicator",
     "**2026-11-08 新增**：该核查项服务于哪个指标（住房 32 项归属指标 1–8；街区 25 项归属 24/25/26），用于把命中数还原成指标值",
     "建模稿（本轮新增）"],
]
k = next(a for a, r in enumerate(rows) if len(r) > 2 and r[2] == "`basedOn`")
rows[k:k] = NEW
for r in rows:
    if len(r) > 3 and r[2] == "`basedOn`":
        r[3] = "Indicator / RenewalProject / **CheckItem** → PolicyStandard"
        r[4] = r[4] + "；**2026-11-08 定义域扩至 `CheckItem`**（核查项须标依据表号）"
lines[start:end] = render(rows)

txt = "\n".join(lines)

# ---- 2) 新增 §2.4 ----
SEC = [
    "",
    "### 2.4 核查项属性（2026-11-08 新增，A2 检查项计数驱动）",
    "",
    "> **为什么单列**：A2 类指标（住房 1–8、街区 24/25/26）的判定来自一组**核查项**，任一未通过即计数。核查项不是布尔，含阈值与单位，故须自带走三要素。",
    "> **个体清单**：见 `类与层级.md` §2.11（`CI_H*` 32 个 / `CI_C1–C6` / `CI_F1–F10` / `CI_L1–L9`）。",
    "",
    "| 属性 | URI 名 | 适用类 | 值域 | 说明 |",
    "| --- | --- | --- | --- | --- |",
    "| 核查项判定类型 | `checkItemType` | `CheckItem` | 枚举：**是否型 / 阈值型 / 比率型** | 决定怎么判：是否型看有/无；阈值型与数值比；比率型算比值 |",
    "| 核查项阈值 | `checkItemThreshold` | `CheckItem` | 字符串（**保留原表述**） | 如 `≥60%`、`≥1.5 m`、`1250–2360 ㎡/千人`。⚠️ 不得自行归一化或换算，原文怎么写就怎么存 |",
    "| 核查项单位 | `checkItemUnit` | `CheckItem` | 字符串 | `%`、`m`、`㎡/千人`、`㎡/人` |",
    "",
]
anchor = "## 三、借鉴同事成果新增的属性与约束"
assert anchor in txt
txt = txt.replace(anchor, "\n".join(SEC) + anchor, 1)

# ---- 3) §四 约束 ----
CONS = [
    "- [x] **`CheckItem` 必备三要素（2026-11-08 新增）**：每个 `CheckItem` 须有 `checkItemType`、`checkItemFor`（`sh:minCount 1`）；阈值型/比率型另须 `checkItemThreshold`。",
    "- [x] **`failsCheckItem` 只记未通过（2026-11-08 新增）**：不记录“通过”的核查项；因此**无法从本体反推“通过项清单”**，如需完整核查底稿，须另存原件（源表/报告）。",
    "- [ ] **`failsCheckItem` 适用范围校验（待实现）**：实体命中的核查项，其 `checkItemFor` 所指指标的 `measures` 须与该实体类型匹配（如楼栋只能命中住房核查项）——`sh:sparql`，本轮只登记。",
    "",
]
anchor2 = "## 五、已知风险"
assert anchor2 in txt
txt = txt.replace(anchor2, "\n".join(CONS) + anchor2, 1)

# ---- 4) §五 风险 ----
RISK = [
    "- **核查项只记命中、不记通过（2026-11-08）**：这样可以避免 3597 栋 × 57 项 ≈ 20 万条的噪声，但代价是**丢失“通过项”的底稿**。若后续要做“整改前后对比”或“逐项复核”，必须回到源表/原始报告，本体不承担该职责。",
    "- **24/25/26 不并入 `FacilityObject`（2026-11-08 讨论结论）**：老旧商业街区 / 老旧厂区 / 老旧生活街区是**片区型调查对象**，不是点状服务设施。它们保持为 `RenewalObject` 子类，经 `DataObject` 角色被指标引用、经 `belongsTo` 挂所属街区——**不动类结构**。",
]
txt = txt.rstrip("\n") + "\n" + "\n".join(RISK) + "\n"

open(P, "w", encoding="utf-8", newline="\n").write(txt)
print("OK", len(txt.encode("utf-8")))
