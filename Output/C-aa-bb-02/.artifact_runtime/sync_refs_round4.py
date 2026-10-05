# -*- coding: utf-8 -*-
"""跨域引用同步（第四轮）：索引与总览文档升版后的引用替换。"""
import io
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", ".."))
DESIGN = os.path.join(ROOT, "Dsh", "Design")

RULES = [
    ("01_设计原则与跨系统交互逻辑_v1.19.md", "01_设计原则与跨系统交互逻辑_v1.20.md"),
    ("02_术语表_v1.22.md", "02_术语表_v1.23.md"),
    ("03_设计决策记录_v1.16.md", "03_设计决策记录_v1.17.md"),
    ("00_系统全景图_v1.20.md", "00_系统全景图_v1.21.md"),
    ("01_通用系统索引_v1.14.md", "01_通用系统索引_v1.15.md"),
    ("02_时间与事件索引_v1.11.md", "02_时间与事件索引_v1.12.md"),
    ("05_运营与经济索引_v2.5.md", "05_运营与经济索引_v2.6.md"),
    ("06_战斗索引_v3.2.md", "06_战斗索引_v3.3.md"),
    ("07_线索树与元进度索引_v1.6.md", "07_线索树与元进度索引_v1.7.md"),
    ("10_金钱与货物设计_v4.1.md", "10_金钱与货物设计_v4.2.md"),
    ("20_委托系统设计_v2.2.md", "20_委托系统设计_v2.3.md"),
    ("30_背包系统设计_v3.1.md", "30_背包系统设计_v3.2.md"),
    ("60_设置与辅助功能设计_v1.4.md", "60_设置与辅助功能设计_v1.5.md"),
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
