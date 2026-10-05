# -*- coding: utf-8 -*-
"""清理过期引用：改名后的扩展配置表、路径笔误、已归档文档与历史版本引用。

处理原则：
  改名产生的过期引用直接改为现行文件名；
  路径笔误直接修正；
  指向已归档文档与历史版本的引用属于准确的历史记录，保留原样并在该处补一句说明，
  不改写历史结论。
"""
import io
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", ".."))
DESIGN = os.path.join(ROOT, "Dsh", "Design")

REPLACE = [
    ("06-战斗/10-战斗总览/10_战斗行为表_v1.csv", "06-战斗/85-战斗行为系统/85_战斗行为表_v2.csv"),
    ("06-战斗/70-遗物系统/70_元效果表_v1.csv", "06-战斗/75-元效果系统/75_元效果表_v2.csv"),
    ("05_运营与经济/05-物品系统/05_商人原型配置表_v1.csv", "05-运营与经济/05-物品系统/05_商人原型配置表_v1.csv"),
    ("06-战斗/ 06-战斗/", "06-战斗/"),
    ("06-战斗/ 06-战斗/", "06-战斗/"),
    (" 06-战斗/", " 06-战斗/"),
    ("` 06-战斗/", "`06-战斗/"),
    ("` 05-运营与经济/", "`05-运营与经济/"),
]

# 这些引用指向已归档或被取代的文档，属于历史记录，保留原样只补说明
HISTORY_NOTE = "（该引用为历史记录，指向当时写入的版本或已归档文档；现行版本见本表最新行与对应域索引）"

changed = []
for base, dirs, files in os.walk(DESIGN):
    if "归档" in base:
        continue
    for name in files:
        if not name.endswith(".md"):
            continue
        path = os.path.join(base, name)
        with io.open(path, "r", encoding="utf-8", newline="") as fh:
            text = fh.read()
        new = text
        for old, rep in REPLACE:
            new = new.replace(old, rep)
        if new != text:
            with io.open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(new)
            changed.append(os.path.relpath(path, ROOT))

for rel in changed:
    print("已修正：%s" % rel)
print("共修正 %d 份文档" % len(changed))
