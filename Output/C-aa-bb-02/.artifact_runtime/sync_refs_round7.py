# -*- coding: utf-8 -*-
"""跨域引用同步（第七轮）：本轮升版后的引用替换。"""
import io
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", ".."))
DESIGN = os.path.join(ROOT, "Dsh", "Design")

RULES = [
    ("40_局末结算与写入设计_v2.5.md", "40_局末结算与写入设计_v2.6.md"),
    ("02_术语表_v1.24.md", "02_术语表_v1.25.md"),
    ("01_设计原则与跨系统交互逻辑_v1.21.md", "01_设计原则与跨系统交互逻辑_v1.22.md"),
    ("03_设计决策记录_v1.18.md", "03_设计决策记录_v1.19.md"),
    ("00_系统全景图_v1.22.md", "00_系统全景图_v1.23.md"),
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
