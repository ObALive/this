# -*- coding: utf-8 -*-
"""跨域引用同步（第六轮）：本轮索引与总览升版后的引用替换。"""
import io
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", ".."))
DESIGN = os.path.join(ROOT, "Dsh", "Design")

RULES = [
    ("01_通用系统索引_v1.15.md", "01_通用系统索引_v1.16.md"),
    ("02_时间与事件索引_v1.12.md", "02_时间与事件索引_v1.13.md"),
    ("06_战斗索引_v3.3.md", "06_战斗索引_v3.4.md"),
    ("07_线索树与元进度索引_v1.7.md", "07_线索树与元进度索引_v1.8.md"),
]

changed = []
for base, _dirs, files in os.walk(DESIGN):
    for name in files:
        if not name.endswith(".md"):
            continue
        path = os.path.join(base, name)
        with io.open(path, "r", encoding="utf-8", newline="") as fh:
            text = fh.read()
        new = text
        for old, rep in RULES:
            new = new.replace(old, rep)
        if new != text:
            with io.open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(new)
            changed.append((os.path.relpath(path, ROOT),
                            sum(text.count(old) for old, _ in RULES)))

for rel, count in changed:
    print("%s 替换 %d 处" % (rel, count))
print("共更新 %d 份文档" % len(changed))
