# -*- coding: utf-8 -*-
import unicodedata, os

def w(s):
    return sum(2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1 for c in s)

base = r"E:\中设数字\00-01-个人\02-学习\01-wordbuddy\2026_working_space\城市体检与更新本体研究\03-本体模型"
for name in ['属性与关系.md', '类与层级.md']:
    p = os.path.join(base, name)
    b = open(p, 'rb').read()
    t = b.decode('utf-8')
    print('%s | CRLF=%d | 字节=%d' % (name, b.count(b'\r'), len(b)))

# 表格列宽一致性（对象属性表）
p = os.path.join(base, '属性与关系.md')
lines = open(p, encoding='utf-8', newline='').read().split('\n')
st = next(i for i, l in enumerate(lines) if l.startswith('| 关系'))
en = st
while en < len(lines) and lines[en].startswith('|'):
    en += 1
ws = [w(l) for l in lines[st:en]]
print('对象属性表 行数=%d  每行显示宽度 min=%d max=%d  一致=%s' % (len(ws), min(ws), max(ws), len(set(ws)) == 1))

# 关键内容校验
t2 = open(p, encoding='utf-8').read()
for k in ['角色类', 'owl:unionOf', 'sh:or', '决议 A']:
    print('  属性与关系 含「%s」: %s' % (k, k in t2))
t3 = open(os.path.join(base, '类与层级.md'), encoding='utf-8').read()
for k in ['2026-09-29 大王批注·第五次', '角色类（role class）']:
    print('  类与层级 含「%s」: %s' % (k, k in t3))
