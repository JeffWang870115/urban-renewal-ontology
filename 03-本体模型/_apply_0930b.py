# -*- coding: utf-8 -*-
"""2026-09-30b 消化大王 §四 批注 + 执行 RecordObject -> ManagementObject 更名。
批注对照：
  308 （可以）        -> 同意更名「管理对象」【执行改名】
  309 （保持待核）    -> 维持【待核】
  310 （保持待核）    -> 维持【待核】
  311 （保持待核）    -> 维持【待核】
  312 （明确不纳入）  -> 决议：TD/T 1063-2021 新版标准号不纳入（打勾）
约定：正文批注文字移除，改为「（日期+批注）」决议记录；CRLF=0。
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
    log.append((("[OK] " if n == 1 else "[WARN n=%d] " % n)) + tag)

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
    log.append((("[OK] " if n == 1 else "[WARN n=%d] " % n)) + tag)

# ================= 文件1 类与层级.md =================
p1 = os.path.join(BASE, "03-本体模型", "类与层级.md")
L1 = read(p1).split("\n")

# --- 1) §2.9.1 表：改名 + 整表重排（字符数对齐，第 4 列含在内） ---
start = next(i for i, ln in enumerate(L1) if ln.startswith("| 分类父类"))
block = L1[start:start + 8]

def parse(ln):
    parts = ln.split("|")
    if len(parts) < 6:
        return None
    return [parts[j].strip() for j in range(1, 5)]

data = [parse(x) for x in block]
for r in data:
    if r and r[0] == "记录对象":
        r[0] = "管理对象"
        r[1] = "Management Object"
        r[2] = "`ManagementObject`"

W = [0, 0, 0, 0]
for i, r in enumerate(data):
    if i == 1:
        continue
    for j in range(4):
        W[j] = max(W[j], len(r[j]))

new_block = []
for i, r in enumerate(data):
    if i == 1:
        segs = ["-" * W[j] for j in range(4)]
    else:
        segs = [r[j].ljust(W[j]) for j in range(4)]
    new_block.append("| " + " | ".join(segs) + " |")
L1[start:start + 8] = new_block
log.append("[OK] F1.§2.9.1 表改名+重排 (列宽 %s)" % W)

# --- 2) §2.9.1 归属注：改名消化 ---
sub(L1, "移入记录对象。记录对象现收纳",
    [("移入记录对象。记录对象现收纳「记录 / 台账 / 管理」类对象，其命名（是否收紧为「管理对象」）【待核】。",
      "移入**管理对象 `ManagementObject`**（2026-09-30 决议：由原「记录对象 `RecordObject`」更名）。管理对象现收纳「记录 / 台账 / 管理」类对象。")],
    "F1.§2.9.1 归属注")

# --- 3) §四 306：移入记录对象 -> 移入管理对象 ---
sub(L1, "危险较大".replace("危险较大", "危险性较大分部分项工程、城市运行管理平台移入记录对象"),
    [("移入记录对象 —— **已决议**", "移入**管理对象 `ManagementObject`** —— **已决议**")],
    "F1.§四306")

# --- 4) §四 308 改名决议 ---
whole(L1, "- [ ] 记录对象 `RecordObject` 命名（现收纳",
      "- [x] 记录对象命名（2026-09-30 大王批注：**可以**）：由「记录对象 `RecordObject`」更名「管理对象 `ManagementObject`」 —— **已决议**。",
      "F1.§四308 改名决议")

# --- 5) §四 309 去批注 ---
whole(L1, "- [ ] `FormulaType` / `CollectionMethod` 枚举值穷尽性【待核】（保持待核）",
      "- [ ] `FormulaType` / `CollectionMethod` 枚举值穷尽性【待核】",
      "F1.§四309")

# --- 6) §四 310 去批注 ---
sub(L1, "作为 `Problem.problemCategory` 取值的来源",
    [("（学术口径，非标准）（保持待核）", "（学术口径，非标准）")],
    "F1.§四310")

# --- 7) §四 311 去批注 ---
sub(L1, "达标等级枚举（达标 / 基本达标 / 不达标）",
    [("待与 55 项指标标准核对【待核】（保持待核）", "待与 55 项指标标准核对【待核】")],
    "F1.§四311")

# --- 8) §四 312 明确不纳入 ---
whole(L1, "- [ ] TD/T 1063-2021 新版标准号【待核】（自然资源口边界",
      "- [x] TD/T 1063-2021 新版标准号（自然资源口边界）—— **已明确不纳入**（2026-09-30 大王批注）。",
      "F1.§四312")

write(p1, "\n".join(L1))

# ================= 文件2 属性与关系.md =================
p2 = os.path.join(BASE, "03-本体模型", "属性与关系.md")
L2 = read(p2).split("\n")
whole(L2, "- **记录对象 `RecordObject` 收纳范围已扩展（2026-09-30 大王批注）**",
      "- **管理对象 `ManagementObject`（原「记录对象 `RecordObject`」）收纳范围已扩展（2026-09-30 大王批注）**：`RiskyConstructionWorks`（危险性较大分部分项工程）、`UrbanOperationPlatform`（城市运行管理平台）由原「事件对象 / 设施对象」移入**管理对象**；2026-09-30 决议由「记录对象 `RecordObject`」更名「管理对象 `ManagementObject`」（现收纳「记录 / 台账 / 管理」类对象）。影响 `.ttl` 的 `rdfs:subClassOf` 与后续 SHACL `sh:targetClass`。",
      "F2.§五 管理对象风险条")
write(p2, "\n".join(L2))

# ================= 校验 =================
print("== 日志 ==")
for x in log:
    print(x)
print("== CRLF（应 0） + 残留“记录对象”（应 0） ==")
for p in (p1, p2):
    raw = open(p, "rb").read()
    s = raw.decode("utf-8")
    print(" ", os.path.basename(p), "CRLF=", raw.count(b"\r\n"),
          "| 残留'记录对象'=", s.count("记录对象"), "| 残留'RecordObject'=", s.count("RecordObject"),
          "| 'ManagementObject'=", s.count("ManagementObject"))
print("== §2.9.1 表列数 ==")
for ln in read(p1).split("\n"):
    if ln.startswith("| 分类父类") or ln.startswith("| 管理对象"):
        print("  ", ln.count("|"), ln[:40])
