# -*- coding: utf-8 -*-
"""跨域引用同步（第二轮）：三份正文升级版本号后的引用替换。"""
import io
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", ".."))
DESIGN = os.path.join(ROOT, "Dsh", "Design")

RULES = [
    ("30_事件系统设计_v4.2.md", "30_事件系统设计_v4.3.md"),
    ("40_技能系统设计_v4.1.md", "40_技能系统设计_v4.2.md"),
    ("60_装备系统设计_v7.1.md", "60_装备系统设计_v7.2.md"),
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
