# -*- coding: utf-8 -*-
"""补丁：仅修复 属性与关系.md（_apply_0930.py 遗漏 write(p2)）。
只做两处：① 切换时机条标决议；② 末尾追加「记录对象收纳范围扩展」风险条。"""
import os
BASE = r"E:\中设数字\00-01-个人\02-学习\01-wordbuddy\2026_working_space\城市体检与更新本体研究"
p2 = os.path.join(BASE, "03-本体模型", "属性与关系.md")
L2 = open(p2, encoding="utf-8").read().split("\n")

n1 = 0
for i, ln in enumerate(L2):
    if "切换时机 = 步骤 3 机读序列化。" in ln:
        L2[i] = ln.replace("；切换时机 = 步骤 3 机读序列化。",
                           "；**已决议（2026-09-30 大王批注）：切换时机 = 步骤 3 机读序列化**。")
        n1 += 1

risk_new = "- **记录对象 `RecordObject` 收纳范围已扩展（2026-09-30 大王批注）**：`RiskyConstructionWorks`（危险性较大分部分项工程）、`UrbanOperationPlatform`（城市运行管理平台）由原「事件对象 / 设施对象」移入**记录对象**；该父类现收纳「记录 / 台账 / 管理」类对象，其命名（是否收紧为「管理对象」）【待核】。影响 `.ttl` 的 `rdfs:subClassOf` 与后续 SHACL `sh:targetClass`。"
n2 = 0
if L2 and not L2[-1].strip():
    L2.insert(len(L2) - 1, risk_new)
    n2 = 1
else:
    L2.append(risk_new)
    n2 = 1

with open(p2, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(L2))

# 回读校验
raw = open(p2, "rb").read()
s = raw.decode("utf-8")
print("替换命中: 切换时机条=%d, 风险条=%d" % (n1, n2))
print("now has 2026-09-30:", "2026-09-30" in s)
print("now has 记录对象收纳范围已扩展:", "记录对象收纳范围已扩展" in s)
print("CRLF:", raw.count(b"\r\n"), "| size:", len(raw))
