# -*- coding: utf-8 -*-
"""指标 14 两级判定落地：类与层级.md + 属性与关系.md"""
from pathlib import Path
import unicodedata

D = Path(__file__).resolve().parent


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


# ==================== 1) 类与层级.md ====================
P1 = str(D / "类与层级.md")
t = open(P1, encoding="utf-8", newline="").read().replace("\r\n", "\n")

START = "**判定范式：以「未达标配建的公共活动场地的社区数量」（指标 14）为例（2026-11-08）**"
END = "- **与实例数据的落差**"
i = t.find(START)
assert i >= 0, "未找到判定范式块起点"
j = t.find("\n\n", t.find(END))
j = t.find("\n", t.find(END)) if j < 0 else j
assert j > i, "未找到判定范式块终点"

NEW = """**判定范式：以指标 14「未达标配建的公共活动场地的社区数量」为例（2026-11-08 定稿）**

**两级结构（本范式的核心）**

| 层 | 类 | 粒度 | 取值 | 指标 14 实例 |
| --- | --- | --- | --- | --- |
| **判断** | `IndicatorJudgement` | 每个**社区** 1 条 | 未配建 / 配建不达标 / 达标（三值） | S01=未配建、S02=配建不达标、S03=达标 |
| **结果** | `AssessmentResult` | 每个**汇总单元** 1 条 | 数值 + 达标/未达标 | 城区 = **5**（5 个社区未达标），grade = 未达标 |

- 聚合式：`AR.indicatorValue = count(IJ where judgementValue ≠ 达标)`。
- **判定是分类，结果才是计数**——二者粒度不同（社区 vs 城区），不得挤在同一个对象上。

**判定规则（2×2 阈值矩阵）**

判据 = 「该社区实例下**是否存在**一片满足面积要求的 `PublicActivityVenue`」；新建 / 既有按**场地本身的建设年代**判定。

| 社区人口 | 既有社区 | 新建社区 |
| --- | --- | --- |
| **≤ 5000** | ≥ 100 ㎡ | ≥ 600 ㎡ |
| **> 5000** | ≥ 150 ㎡ | ≥ 800 ㎡ |

- >5000 的 150 / 800 ㎡ 来自《完整居住社区建设标准（试行）》（建科规〔2020〕7号）【条款号待核】。
- **≤5000 的 100 / 600 ㎡ 为大王 2026-11-08 补充口径**，**非标准原文**，使用时须标【口径补充】。

**三情形**

- **未配建** ← 社区下无任何场地实例（规则用 `NOT EXISTS` 判空；OWL 开放世界推不出）
- **配建不达标** ← 有实例，但全部 < 阈值
- **达标** ← 存在一片 ≥ 阈值

**聚合口径**：社区内取**最大**（`∃v.area ≥ T`），**不是求和**——求和会把多个小场地误算成一片大场地。

**两处按大王口径的简化**：① 「场地与绿地统筹衡量」**不做面积合并**，仅作背景说明（标准只给 10–15% 指引，本身灵活）；② 配套设施配置、应急避难转换能力**本期不判**——规则不要求，故不建模。

**仍待核 / 已知落差**：① 「场地建设年代 → 新建 / 既有」的**分界年**【待核】；② 源数据只有**小区级**布尔＋面积（`publicVenueBuilt` / `publicVenueArea`），**无逐场地台账**，本期只能由小区级近似，做不到逐场地面积核验（见 `数据契约-v1.md` §八）。"""

t = t[:i] + NEW + t[j:]

# §四 待决：替换此前三条
OLD_Q = """- [ ] 设施类「面积」属性未形式化（`PublicActivityVenue` / `ParkGreenSpace` 等）——判「面积是否达标」时无属性可用【待补】
- [ ] 「新建 / 既有」居住社区的判定口径与分界年（阈值分叉依据）【待核】
- [ ] 完整居住社区标准中「居住人口 ≤ 5000」的社区是否免判【待核】"""
NEW_Q = """- [x] 设施类「面积」属性 —— **已补** `facilityArea`（设施占地面积，适用设施对象公共基类），见 `属性与关系.md` §2.3
- [x] 「居住人口 ≤ 5000」的社区是否免判 —— **已决议：不免判**，取 100 / 600 ㎡（大王 2026-11-08 补充口径，**非标准原文**）
- [ ] 「场地建设年代 → 新建 / 既有」的**分界年**【待核】（判定依据已定：看场地本身的建设年代，非社区/小区）
- [ ] 场地级台账缺失（源数据仅小区级汇总）——指标 14 本期只能近似判定【待补】"""
assert OLD_Q in t
t = t.replace(OLD_Q, NEW_Q, 1)
open(P1, "w", encoding="utf-8", newline="\n").write(t)
print("类与层级.md OK", len(t.encode("utf-8")))

# ==================== 2) 属性与关系.md ====================
P2 = str(D / "属性与关系.md")
lines = open(P2, encoding="utf-8", newline="").read().replace("\r\n", "\n").split("\n")

# 2.1 对象属性表
start = next(k for k, l in enumerate(lines) if l.startswith("| 关系"))
end = start
while end < len(lines) and lines[end].startswith("|"):
    end += 1
rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in lines[start:end]]
assert not any(len(r) > 2 and r[2] == "`aggregatedFrom`" for r in rows), "已存在"

for r in rows:
    if len(r) > 3 and r[2] == "`assesses`":
        r[3] = "AssessmentResult / IndicatorJudgement → SpatialUnit"
        r[4] = ("**2026-11-08 新增（W-C01）**：评估**落在哪个空间单元**，基数 1..1。与 `measures`（指标数的是什么）、`computedFrom`（由什么算出）**三线正交**。"
                "2026-11-08 第二次扩域：定义域加 `IndicatorJudgement`（指标判断）——**判断是对象级、结果是汇总级**，两者都要绑单元")

NEW_ROWS = [
    ["聚合自", "aggregated from", "`aggregatedFrom`", "AssessmentResult → IndicatorJudgement",
     "**2026-11-08 新增**：评估结果由哪些判断聚合而来，基数 1..n。判断是**对象级**（三值），结果是**汇总级**（数值 + grade），**粒度不同、不可合并**", "建模稿（本轮新增）"],
    ["证据", "based on evidence", "`basedOnEvidence`", "IndicatorJudgement → 设施对象（`PublicActivityVenue` 等）",
     "**2026-11-08 新增**：判断所依据的设施实例，基数 0..n——`未配建` 时为 0（无实例即缺项），`达标 / 配建不达标` 时 ≥1。这是「判定可追溯」的落点", "建模稿（本轮新增）"],
]
k = next(a for a, r in enumerate(rows) if len(r) > 2 and r[2] == "`assesses`")
rows[k + 1:k + 1] = NEW_ROWS
lines[start:end] = render(rows)

# 2.2 新增 §2.3
t = "\n".join(lines)
SEC = [
    "",
    "### 2.3 指标判断层属性（2026-11-08 新增，指标 14 拆解驱动）",
    "",
    "> **为什么单列一层**：指标 14「未达标配建的公共活动场地的社区数量」的判定**逐个社区**发生（三值），而结果只在**城区**汇总（计数）。判断与结果粒度不同，故分设 `IndicatorJudgement`（指标判断）与 `AssessmentResult`（评估结果）。",
    "> **复用范围**：指标 9 / 10 / 20 / 21（养老、托育、运动场地、文化中心）同构。",
    "",
    "| 属性 | URI 名 | 适用类 | 值域 | 说明 |",
    "| --- | --- | --- | --- | --- |",
    "| 指标判断值 | `judgementValue` | `IndicatorJudgement` | 枚举：**未配建 / 配建不达标 / 达标** | 三值。`未配建` 与 `配建不达标` **必须分开**——前者对策是新建、后者是扩建，合成一个「不达标」会把两类更新需求混掉 |",
    "| 设施占地面积 | `facilityArea` | 设施对象公共基类（`PublicActivityVenue` / `ParkGreenSpace` / `MiddleSchool` 等） | decimal（㎡） | 单个设施实体的面积。⚠️ 与小区级填报口径 `publicVenueArea`（该小区场地面积汇总）**不是一回事**，勿混 |",
    "",
    "> **`complianceStatus`（配建达标状态，既有）与 `judgementValue` 的分工**：前者是**单个设施是否达标**（设施级，达标/不达标）；后者是**某单元对该指标的整体判断**（单元级，含「未配建」）。不复用、不合并。",
    "",
]
anchor = "## 三、借鉴同事成果新增的属性与约束"
assert anchor in t
t = t.replace(anchor, "\n".join(SEC) + anchor, 1)

# 2.3 §四 约束
CONS = [
    "- [x] `judgementValue` **枚举（2026-11-08 新增）**：取值 ∈ {未配建, 配建不达标, 达标}（`owl:oneOf` / `sh:in`）。",
    "- [x] **判断唯一性（2026-11-08 新增）**：同一体检内 `(指标, 空间单元)` 只能有 1 条 `IndicatorJudgement`（`sh:sparql`，防重复判定）。",
    "- [x] **证据基数（2026-11-08 新增）**：`judgementValue = 未配建` → `basedOnEvidence` **0 条**（`sh:maxCount 0`）；`达标 / 配建不达标` → **≥1 条**（`sh:minCount 1`）。",
    "- [x] **聚合一致（2026-11-08 新增）**：指标 14 的 `AssessmentResult.indicatorValue` = `count(IndicatorJudgement where judgementValue ≠ 达标)`；`grade = 未达标` 当且仅当该计数 > 0（`sh:sparql`）。",
    "- [x] `facilityArea` **非负**：`sh:minInclusive 0`，单位统一 ㎡。",
    "",
]
anchor2 = "## 五、已知风险"
assert anchor2 in t
t = t.replace(anchor2, "\n".join(CONS) + anchor2, 1)

# 2.4 §五 风险
RISK = [
    "- **评估链已拆两级（2026-11-08）**：`IndicatorJudgement`（对象级、三值）→ `AssessmentResult`（汇总级、数值）。原先把「判定」和「计数」挤在 `AssessmentResult` 上，导致一条结果既要说「这个社区达不达标」又要说「全区几个未达标」，粒度冲突。折成两级后，判断可逐社区追溯、结果可聚合校验，且直接复用于指标 9 / 10 / 20 / 21。",
    "- **`未配建` 必须显式判（2026-11-08）**：OWL 开放世界（Open World）下「查不到场地实例」推不出「没有场地」。规则须用 `NOT EXISTS`，或装载时显式写判断事实；否则情况 1 漏判，指标值偏小。",
    "- **`facilityArea`（设施实体面积）≠ `publicVenueArea`（小区级汇总）**：前者是判定用的单实例面积，后者是源表填报的小区汇总值。二者混用会使「任一片满足」退化成「平均面积达标」，结论方向都会变。",
    "- **阈值含地方补充口径（2026-11-08）**：>5000 人的 150 / 800 ㎡ 源自建科规〔2020〕7号；**≤5000 人的 100 / 600 ㎡ 为大王补充口径、非标准原文**，引用须标【口径补充】，不得写成标准条款。",
    "- **「新建 / 既有」看在建设施的年代，不看社区/小区（2026-11-08 大王口径）**：故判定依据属性须落到 `PublicActivityVenue.constructionYear`（由既有 `constructionYear` 扩定义域承担）；**分界年待核**。",
]
t = t.rstrip("\n") + "\n" + "\n".join(RISK) + "\n"
open(P2, "w", encoding="utf-8", newline="\n").write(t)
print("属性与关系.md OK", len(t.encode("utf-8")))
