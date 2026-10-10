# -*- coding: utf-8 -*-
"""修改 属性与关系.md 的 computedFrom / feedsInto 两行，并只重排"一、对象属性"这张表。"""
import unicodedata, os, shutil

P = r"E:\中设数字\00-01-个人\02-学习\01-wordbuddy\2026_working_space\城市体检与更新本体研究\03-本体模型\属性与关系.md"

BAK = r"E:\中设数字\00-01-个人\02-学习\01-wordbuddy\2026_working_space\城市体检与更新本体研究\03-本体模型\_bak_20260929"
os.makedirs(BAK, exist_ok=True)
shutil.copy2(P, os.path.join(BAK, '属性与关系.md.bak1'))
print('backup ->', os.path.join(BAK, '属性与关系.md.bak1'))

def w(s):
    return sum(2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1 for c in s)

def pad(s, n):
    return s + ' ' * max(0, n - w(s))

txt = open(P, encoding='utf-8', newline='').read().replace('\r\n', '\n')
lines = txt.split('\n')

# --- 1) 定位"一、对象属性"表 ---
start = None
for i, l in enumerate(lines):
    if l.startswith('| 关系'):
        start = i
        break
if start is None:
    raise SystemExit('未找到对象属性表')

end = start
while end < len(lines) and lines[end].startswith('|'):
    end += 1

rows = [[c.strip() for c in l.strip().strip('|').split('|')] for l in lines[start:end]]

# --- 2) 改单元格 ---
for r in rows:
    if len(r) >= 5 and r[2] == '`computedFrom`':
        r[3] = 'Indicator → DataObject（角色类）'
        r[4] = ('**指标由哪些数据对象派生**，基数 1..n；`DataObject` 为**角色类**，值域兼容复用实体 '
                '`SpatialUnit` / `RenewalObject` / `Problem` / `RenewalProject`（2026-09-29 决议 A，类与层级 §2.8）')
        if len(r) >= 6:
            r[5] = '已决议'
    if len(r) >= 5 and r[2] == '`feedsInto`':
        r[3] = 'DataObject（角色类）→ Indicator'
        r[4] = '反向，数据对象被哪些指标引用（多对多）；定义域随 `computedFrom` 值域同步放宽，复用实体亦可 `feedsInto`（2026-09-29 决议 A）'

def is_sep(r):
    return all(set(c) <= set('-: ') for c in r)

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
        out.append('|' + '|'.join('-' * (widths[j] + 2) for j in range(len(r))) + '|')
    else:
        out.append('|' + '|'.join(' ' + pad(c, widths[j]) + ' ' for j, c in enumerate(r)) + '|')

lines[start:end] = out
open(P, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
print('OK rows=%d cols=%d widths=%s' % (len(rows), ncol, widths))
