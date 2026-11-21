# -*- coding: utf-8 -*-
"""
楼栋台账读取共享模块（2026-11-20）
====================================
权威源：01-资料/*/楼栋数据.xlsx（大王 11-20 指定的最终版，取代 楼栋数据汇总表.xlsx）
表结构：表头第1行=维度名、第2行=指标号、第3行=指标名、数据第4行起；
        街道/社区/小区列用合并单元格（稀疏填写），须向下填充；隐患列按第3行指标名定位。
功能：read_scopes() -> {(level, group): (denominator, numerator)} 供分尺度生成器/诊断导出共用。
纪律：源码零真名（路径动态发现）；脱敏由调用方负责。
"""
from pathlib import Path
from collections import Counter

PROJ = Path(__file__).resolve().parents[1]

# 8项隐患指标名前缀（第3行表头，按 2026 编号）
HAZARD_KEYS = {
    "1": "存在结构安全隐患", "2": "存在燃气安全隐患", "3": "存在楼道安全隐患",
    "4": "存在围护安全隐患", "5": "存在管线管道破损", "6": "适老化改造",
    "7": "节能改造", "8": "数字化改造",
}


def find_ledger():
    hits = sorted(PROJ.glob("01-资料/*/楼栋数据.xlsx"))
    assert hits, "找不到权威源 楼栋数据.xlsx"
    return hits[0]


def read_scopes():
    """返回 (stats, rows)：
    stats = {'district':{'den','num'}, 'street':{name:(den,num)}, 'community':{...}, 'quarter':{...}}
    rows  = 逐栋 [(街道,社区,小区,楼栋名,{指标:bool}), ...]（内存，不写出）
    """
    import openpyxl
    wb = openpyxl.load_workbook(find_ledger(), data_only=True)
    ws = wb.active

    def cell(c, r):
        x = ws.cell(r, c).value
        return str(x).strip() if x is not None and str(x).strip() else ""

    # 隐患列按第3行指标名定位（不写死列号，防表结构漂移）
    colmap = {}
    for c in range(1, ws.max_column + 1):
        h = str(ws.cell(3, c).value or "")
        for k, kw in HAZARD_KEYS.items():
            if kw in h and k not in colmap:
                colmap[k] = c
    assert len(colmap) == 8, f"隐患列定位不全：{colmap}"

    def truthy(c, r):
        x = ws.cell(r, c).value
        return x is not None and str(x).strip() not in ("", "否", "0", "无", "False", "false", "[]", "NaN")

    st, cm, qd = Counter(), Counter(), Counter()
    haz_total = Counter()
    rows = []
    last = ["", "", ""]
    n = 0
    for r in range(4, ws.max_row + 1):
        for i, c in enumerate([1, 2, 3]):          # 街道/社区/小区向下填充
            cur = cell(c, r)
            if cur:
                last[i] = cur
        bname = cell(4, r)
        if not bname:
            continue
        n += 1
        st[last[0]] += 1
        cm[last[1]] += 1
        qd[last[2]] += 1
        flags = {}
        for k, col in colmap.items():
            bad = truthy(col, r)
            if bad:
                haz_total[k] += 1
            flags[k] = bad
        rows.append((last[0], last[1], last[2], bname, flags))
    wb.close()
    assert n == 3599, f"权威楼栋行数应为 3599，实得 {n}"
    assert len(cm) == 53, f"社区数应为 53，实得 {len(cm)}"
    assert len(qd) == 404, f"小区数应为 404，实得 {len(qd)}"
    assert not any("支油区" in x for x in cm), "新表不应有支油区社区"

    stats = {
        "district": {"den": n, "num": haz_total["1"]},
        "street": {k: (v, 0) for k, v in st.items()},
        "community": {k: (v, 0) for k, v in cm.items()},
        "quarter": {k: (v, 0) for k, v in qd.items()},
    }
    # 分子回填（按各层级组）
    for s, c, qdname, bname, flags in rows:
        for lev, key in (("street", s), ("community", c), ("quarter", qdname)):
            if flags["1"]:
                den, num = stats[lev][key]
                stats[lev][key] = (den, num + 1)
    return stats, rows, haz_total


if __name__ == "__main__":
    s, rows, hz = read_scopes()
    print("楼栋", s["district"], "街道", len(s["street"]), "社区", len(s["community"]), "小区", len(s["quarter"]))
    print("结构隐患分子(城区/全市) =", hz["1"])
    # 脱敏：不写死社区真名；演示 CM_S01 的取数用「映射代号反查」方式
    _hits = sorted(PROJ.glob("01-资料/*/_脱敏映射/编号映射.csv"))
    if _hits:
        import csv as _csv
        with _hits[0].open(encoding="utf-8-sig") as _f:
            _cname = next((str(r.get("原名（本地，不入库）", "")).split("/")[-1].strip()
                           for r in _csv.DictReader(_f)
                           if str(r.get("编号", "")).strip() == "CM_S01"), "")
        print("CM_S01 =", s["community"].get(_cname))
