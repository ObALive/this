# -*- coding: utf-8 -*-
"""跨域引用同步（第三轮）：本轮升版与改名的正文引用替换。"""
import io
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", ".."))
DESIGN = os.path.join(ROOT, "Dsh", "Design")

RULES = [
    ("05_物品系统设计_v6.md", "05_物品系统设计_v7.md"),
    ("80_技能与库存联动设计_v6.1.md", "80_技能与库存联动设计_v6.2.md"),
    ("50_存档与持久化设计_v4.2.md", "50_存档与持久化设计_v4.3.md"),
    ("40_角色与小队设计_v1.2.md", "40_角色与小队设计_v1.3.md"),
    ("07_线索树与元进度索引_v1.6.md", "07_线索树与元进度索引_v1.7.md"),
    ("10_线索树核心设计_v2.4.md", "10_线索树核心设计_v2.4.md"),
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
