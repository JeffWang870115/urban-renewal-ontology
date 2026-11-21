# 街区维度 24–26 更新侧闭环 · 真实数据接入版

> 生成器：`_gen_街区更新真实_v1.py`（可重跑，seed=20261117）
> 产物：`城市体检实例-街区更新真实.ttl`（增量，须与主 ABox + TBox 合并载入）、
> `街区更新真实-对账报表.csv`、`README-街区更新真实.md`
> 状态：【真实底稿·脱敏接入】——对象/核查项取自 5 张街道调查统计表；精确面积只留本地，公开版标量级/缺。

## 〇、与 pilot 版的关系

本版**替代** `_gen_街区更新闭环_pilot.py` 的虚构样本（同匿名 URI 编码 OCB/OIA/ORB_{A–E}_{k}）。
两者勿同时载入，否则同一 URI 会叠加虚构 + 真实的 `failsCheckItem`。

## 一、数据来源与脱敏

- 输入：本地 `01-资料/` 下 5 张街道调查统计表（真实底稿，本地只读；路径与真名在生成器运行时从
  **不入库**的本地映射表读取，本源码及公开产物均不含真实地名）。
- 街道真名 → A–E；对象真名 → `OCB/OIA/ORB_{街道}_{k}` 匿名编码。
- **本地真值对照**：`01-资料/` 下脱敏映射目录的对象匿名对照表（不入库）。
- 公开产物真实地名 **0 命中**。

## 二、真实对象清单（脱敏）

| 街道 | 指标 | 匿名对象 | 占地面积 | 建筑面积 | 命中核查项 |
|---|---|---|---|---|---|
| A | 24 | `OCB_A_1` | 源数据缺 | 源数据缺 | CI_C_2, CI_C_4, CI_C_5 |
| A | 24 | `OCB_A_2` | 源数据缺 | 源数据缺 | CI_C_1, CI_C_4 |
| B | 24 | `OCB_B_1` | 源数据缺 | 源数据缺 | CI_C_4, CI_C_5 |
| B | 25 | `OIA_B_1` | 源数据缺 | 源数据缺 | CI_F_10, CI_F_3 |
| C | 24 | `OCB_C_1` | 千㎡级 | 千㎡级 | CI_C_1, CI_C_4, CI_C_5 |
| C | 24 | `OCB_C_2` | 千㎡级 | 百㎡级 | CI_C_2, CI_C_4, CI_C_5 |
| C | 24 | `OCB_C_3` | 千㎡级 | 百㎡级 | CI_C_1, CI_C_4, CI_C_5 |
| C | 26 | `ORB_C_1` | 万㎡级 | 万㎡级 | CI_L_2, CI_L_3, CI_L_5, CI_L_7 |
| D | 24 | `OCB_D_1` | 源数据缺 | 源数据缺 | CI_C_5 |
| D | 24 | `OCB_D_2` | 源数据缺 | 源数据缺 | CI_C_4, CI_C_5 |
| D | 25 | `OIA_D_1` | 十万㎡级 | 源数据缺 | CI_F_10, CI_F_3 |
| E | 24 | `OCB_E_1` | 源数据缺 | 源数据缺 | CI_C_4, CI_C_5 |

合计 **12** 个真实对象（商业街区 9 / 厂区 2 / 生活街区 1），与既有 AR 值完全对齐。

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
2. 映射覆盖：12 对象均 `failsCheckItem` 到有效核查项，`checkItemFor` 对齐本指标。
3. 全链回溯：SPARQL 从 `AR_NB_C_I24` 追到 对象→核查项→问题→建议→项目。
4. 脱敏 0 命中（含 README 自身）；源码 0 真名；CRLF=0；负向测试（OR 规则）通过。

## 七、已知局限

- **面积多缺**：12 对象中 7 个未填占地面积、8 个未填建筑面积，标"源数据缺"，不虚构。
- **W-B01 部分推进（2026-11-17）**：12 个 Problem 已归位 `NeighborhoodProblem` 子类；`RemediationSuggestion`/`RenewalProject` 仍用父类（判定规则【待核】未强标）；`severity` 为示意数值、档位边界采用候选值【待核·建议】。
- **映射已复核定稿**：见 §五（2026-11-17 大王复核）；"设施老旧"提交为开放问题——若后续取得其判定口径（属哪条核查项/是否独立成项），可再补链。
