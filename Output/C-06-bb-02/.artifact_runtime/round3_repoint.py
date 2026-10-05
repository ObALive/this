# -*- coding: utf-8 -*-
"""第三轮：把全库对已重命名文档的引用改指到新文件名。

重命名映射：
  06_战斗索引_v3.md            -> 06_战斗索引_v3.1.md
  10_战斗总览设计_v3.md         -> 10_战斗总览设计_v4.md
  40_技能系统设计_v3.md         -> 40_技能系统设计_v4.md
  60_装备系统设计_v5.md         -> 60_装备系统设计_v6.md
  80_技能与库存联动设计_v4.md    -> 80_技能与库存联动设计_v5.md
  90_敌人与AI设计_v3.md        -> 90_敌人与AI设计_v4.md
  05_运营与经济索引_v2.md       -> 05_运营与经济索引_v2.2.md
"""
import io
import os
import re

TARGETS = [
    (r"D:\myspace\Git\mygame\Dsh\Design", "Design"),
    (r"D:\myspace\Git\mygame\Dsh\Output", "Output"),
]

REPL = [
    ("06_战斗索引_v3.md", "06_战斗索引_v3.1.md"),
    ("10_战斗总览设计_v3.md", "10_战斗总览设计_v4.md"),
    ("40_技能系统设计_v3.md", "40_技能系统设计_v4.md"),
    ("60_装备系统设计_v5.md", "60_装备系统设计_v6.md"),
    ("80_技能与库存联动设计_v4.md", "80_技能与库存联动设计_v5.md"),
    ("90_敌人与AI设计_v3.md", "90_敌人与AI设计_v4.md"),
    ("05_运营与经济索引_v2.md", "05_运营与经济索引_v2.2.md"),
]

# 不改动归档目录与历史版本文件
SKIP_DIR = {"归档", ".git", "node_modules"}
HIST = re.compile(r"_v[1-9](\.[0-9])?\.(md|csv)$")


def main():
    changed = []
    for base, label in TARGETS:
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in SKIP_DIR]
            for name in files:
                if not name.endswith((".md", ".csv")):
                    continue
                path = os.path.join(root, name)
                try:
                    t = io.open(path, encoding="utf-8").read()
                except (UnicodeDecodeError, OSError):
                    continue
                original = t
                for old, new in REPL:
                    if old in t:
                        t = t.replace(old, new)
                if t != original:
                    io.open(path, "w", encoding="utf-8", newline="\n").write(t)
                    changed.append(os.path.relpath(path, base))
    print("改指文件数:", len(changed))
    for c in sorted(changed):
        print("  ", c)


if __name__ == "__main__":
    main()
