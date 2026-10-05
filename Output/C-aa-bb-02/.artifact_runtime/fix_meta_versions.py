# -*- coding: utf-8 -*-
"""修正五份正文的元信息版本号，使其与文件名版本号一致。"""
import io
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", ".."))
DESIGN = os.path.join(ROOT, "Dsh", "Design")

TARGETS = {
    "05-运营与经济/10-金钱与货物/10_金钱与货物设计_v4.2.md": ("v4.1", "v4.2"),
    "05-运营与经济/20-委托系统/20_委托系统设计_v2.3.md": ("v2.2", "v2.3"),
    "05-运营与经济/30-背包系统/30_背包系统设计_v3.2.md": ("v3.1", "v3.2"),
    "06-战斗/40-技能系统/40_技能系统设计_v4.2.md": ("v4.1", "v4.2"),
    "06-战斗/60-装备系统/60_装备系统设计_v7.2.md": ("v7.1", "v7.2"),
    "07-线索树与元进度/10-线索树核心/10_线索树核心设计_v2.4.md": ("v2.3", "v2.4"),
}

for rel, (old, new) in TARGETS.items():
    path = os.path.join(DESIGN, rel.replace("/", os.sep))
    with io.open(path, "r", encoding="utf-8", newline="") as fh:
        text = fh.read()
    original = text
    text = text.replace("| 版本 | %s |" % old, "| 版本 | %s |" % new, 1)
    head_old = "（%s）\n" % old
    if text.startswith("# ") and head_old in text.split("\n")[0] + "\n":
        first, rest = text.split("\n", 1)
        text = first.replace(head_old.strip(), "（%s）" % new) + "\n" + rest
    if text != original:
        with io.open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        print("已修正：%s（%s -> %s）" % (rel, old, new))
    else:
        print("未变更：%s" % rel)
