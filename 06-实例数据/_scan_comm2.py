# -*- coding: utf-8 -*-
"""探查三尺度结果表列结构（只读，不产出项目文件）。"""
import glob, os, warnings
import openpyxl
warnings.filterwarnings('ignore')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 06-实例数据 -> 项目根
MAT = os.path.join(ROOT, '01-资料')


def find(name):
    hits = [p for p in glob.glob(os.path.join(MAT, '**', name), recursive=True)
            if not os.path.basename(p).startswith('~$')]
    return hits


def profile(name):
    hits = find(name)
    print('\n########', name, '->', len(hits), 'hit(s)')
    if not hits:
        return
    p = hits[0]
    wb = openpyxl.load_workbook(p, data_only=True)
    ws = wb.worksheets[0]
    print('dims', ws.max_row, 'x', ws.max_column, '| rel', os.path.relpath(p, ROOT))
    print('--- 前 4 行原文 ---')
    for i, r in enumerate(ws.iter_rows(min_row=1, max_row=min(4, ws.max_row), values_only=True), 1):
        print(' r%d:' % i, [('' if c is None else str(c).strip())[:26] for c in r])
    print('--- 逐列画像（表头取 1..3 行）---')
    for c in range(1, ws.max_column + 1):
        heads = [str(ws.cell(r, c).value).strip() for r in range(1, 4)
                 if ws.cell(r, c).value is not None]
        vals = [ws.cell(r, c).value for r in range(4, ws.max_row + 1)]
        ne = [v for v in vals if v is not None and str(v).strip() != '']
        sample = [str(v)[:22] for v in ne[:2]]
        pos = sum(1 for v in ne if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0)
        print(' c%02d | %s | 非空 %d | >0 %d | 例 %s' %
              (c, ' / '.join(heads)[:52], len(ne), pos, sample))
    wb.close()


for n in ['社区数据.xlsx', '小区数据.xlsx', '街区数据.xlsx']:
    profile(n)
