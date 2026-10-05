# -*- coding: utf-8 -*-
"""跨域引用同步：按 C-aa-bb-02 的改名与升版结果，批量更新仍然指向旧文件名或旧版本的引用。

只做三组确定性替换，不触碰其余文字：
  1. 10_节点类型表_v1.csv   -> 10_节点类型表_v2.csv   （节点类型表升级 v2，新增派生落点列）
  2. 10_线索树核心设计_v2.3.md -> 10_线索树核心设计_v2.4.md
  3. 40_局末结算与写入设计_v2.3.md -> 40_局末结算与写入设计_v2.4.md
"""
import io
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", ".."))
DESIGN = os.path.join(ROOT, "Dsh", "Design")

RULES = [
    ("10_节点类型表_v1.csv", "10_节点类型表_v2.csv"),
    ("10_线索树核心设计_v2.3.md", "10_线索树核心设计_v2.4.md"),
    ("40_局末结算与写入设计_v2.3.md", "40_局末结算与写入设计_v2.4.md"),
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
            changed.append((os.path.relpath(path, ROOT), sum(
                text.count(old) for old, _ in RULES)))

for rel, count in changed:
    print("%-72s 替换 %d 处" % (rel, count))
print("共更新 %d 份文档" % len(changed))
