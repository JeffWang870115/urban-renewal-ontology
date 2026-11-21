# -*- coding: utf-8 -*-
"""把本地探查脚本里硬编码的绝对路径改为动态定位，消除入库目录中的真实地名。"""
import re
from pathlib import Path
import glob

D = Path(__file__).resolve().parent
SELF = Path(__file__).name

BLOCK = '''def _locate_src():
    _root = Path(__file__).resolve().parent.parent
    _h = sorted(glob.glob(str(_root / "01-资料" / "**" / "楼栋数据汇总表.xlsx"), recursive=True))
    return Path(_h[0]).parent if _h else (_root / "01-资料")
B = str(_locate_src())'''

pat_b = re.compile(r'^B = r"[A-Z]:/[^"]*"\s*$', re.M)
pat_root = re.compile(r'^ROOT = r"[A-Z]:/[^"]*"\s*$', re.M)

for p in sorted(D.glob("*.py")):
    if p.name == SELF:
        continue
    t = p.read_text(encoding="utf-8")
    if not pat_b.search(t) and not pat_root.search(t):
        continue
    if "import glob" not in t:
        t = "import glob\nimport os\nfrom pathlib import Path\n" + t
    elif "from pathlib import Path" not in t:
        t = "from pathlib import Path\n" + t
    t = pat_b.sub(BLOCK, t)
    t = pat_root.sub('ROOT = str(Path(__file__).resolve().parent.parent) + "/"', t)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(t)
    print("FIXED", p.name)
