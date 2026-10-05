# -*- coding: utf-8 -*-
"""第三轮：修正术语表与技能系统中指向旧位置的配置表引用。"""
import io
import os

DESIGN = r"D:\myspace\Git\mygame\Dsh\Design"

JOBS = [
    ("00-总览/02_术语表_v1.md",
     "| 元效果表 | 元效果的权威登记清单，位于 `06-战斗/70-遗物系统/70_元效果表_v1.csv`，登记效果类别、作用对象、叠加规则与来源组件等 | C-06-bb-02 回答 24 |",
     "| 元效果表 | 元效果的权威登记清单，位于 `06-战斗/75-元效果系统/75_元效果表_v2.csv`，登记效果类别、作用对象、叠加规则与来源组件等 | C-06-bb-02 回答 24 |"),
    ("00-总览/02_术语表_v1.md",
     "| 战斗行为 | 战斗过程中玩家可控角色可以执行的行为；权威清单登记在 `06-战斗/10-战斗总览/10_战斗行为表_v1.csv` | C-06-bb-02 回答 42 |",
     "| 战斗行为 | 战斗过程中玩家可控角色可以执行的行为；权威清单登记在 `06-战斗/85-战斗行为系统/85_战斗行为表_v2.csv` | C-06-bb-02 回答 42 |"),
    ("06-战斗/40-技能系统/40_技能系统设计_v4.md",
     "`06-战斗/80-技能与库存联动/80_技能与库存联动设计_v3.md`",
     "`06-战斗/80-技能与库存联动/80_技能与库存联动设计_v5.md`"),
    ("05-运营与经济/30-背包系统/30_背包系统设计_v2.md",
     "`06-战斗/60-装备系统/60_装备系统设计_v4.md`",
     "`06-战斗/60-装备系统/60_装备系统设计_v6.md`"),
    ("05-运营与经济/05-物品系统/05_物品系统设计_v1.md",
     "`06-战斗/10-战斗总览/10_战斗行为表_v1.csv`",
     "`06-战斗/85-战斗行为系统/85_战斗行为表_v2.csv`"),
    # README 进度行属于历史记录，保留原文；其配置表清单行单独确认
]


def main():
    for rel, old, new in JOBS:
        path = os.path.join(DESIGN, rel.replace("/", os.sep))
        t = io.open(path, encoding="utf-8").read()
        if old not in t:
            print("未命中:", os.path.basename(rel), "|", old[:40])
            continue
        io.open(path, "w", encoding="utf-8", newline="\n").write(t.replace(old, new))
        print("已修正:", os.path.basename(rel))

    # 术语表版本不变，变更记录补一行说明
    p = os.path.join(DESIGN, "00-总览", "02_术语表_v1.md")
    t = io.open(p, encoding="utf-8").read()
    anchor = "| v1.16 | 2026-09-25 | 新增允许内容约束、投掷组件、投掷组件表三项术语 | C-06-bb-02（第三轮） |"
    if anchor in t:
        t = t.replace(anchor, anchor + "\n| v1.16.1 | 2026-09-25 | 元效果表与战斗行为表的路径更新为迁移后的新位置 | C-06-bb-02（第三轮） |", 1)
        t = t.replace("| 版本 | v1.16 |", "| 版本 | v1.16.1 |", 1)
        io.open(p, "w", encoding="utf-8", newline="\n").write(t)
        print("术语表：版本升至 v1.16.1")


if __name__ == "__main__":
    main()
