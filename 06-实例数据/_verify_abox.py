import glob
import os
from pathlib import Path
# -*- coding: utf-8 -*-
"""W-C02 验收：合并 TBox + ABox 后跑 pyshacl，并统计实例规模。"""
from rdflib import Graph, Namespace, RDF
from pyshacl import validate

ROOT = str(Path(__file__).resolve().parent.parent) + "/"
UR = Namespace("https://ontology.cset-digital.cn/urban-renewal#")

tbox = Graph().parse(ROOT + "03-本体模型/城市体检-更新本体.ttl", format="turtle")
abox = Graph().parse(ROOT + "06-实例数据/abox/城市体检实例.ttl", format="turtle")
shacl = Graph().parse(ROOT + "03-本体模型/城市体检-更新约束.shacl", format="turtle")

g = Graph()
for t in tbox:
    g.add(t)
for t in abox:
    g.add(t)

print("TBox 三元组:", len(tbox), "| ABox 三元组:", len(abox), "| 合并:", len(g))


def cnt(cls):
    return len(set(g.subjects(RDF.type, UR[cls])))


for c in ["UrbanDistrict", "Neighborhood", "Community", "ResidentialQuarter", "Building",
          "PublicActivityVenue", "IndicatorJudgement", "AssessmentResult"]:
    print(f"  {c}: {cnt(c)}")

c, _, txt = validate(g, shacl_graph=shacl, inference="rdfs")
print("\nCONFORMS:", c)
if not c:
    lines = txt.split("\n")
    print("\n".join(lines[:40]))
