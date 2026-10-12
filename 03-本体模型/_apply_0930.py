# -*- coding: utf-8 -*-
"""2026-09-30 执行大王三项拍板：
1) 桥梁留设施对象；危大工程 / 运行管理平台 移入记录对象
2) FormulaType / CollectionMethod 切换时机 = 步骤 3（标决议）
3) PolicyIntervention -> RenewalProject 术语对齐（概念清单新增术语）
写文件统一 newline='\n'，避免 Windows CRLF 陷阱。
"""
from pathlib import Path
import os

BASE = str(Path(__file__).resolve().parent.parent)

def read(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()

def write(p, s):
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)

log = []

def whole(lines, key, new, tag):
    n = 0
    for i, ln in enumerate(lines):
        if key in ln:
            lines[i] = new
            n += 1
    log.append(("[OK] " if n == 1 else "[WARN n=%d] " % n) + tag)

def sub(lines, key, pairs, tag):
    n = 0
    for i, ln in enumerate(lines):
        if key in ln:
            o = ln
            for a, b in pairs:
                if a not in ln:
                    log.append("[MISS] %s -> %s" % (tag, a[:50]))
                ln = ln.replace(a, b)
            if ln != o:
                lines[i] = ln
                n += 1
    log.append(("[OK] " if n == 1 else "[WARN n=%d] " % n) + tag)

# ---------- 文件1 类与层级.md ----------
p1 = os.path.join(BASE, "03-本体模型", "类与层级.md")
L1 = read(p1).split("\n")
sub(L1, "| 设施对象 ", [("、城市运行管理平台（17）", "（16）")], "F1.设施对象行")
sub(L1, "| 事件对象 ", [("、危险性较大分部分项工程（3）", "（2）")], "F1.事件对象行")
sub(L1, "| 记录对象 ", [("公租房轮候记录（1）", "公租房轮候记录、危险性较大分部分项工程、城市运行管理平台（3）")], "F1.记录对象行")
whole(L1, "归属为**建模草案**；",
      "> 归属为**建模草案**；**已决议（2026-09-30 大王批注）**：桥梁 `Bridge` 保留设施对象；危险性较大分部分项工程 `RiskyConstructionWorks`、城市运行管理平台 `UrbanOperationPlatform` 移入记录对象。记录对象现收纳「记录 / 台账 / 管理」类对象，其命名（是否收紧为「管理对象」）【待核】。",
      "F1.§2.9.1 归属注")
sub(L1, "本期保留字符串写法，类作为受控词表备用",
    [("**本期保留字符串写法，类作为受控词表备用**（待步骤 3 机读序列化时切换）。",
      "**已决议（2026-09-30 大王批注）：本期保留字符串写法，类作为受控词表备用，切换时机 = 步骤 3（55 项指标机读序列化）。**")],
    "F1.§2.9.2 切换注")
whole(L1, "- [ ] 分类父类归属（桥梁 / 危大工程 / 运行管理平台）",
      "- [x] 分类父类归属（2026-09-30 大王批注）：桥梁 `Bridge` 保留设施对象；危险性较大分部分项工程、城市运行管理平台移入记录对象 —— **已决议**。\n"
      "- [x] `FormulaType` / `CollectionMethod` 切换时机（2026-09-30 大王批注）：本期保留字符串，**步骤 3 机读序列化时切换** —— **已决议**。\n"
      "- [ ] 记录对象 `RecordObject` 命名（现收纳「记录 / 台账 / 管理」类对象，是否收紧为「管理对象」）【待核】\n"
      "- [ ] `FormulaType` / `CollectionMethod` 枚举值穷尽性【待核】",
      "F1.§四待决行")
write(p1, "\n".join(L1))

# ---------- 文件2 属性与关系.md ----------
p2 = os.path.join(BASE, "03-本体模型", "属性与关系.md")
L2 = read(p2).split("\n")
sub(L2, "切换时机 = 步骤 3 机读序列化。",
    [("；切换时机 = 步骤 3 机读序列化。", "；**已决议（2026-09-30 大王批注）：切换时机 = 步骤 3 机读序列化**。")],
    "F2.切换时机条")
risk_new = "- **记录对象 `RecordObject` 收纳范围已扩展（2026-09-30 大王批注）**：`RiskyConstructionWorks`（危险性较大分部分项工程）、`UrbanOperationPlatform`（城市运行管理平台）由原「事件对象 / 设施对象」移入**记录对象**；该父类现收纳「记录 / 台账 / 管理」类对象，其命名（是否收紧为「管理对象」）【待核】。影响 `.ttl` 的 `rdfs:subClassOf` 与后续 SHACL `sh:targetClass`。"
if L2 and not L2[-1].strip():
    L2.insert(len(L2) - 1, risk_new)
else:
    L2.append(risk_new)
log.append("[OK] F2.新增记录对象风险条")
write(p2, "\n".join(L2))

# ---------- 文件3 概念清单.md ----------
p3 = os.path.join(BASE, "02-术语与概念", "概念清单.md")
L3 = read(p3).split("\n")
new_row = "| 治理处方 | Policy Intervention | 同事 `PolicyIntervention`，指城市病（问题短板）的治理措施；**与我方「更新项目 `RenewalProject`」为概念映射、不等同**（更新项目含对象 / 方式 / 主体 / 资金四要素） | 问题识别 | 借鉴同事 `PolicyIntervention` | 概念映射·不照搬 |"
n = 0
for i, ln in enumerate(L3):
    if ln.startswith("| 问题性质分类 |"):
        L3.insert(i + 1, new_row)
        n += 1
        break
log.append(("[OK] " if n == 1 else "[WARN n=%d] " % n) + "F3.§九新增治理处方行")
align = "> **术语对齐（2026-09-30 大王批注·选项 a）**：同事「治理处方 `PolicyIntervention`」与我方「更新项目 `RenewalProject`」为**概念映射关系，不等同**——前者是问题短板的治理措施（措施语义），后者是含**更新对象 / 更新方式 / 行动主体 / 资金**四要素的项目单元（项目语义）。**不照搬同事类名**，我方主干仍用 `RenewalProject`。"
n = 0
for i, ln in enumerate(L3):
    if ln.startswith("> **边界提示**"):
        j = i
        while j < len(L3) and L3[j].strip() != "":
            j += 1
        L3.insert(j, align)
        n += 1
        break
log.append(("[OK] " if n == 1 else "[WARN n=%d] " % n) + "F3.§九术语对齐段")
write(p3, "\n".join(L3))

# ---------- 校验 ----------
def crlf(p):
    with open(p, "rb") as f:
        return f.read().count(b"\r\n")

print("== 替换日志 ==")
for x in log:
    print(x)
print("== CRLF 校验（应为 0）==")
for p in (p1, p2, p3):
    print(" ", os.path.basename(p), crlf(p))
print("== 表格列数抽查（应一致）==")
for p, keys in ((p1, ["| 设施对象 ", "| 空间对象 ", "| 事件对象 ", "| 记录对象 "]), (p3, ["| 治理处方 |", "| 问题性质分类 |"])):
    L = read(p).split("\n")
    for k in keys:
        for ln in L:
            if ln.startswith(k):
                print(" ", k.strip(), "-> 竖线数", ln.count("|"))
                break
