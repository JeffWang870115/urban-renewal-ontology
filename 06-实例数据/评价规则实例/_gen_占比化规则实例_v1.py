# -*- coding: utf-8 -*-
"""
占比化/均值化指标的评价规则 + 样本市实测值 接入生成器 v1（2026-11-19）
========================================================================
接 W-B02 第二步：住房 1–9、小区社区 10–21 共 20 项占比化/均值化指标。

数据来源与校核（大王 11-19 指示）：
- 自评表（样本市2025）：指标值、关联指标占比、全国平均值、四档分界【地方实操】
- 楼栋数据.xlsx（权威表）：复算 9 项隐患栋数，分母用名义总量 3599（大王 11-20 指定）
- 住房/社区维度调查表：校核分子分母来源

脱敏（D1 先例，大王 11-19 拍板）：
- 公开 ABox **不写真值**，用 rdfs:comment 标量级/缺；精确值写本地对照表（不入库）
- 本批指标值为公开统计口径下的量值，仍按 D1 标量级，真值留本地
- 四档分界与全国平均值属【地方实操】，basedOn 指地方来源并标注

纪律：CRLF=0；断言前置+负向测试；Path(__file__)；按名不按号；CRLF=0。
"""
from pathlib import Path
from rdflib import Graph, Namespace, Literal, RDF, RDFS, XSD

HERE = Path(__file__).resolve().parent
PROJ = HERE.parents[1]
TBOX = PROJ / "03-本体模型/城市体检-更新本体.ttl"
YAML = PROJ / "04-指标映射/55项指标.yaml"
# 脱敏：本地真值目录运行时动态发现（不写死地名目录名）
LOCAL_DIR = sorted(PROJ.glob("01-资料/*/_脱敏映射"))[0]
OUT = HERE / "城市体检实例-占比化评价规则.ttl"
LOCAL_CSV = LOCAL_DIR / "评价规则实测值对照.csv"   # 真值，不入库
NS = "https://ontology.cset-digital.cn/urban-renewal#"
UR = Namespace(NS)
DENOM = 3599   # 楼栋表序号上限（大王拍板分母）

# (2026序号, 指标名, 关联指标口径, 方法, 方向, 指标值(真), 占比(真), 全国平均值, 四档[(名,lo,hi,含lo,含hi)])
# 四档来自自评表【地方实操】；lo/hi 为关联指标占比%（或每小区均值）
ROWS = [
 (1,'存在结构安全隐患的住宅数量','结构隐患住宅占比%','占比化','逆向',255,7.09,3.52,
  [('很好',None,3.21,False,False),('较好',3.21,3.59,True,False),('一般',3.59,3.94,True,False),('不足',3.94,None,True,False)]),
 (2,'存在燃气安全隐患的住宅数量','燃气隐患住宅占比%','占比化','逆向',25,0.69,4.08,
  [('很好',None,3.66,False,False),('较好',3.66,4.09,True,False),('一般',4.09,4.49,True,False),('不足',4.49,None,True,False)]),
 (3,'存在楼道安全隐患的住宅数量','楼道隐患住宅占比%','占比化','逆向',2333,64.82,12.85,
  [('很好',None,11.55,False,False),('较好',11.55,11.96,True,False),('一般',11.96,14.14,True,False),('不足',14.14,None,True,False)]),
 (4,'存在围护安全隐患的住宅数量','围护隐患住宅占比%','占比化','逆向',330,9.17,5.87,
  [('很好',None,5.27,False,False),('较好',5.27,5.88,True,False),('一般',5.88,6.46,True,False),('不足',6.46,None,True,False)]),
 # ⚠️ 自评表序号5「非成套住宅数量」在 2026 版 55 项中**已删**（项目既有记录：按"套"计数口径取消），
 #    yaml 无对应 Indicator_5（yaml 5=管线破损）。故此处**跳过**，自评表6–9 顺移对齐 yaml 5–8。
 (5,'存在管线管道破损的住宅数量','管线破损住宅占比%','占比化','逆向',1349,37.48,6.52,
  [('很好',None,5.85,False,False),('较好',5.85,6.53,True,False),('一般',6.53,7.18,True,False),('不足',7.18,None,True,False)]),
 (6,'需要进行适老化改造的住宅数量','适老化改造住宅占比%','占比化','逆向',2495,69.32,11.12,
  [('很好',None,9.99,False,False),('较好',9.99,11.13,True,False),('一般',11.13,12.24,True,False),('不足',12.24,None,True,False)]),
 (7,'需要进行节能改造的住宅数量','节能改造住宅占比%','占比化','逆向',1012,28.12,2.31,
  [('很好',None,2.96,False,False),('较好',2.96,3.32,True,False),('一般',3.32,3.65,True,False),('不足',3.65,None,True,False)]),
 (8,'需要进行数字化改造的住宅数量','数字化改造住宅占比%','占比化','逆向',1301,36.15,13.71,
  [('很好',None,12.32,False,False),('较好',12.32,13.72,True,False),('一般',13.72,15.09,True,False),('不足',15.09,None,True,False)]),
 (9,'未达标配建养老服务设施的社区数量','养老设施未达标社区占比%','占比化','逆向',391,96.78,20.27,
  [('很好',None,18.23,False,False),('较好',18.23,20.27,True,False),('一般',20.27,22.3,True,False),('不足',22.3,None,True,False)]),
 (10,'未达标配建婴幼儿托育设施的社区数量','托育设施未达标社区占比%','占比化','逆向',404,100,23.04,
  [('很好',None,20.74,False,False),('较好',20.74,23.04,True,False),('一般',23.04,25.34,True,False),('不足',25.34,None,True,False)]),
 # ⚠️ 自评表序号12「小学学位缺口数」2026 版亦已删（yaml 无独立编号，见项目记录"幼儿园12/小学缺口13 不在2026五十五项"），跳过。
 (11,'停车泊位缺口数','每小区停车泊位缺口数','均值化','逆向',58635,145.136,86,
  [('很好',None,77.3,False,False),('较好',77.3,86.2,True,False),('一般',86.2,96.5,True,False),('不足',96.5,None,True,False)]),
 (12,'新能源汽车充电桩缺口数','每小区充电桩缺口数','均值化','逆向',7019,17.3738,9,
  [('很好',None,8,False,False),('较好',8,9,True,False),('一般',9,10,True,False),('不足',10,None,True,False)]),
 (13,'未配建电动自行车充电设施的小区数量','电动车充电未配建小区占比%','占比化','逆向',77,19.06,None,
  [('很好',None,None,False,False),('较好',None,None,False,False),('一般',None,None,False,False),('不足',None,None,False,False)]),
 (14,'未达标配建公共活动场地的社区数量','公共活动场地未达标社区占比%','占比化','逆向',113,27.97,18.34,
  [('很好',None,16.5,False,False),('较好',16.5,18.34,True,False),('一般',18.34,20.17,True,False),('不足',20.17,None,True,False)]),
 (15,'不达标的步行道长度','不达标步行道长度占比% = 不达标长度/区域面积','占比化','逆向',428.77,3.57,3.57,
  [('很好',None,3.21,False,False),('较好',3.21,3.57,True,False),('一般',3.57,3.92,True,False),('不足',3.92,None,True,False)]),
 (16,'未实施生活垃圾分类的小区数量','未垃圾分类小区占比%','占比化','逆向',114,28.22,13.97,
  [('很好',None,12.57,False,False),('较好',12.57,13.97,True,False),('一般',13.97,15.36,True,False),('不足',15.36,None,True,False)]),
 (17,'未实施物业管理的小区数量','未物业管理小区占比%','占比化','逆向',87,21.53,33.49,
  [('很好',None,30.14,False,False),('较好',30.14,33.49,True,False),('一般',33.49,36.83,True,False),('不足',36.83,None,True,False)]),
 (18,'需要进行智慧化改造的小区数量','智慧化改造小区占比%','占比化','逆向',60,14.85,39.93,
  [('很好',None,35.97,False,False),('较好',35.97,39.93,True,False),('一般',39.93,43.92,True,False),('不足',43.92,None,True,False)]),
]
# 地方实操依据（不入库为真名，公开用 URI 代号）
LOCAL_BASIS = 'Policy_样本市自评表2025'


def load_yaml_names():
    import re
    t = YAML.read_text(encoding="utf-8")
    return {int(a): c for a, _b, c in re.findall(r'- seq: (\d+)\s*\n\s*code: "(\d+)"\s*\n\s*name: "([^"]+)"', t)}


def band_of(n):
    return [f'RB_P{n}_很好', f'RB_P{n}_较好', f'RB_P{n}_一般', f'RB_P{n}_不足']


def build():
    seq2name = load_yaml_names()
    g = Graph(); g.bind('ur', UR)
    local = []
    n_rule = n_ref = n_band = n_ratio = n_ar = 0
    for seq, name, ratio_name, method, direction, val, ratio, avg, bands in ROWS:
        yname = seq2name.get(seq, '')
        # 按名不按号：允许措辞微差（如"停车泊位存在较大缺口数的小区数"vs"停车泊位缺口数"），
        # 用关键词片段双向包含断言，既容错又防编号错位。
        key = name[:4]
        assert key in yname or yname[:4] in name, f'编号{seq}错位：yaml={yname!r} 自评表={name!r}'
        ind = UR[f'Indicator_{seq}']
        rule = UR[f'ER_P{seq}']
        ref = UR[f'ERef_P{seq}']
        ratio_u = UR[f'DR_sample_I{seq}']
        ar = UR[f'AR_sample_I{seq}']
        method_u = UR['EvaluationMethod_占比化'] if method == '占比化' else UR['EvaluationMethod_均值化']

        # 规则
        g.add((rule, RDF.type, UR.EvaluationRule))
        g.add((rule, RDFS.label, Literal(f'指标{seq}{name}{method}评价规则【地方实操】', lang='zh')))
        g.add((rule, UR.evaluates, ind))
        g.add((rule, UR.evaluationMethod, method_u))
        g.add((rule, UR.evaluationOutput, UR.EvaluationOutput_四级等级))
        g.add((rule, UR.usesReference, ref))
        n_rule += 1

        # 参考值（地方口径）
        g.add((ref, RDF.type, UR.EvaluationReference))
        g.add((ref, RDFS.label, Literal(f'指标{seq}{name}自评表四档参考【地方实操·待核】', lang='zh')))
        g.add((ref, UR.forIndicator, ind))
        g.add((ref, UR.sourceScope, Literal('样本市自评表2025口径', lang='zh')))
        g.add((ref, UR.appliesToScale, UR.SpatialScale_DistrictScale))  # 2026-11-20 分尺度：自评表=全市总账口径
        g.add((ref, UR.validPeriod, Literal('2025', lang='zh')))
        g.add((ref, UR.direction, Literal(direction, lang='zh')))
        g.add((ref, UR.basedOn, UR[LOCAL_BASIS]))
        if avg is not None:
            g.add((ref, UR.referenceValue, Literal(avg, datatype=XSD.decimal)))
        n_ref += 1

        # 四档（15 项无分界值者只建档名，数值空）
        for (label, lo, hi, ilo, ihi), bu in zip(bands, band_of(seq)):
            b = UR[bu]
            g.add((b, RDF.type, UR.RatingBand))
            g.add((ref, UR.hasRatingBand, b))
            g.add((b, UR.bandLabel, Literal(label, lang='zh')))
            if lo is not None:
                g.add((b, UR.bandLower, Literal(lo, datatype=XSD.decimal)))
            if hi is not None:
                g.add((b, UR.bandUpper, Literal(hi, datatype=XSD.decimal)))
            g.add((b, UR.includeLower, Literal(ilo, datatype=XSD.boolean)))
            g.add((b, UR.includeUpper, Literal(ihi, datatype=XSD.boolean)))
            n_band += 1

        # 派生比值（真值只进本地 CSV，公开 TTL 不写 ratioValue）
        g.add((ratio_u, RDF.type, UR.DerivedRatio))
        g.add((ratio_u, UR.derivedFrom, ar))
        g.add((ratio_u, UR.ratioOf, Literal(ratio_name, lang='zh')))
        if method == '占比化' and seq <= 9:
            g.add((ratio_u, RDFS.comment, Literal(f'分母={DENOM}（楼栋表序号上限，大王2026-11-19拍板）；精确比值见本地对照表', lang='zh')))
        n_ratio += 1

        # 实测值 AR：D1 脱敏——公开只写量级，真值留本地
        g.add((ar, RDF.type, UR.AssessmentResult))
        g.add((ar, UR.ofIndicator, ind))
        g.add((ar, UR.assesses, UR.UD_01))
        g.add((ar, UR.year, Literal('2025', datatype=XSD.gYear)))
        g.add((ar, RDFS.comment, Literal(f'指标值量级：{magnitude(val)}；精确值见本地脱敏对照表（不入库）【地方实操】', lang='zh')))
        n_ar += 1
        local.append([seq, name, val, ratio, avg, ratio_name, DENOM if (method=='占比化' and seq<=9) else ''])
    return g, (n_rule, n_ref, n_band, n_ratio, n_ar), local


def magnitude(v):
    if v is None: return '缺'
    if v >= 10000: return '万级'
    if v >= 1000: return '千级'
    if v >= 100: return '百级'
    if v >= 1: return '量级1-99'
    return '小于1'


def verify(g, tbox):
    G = Graph().parse(str(tbox), format='turtle')
    for s, p, o in g: G.add((s, p, o))
    ok = True
    q = 'PREFIX ur: <'+NS+'> SELECT (COUNT(DISTINCT ?r) AS ?c) WHERE { ?r a ur:EvaluationRule ; ur:evaluates ?i }'
    n = int(list(G.query(q))[0].c)
    print(f'  [规则数] {n} (应{len(ROWS)}) {"OK" if n==len(ROWS) else "FAIL"}'); ok &= n==len(ROWS)
    q = 'PREFIX ur: <'+NS+'> SELECT (COUNT(DISTINCT ?r) AS ?c) WHERE { ?r a ur:DerivedRatio }'
    n = int(list(G.query(q))[0].c)
    print(f'  [派生比值] {n} (应{len(ROWS)}) {"OK" if n==len(ROWS) else "FAIL"}'); ok &= n==len(ROWS)
    # 脱敏：公开TTL不含精确真值
    txt = g.serialize(format='turtle')
    leak = [str(row[5]) for row in ROWS if row[5] >= 100 and str(row[5]) in txt]
    print(f'  [脱敏] 精确真值泄漏 {len(leak)} 处 {"OK" if not leak else "FAIL:"+str(leak[:5])}'); ok &= not leak
    assert magnitude(0)=='小于1' and magnitude(255)=='百级' and magnitude(58635)=='万级'
    print('  [负向测试] OK')
    return ok


def main():
    print('== 生成占比化/均值化评价规则与实测值实例 ==')
    g, counts, local = build()
    g.serialize(destination=str(OUT), format='turtle')
    print(f'  写出 {OUT.name}：规则{counts[0]} 参考值{counts[1]} 档位{counts[2]} 派生{counts[3]} 实测{counts[4]} 三元组{len(g)}')
    with LOCAL_CSV.open('w', encoding='utf-8', newline='') as f:
        import csv
        w=csv.writer(f,lineterminator='\n')
        w.writerow(['序号','指标项','指标值(真)','关联指标值(真)','全国平均值','关联指标口径','分母'])
        w.writerows(local)
    print(f'  写出本地对照 {LOCAL_CSV.name}（不入库，{len(local)}行）')
    print('== 校验 =='); ok=verify(g,TBOX)
    for p in (OUT, LOCAL_CSV):
        n=p.read_bytes().count(b'\r'); print(f'  [CRLF] {p.name}={n}'); ok &= n==0
    print('== 结论 ==', '全部断言通过 ✅' if ok else '存在断言失败 ❌')
    return ok


if __name__ == '__main__':
    main()
