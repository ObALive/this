# -*- coding: utf-8 -*-
"""第四轮：改指重命名后的文档、补装备系统变更记录、更新 05 索引标题版本。"""
import io
import os
import re

DESIGN = r"D:\myspace\Git\mygame\Dsh\Design"
OUTPUT = r"D:\myspace\Git\mygame\Dsh\Output"

REPL = [
    ("05_运营与经济索引_v2.2.md", "05_运营与经济索引_v2.3.md"),
    ("60_装备系统设计_v6.md", "60_装备系统设计_v7.md"),
    ("80_技能与库存联动设计_v5.md", "80_技能与库存联动设计_v6.md"),
]

SKIP_DIR = {"归档", ".git", "node_modules"}


def repoint(base):
    changed = 0
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
                changed += 1
    return changed


def main():
    print("Design 改指文件数:", repoint(DESIGN))
    print("Output 改指文件数:", repoint(OUTPUT))

    # 装备系统：头部版本与变更记录补齐
    p = os.path.join(DESIGN, "06-战斗", "60-装备系统", "60_装备系统设计_v7.md")
    t = io.open(p, encoding="utf-8").read()
    t = t.replace("| 版本 | v6 |", "| 版本 | v7 |", 1)
    anchor = "| v6 | 2026-09-25 | 法术书条款落到容器允许内容约束，书页装入取出使用容器界面常规操作；补充投掷组件对法术书可投掷性的判定 | C-06-bb-02（第三轮） |"
    if anchor in t and "| v7 |" not in t:
        t = t.replace(anchor, anchor + "\n| v7 | 2026-09-25 | 法术书的允许内容约束改按符文书页词条匹配，与词条体系统一 | C-06-bb-02（第四轮） |", 1)
    io.open(p, "w", encoding="utf-8", newline="\n").write(t)
    print("装备系统：版本与变更记录已补齐")

    # 技能与库存联动：变更记录补齐（文件名 v6，内部已为 v6）
    p = os.path.join(DESIGN, "06-战斗", "80-技能与库存联动", "80_技能与库存联动设计_v6.md")
    t = io.open(p, encoding="utf-8").read()
    head = re.search(r"^\| 版本 \| (v[\d.]+) \|", t, re.M)
    rows = re.findall(r"^\| (v[\d.]+) \| \d{4}-\d{2}-\d{2} \|", t, re.M)
    print("技能与库存联动 头部=%s 变更记录最新=%s" % (head.group(1) if head else "-",
                                                    rows[-1] if rows else "?"))

    # 05 索引标题版本
    p = os.path.join(DESIGN, "05-运营与经济", "05_运营与经济索引_v2.3.md")
    t = io.open(p, encoding="utf-8").read()
    t = t.replace("# 05 运营与经济域 · 索引（v2.2）", "# 05 运营与经济域 · 索引（v2.3）", 1)
    io.open(p, "w", encoding="utf-8", newline="\n").write(t)
    print("05 索引标题版本已更新")

    # 数值模型版本升 v1.8（变更记录已在第四轮脚本中加入）
    p = os.path.join(DESIGN, "09-数值与配置", "10-数值模型", "10_数值模型设计_v1.md")
    t = io.open(p, encoding="utf-8").read()
    t = t.replace("| 版本 | v1.7 |", "| 版本 | v1.8 |", 1)
    io.open(p, "w", encoding="utf-8", newline="\n").write(t)
    print("数值模型版本升 v1.8")


if __name__ == "__main__":
    main()
