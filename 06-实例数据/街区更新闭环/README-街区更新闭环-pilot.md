# 街区维度 24–26 更新侧闭环 Pilot（端到端最小闭环实证）

> 生成器：`_gen_街区更新闭环_pilot.py`（可重跑，固定 seed=20261114）
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

- 老旧对象实例（RenewalObject 子类）：**12** 个（各命中≥1 核查项，满足 OR 规则）
- 问题短板 Problem：**8** 个（每条 AR 1:1 派生）
- 整治建议 RemediationSuggestion：**46** 条
- 更新项目 RenewalProject：**46** 个（各 `actsOn` 命中该核查项的老旧对象，`adoptsApproach` 改造/提升）

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
