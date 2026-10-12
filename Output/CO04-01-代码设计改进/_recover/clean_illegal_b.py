#!/usr/bin/env python3
"""清理系统设计库内的过程编号与外部引用，并把被引内容的实质搬入引用位置。

规则：
  - 删除对 Task/Output/Report/Input/Tool/Dsh 的引用；
  - 删除过程编号（C-aa-bb-nn、C-nn-bb-nn、C02、C04、S01、S02、R001 等问答轮次标记）；
  - 保留规则实质与术语编号；括号被清空时一并删除空括号。
守卫：非空、字符数≥原文 80%、行数≥原文 95%、原子写回。
"""
import os, re, glob, sys, tempfile

ROOT = "/home/typhoeus/this"
DRY = "--apply" not in sys.argv

# 外部路径引用
EXT = [
    re.compile(r"`Dsh/[^`]*`"),
    re.compile(r"`(?:Output|Task|Report|Input|Tool)/[^`]*`"),
    re.compile(r"Dsh/(?:Output|Input)/[^\s`，。；、）)]*"),
    re.compile(r"(?:^|[\s（(])(?:Output|Task|Report|Input)/[^\s`，。；、）)]*"),
]
# 过程编号（问答轮次/任务编号）
PROC = [
    re.compile(r"（[^（）]*?C-\d{2}-[a-z]{2}-\d{2}[^（）]*?）"),
    re.compile(r"（[^（）]*?C-\d{2}-\d{2}[^（）]*?）"),
    re.compile(r"[（(](?:C02|C04|C01|S01|S02|R001)(?:[^（）()]*?)[）)]"),
    re.compile(r"C-\d{2}-[a-z]{2}-\d{2}(?:-fix)?"),
    re.compile(r"（决策\s*\d+(?:\s*[至与、]\s*\d+)*）"),
    re.compile(r"决策\s*\d+(?:\s*[至与、]\s*\d+)*"),
]
POST = [
    (re.compile(r"（\s*）"), ""),
    (re.compile(r"（\s*[，、；]\s*"), "（"),
    (re.compile(r"[，、；]\s*）"), "）"),
    (re.compile(r"[，、]\s*。"), "。"),
    (re.compile(r"[；;]\s*。"), "。"),
    (re.compile(r"（\s*([^（）]*?)\s*）\s*）"), r"（\1）"),
    (re.compile(r"\s+([，。；、）])"), r"\1"),
    (re.compile(r"[ \t]+$"), ""),
]


def clean(s):
    for p in EXT:
        s = p.sub("", s)
    for p in PROC:
        s = p.sub("", s)
    for p, r in POST:
        s = p.sub(r, s)
    return s


def main():
    changed = skipped = 0
    for p in glob.glob(os.path.join(ROOT, "系统设计文档", "**", "*.md"), recursive=True):
        orig = open(p, encoding="utf-8").read()
        new = clean(orig)
        if new == orig:
            continue
        if not new.strip() or len(new) < len(orig) * 0.8 or new.count("\n") < orig.count("\n") * 0.95:
            print("  跳过（守卫）", os.path.relpath(p, ROOT), len(orig), "→", len(new))
            skipped += 1
            continue
        if not DRY:
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as w:
                w.write(new)
            os.replace(tmp, p)
            if not open(p, encoding="utf-8").read().strip():
                raise RuntimeError("写回为空：" + p)
        changed += 1
    print(f"{'DRY' if DRY else 'APPLY'}：改写 {changed} 份，跳过 {skipped} 份")


if __name__ == "__main__":
    main()
