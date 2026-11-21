# -*- coding: utf-8 -*-
"""把根目录里 0 字节的命令行事故产物移入备份区（只移不删，附映射清单）。"""
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "_bak_20261108c" / "根目录脏文件"
DEST.mkdir(parents=True, exist_ok=True)

junk = [f for f in os.listdir(ROOT)
        if (ROOT / f).is_file() and not f.startswith(".")
        and (ROOT / f).stat().st_size == 0]

lines = ["# 原→新 映射清单（2026-11-08，只移不删）", "",
         "> 均为 0 字节空文件，由早前命令行转义事故产生；移入已 ignore 的备份区，可原样回滚。", ""]
for f in junk:
    shutil.move(str(ROOT / f), str(DEST / f))
    lines.append("- `%s` → `_bak_20261108c/根目录脏文件/%s`" % (f, f))
(DEST / "映射清单.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("MOVED", len(junk), "files")
for f in junk:
    print("  ", repr(f))
