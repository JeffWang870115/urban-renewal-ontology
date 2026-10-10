# -*- coding: utf-8 -*-
"""2026-10-10 结构性微调（折中方案 + 指标导向）：
  1) §一 对象属性表：新增 `belongsToDimension`（分类归属维度）
  2) §二 数据属性表：新增 `orientation`（指标导向）
  3) §四 约束：新增 belongsToDimension 基数约束
只重排被改的两张表；其余不动。
"""
import unicodedata

P = r"E:\中设数字\00-01-个人\02-学习\01-wordbuddy\2026_working_space\城市体检与更新本体研究\03-本体模型\属性与关系.md"


def w(s):
    return sum(2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1 for c in s)


def pad(s, n):
    return s + ' ' * max(0, n - w(s))


def is_sep(r):
    return all(set(c) <= set('-: ') for c in r)


def reflow(rows):
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
    return out


txt = open(P, encoding='utf-8', newline='').read().replace('\r\n', '\n')
lines = txt.split('\n')


def find_table(prefix, start_from=0):
    s = None
    for i in range(start_from, len(lines)):
        if lines[i].startswith(prefix):
            s = i
            break
    if s is None:
        raise SystemExit('未找到表头: ' + prefix)
    e = s
    while e < len(lines) and lines[e].startswith('|'):
        e += 1
    return s, e


# ---- 1) §一 对象属性表：插入 belongsToDimension ----
s, e = find_table('| 关系')
rows = [[c.strip() for c in l.strip().strip('|').split('|')] for l in lines[s:e]]
if not any(len(r) >= 3 and r[2] == '`belongsToDimension`' for r in rows):
    idx = next(i for i, r in enumerate(rows) if len(r) >= 3 and r[2] == '`inCategory`')
    newrow = ['分类归属维度', 'belongs to dimension', '`belongsToDimension`', 'IndicatorCategory → Dimension',
              '**2026-10-10 新增（折中方案）**：`IndicatorCategory` 实例**显式归属**到 `Dimension` 实例；**一对多**（如「设施完善」同归社区维度 + 小区维度）。分类轴仍与 `Dimension` **平行独立**（不合并），本关系仅补显式归属记录。',
              '建模稿（本轮新增）']
    rows.insert(idx + 1, newrow)
    lines[s:e] = reflow(rows)
    print('§一 已插入 belongsToDimension')
else:
    print('§一 已存在，跳过')

# ---- 2) §二 数据属性表：插入 orientation ----
# 重新定位（行号已变）
s, e = find_table('| 属性')
rows = [[c.strip() for c in l.strip().strip('|').split('|')] for l in lines[s:e]]
if not any(len(r) >= 2 and r[1] == '`orientation`' for r in rows):
    idx = next(i for i, r in enumerate(rows) if len(r) >= 2 and r[1] == '`formula`')
    newrow = ['指标导向', '`orientation`', 'Indicator',
              '枚举（正向 / 逆向）；**正向 = 数值越高越好；逆向 = 越低越好**（未来或增「区间」型）',
              '已确认（2026-10-10 大王拍板）']
    rows.insert(idx + 1, newrow)
    lines[s:e] = reflow(rows)
    print('§二 已插入 orientation')
else:
    print('§二 已存在，跳过')

# ---- 3) §四 约束：新增 belongsToDimension 基数 ----
anchor = None
for i, l in enumerate(lines):
    if l.startswith('- [x] `formula` **完整性**'):
        anchor = i
        break
if anchor is not None:
    newb = ('- [x] `belongsToDimension` **基数（2026-10-10 新增·折中方案）**：每个 `IndicatorCategory` 至少归属 1 个 `Dimension`'
            '（`sh:minCount 1`），**允许一对多**（如「设施完善」同归社区维度 + 小区维度）；分类轴仍与 `Dimension` 平行独立，'
            '本关系仅显式记录归属（决议见 `类与层级.md` §2.10.3）。')
    if '`belongsToDimension` **基数' not in txt:
        lines.insert(anchor + 1, newb)
        print('§四 已插入约束')
    else:
        print('§四 已存在，跳过')

open(P, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
print('WROTE:', P)
