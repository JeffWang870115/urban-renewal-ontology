# -*- coding: utf-8 -*-
"""2026-10-10 校验：belongsToDimension / orientation / 三产物一致性。"""
from pathlib import Path
import os
from rdflib import Graph, Namespace
from pyshacl import validate
import yaml

BASE = str(Path(__file__).resolve().parent.parent)
M = os.path.join(BASE, "03-本体模型")
UR = Namespace("https://ontology.cset-digital.cn/urban-renewal#")

print("== yaml ==")
d = yaml.safe_load(open(os.path.join(BASE, "04-指标映射", "55项指标.yaml"), encoding="utf-8"))
print("indicators:", len(d["indicators"]), "| categories:", len(d["categories"]))
for c in d["categories"]:
    print("  ", c["name"], "->", c.get("dimensions"), "| seqs", c["seqs"])

print("== ttl ==")
g = Graph().parse(os.path.join(M, "城市体检-更新本体.ttl"), format="turtle")
print("triples:", len(g))
btd = list(g.subject_objects(UR.belongsToDimension))
print("belongsToDimension 三元组:", len(btd))
from collections import defaultdict
mp = defaultdict(list)
for s, o in btd:
    mp[str(s).split("#")[-1]].append(str(o).split("#")[-1])
print("分类→维度:", dict(mp))
ori = [s for s in g.subjects(UR.orientation, None)]
print("带 orientation 的指标数:", len(ori))

print("== pyshacl ==")
sg = Graph().parse(os.path.join(M, "城市体检-更新约束.shacl"), format="turtle")
print("shacl triples:", len(sg))
conforms, _, txt = validate(g, shacl_graph=sg, inference="rdfs")
print("CONFORMS:", conforms)

print("== 负向测试：删掉「设施完善」的 belongsToDimension -> 应违反 S5b ==")
g2 = Graph()
for t in g:
    g2.add(t)
g2.remove((UR["设施完善"], UR.belongsToDimension, None))
c2, _, _ = validate(g2, shacl_graph=sg, inference="rdfs")
print("CONFORMS(should be False):", c2)
