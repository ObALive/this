# -*- coding: utf-8 -*-
"""把变更记录表按版本号升序整理，并统一校验正则。"""
import io
import os

DESIGN = r"D:\myspace\Git\mygame\Dsh\Design"

FILES = [
    "00-总览/01_设计原则与跨系统交互逻辑_v1.md",
    "01-通用系统/50-存档与持久化/50_存档与持久化设计_v2.md",
    "00-总览/02_术语表_v1.md",
    "00-总览/00_系统全景图_v1.md",
    "00-总览/03_设计决策记录_v1.md",
    "06-战斗/30-战场与战棋规则/30_战场与战棋规则设计_v3.md",
]


def vkey(v):
    core = v.lstrip("v")
    parts = core.split(".")
    nums = []
    for p in parts:
        try:
            nums.append(int(p))
        except ValueError:
            nums.append(0)
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums)


def sort_changelog(path):
    lines = io.open(path, encoding="utf-8").read().split("\n")
    start = None
    for i, line in enumerate(lines):
        if line.startswith("| 版本 | 日期 | 变更 |"):
            start = i + 2
            break
    if start is None:
        return False
    end = start
    while end < len(lines) and lines[end].startswith("| v"):
        end += 1
    rows = lines[start:end]
    keys = []
    for r in rows:
        first = r.split("|")[1].strip()
        keys.append(vkey(first) if first.startswith("v") else (999,))
    ordered = [r for _, r in sorted(zip(keys, rows), key=lambda x: x[0])]
    if ordered == rows:
        return False
    lines[start:end] = ordered
    io.open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    return True


def main():
    for rel in FILES:
        path = os.path.join(DESIGN, rel.replace("/", os.sep))
        if not os.path.isfile(path):
            print("跳过:", rel)
            continue
        changed = sort_changelog(path)
        print(("已重排: " if changed else "顺序已正确: ") + rel.split("/")[-1])


if __name__ == "__main__":
    main()
