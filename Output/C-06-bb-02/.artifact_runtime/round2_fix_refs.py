# -*- coding: utf-8 -*-
"""第二轮：修正残留引用、删除被 v3 取代的 v2 中间文件、重写战斗索引 v3。"""
import io
import os

COMBAT = r"D:\myspace\Git\mygame\Dsh\Design\06-战斗"

FIXES = [
    ("90-敌人与AI/90_敌人与AI设计_v3.md",
     "A0-战斗目标与结果/A0_战斗目标与结果设计_v2.md",
     "A0-战斗目标与结果/A0_战斗目标与结果设计_v3.md"),
    ("A0-战斗目标与结果/A0_战斗目标与结果设计_v3.md",
     "10-战斗总览/10_战斗行为表_v1.csv",
     "85-战斗行为系统/85_战斗行为表_v2.csv"),
    ("70-遗物系统/70_遗物系统设计_v4.md",
     "70_元效果表_v1.csv", "75_元效果表_v2.csv"),
    ("10-战斗总览/10_战斗总览设计_v3.md",
     "10-战斗总览/10_战斗行为表_v1.csv", "85-战斗行为系统/85_战斗行为表_v2.csv"),
]

# 被 v3 取代的中间文件（本任务本轮生成，非历史归档）
DROP = [
    "10-战斗总览/10_战斗总览设计_v2.md",
    "20-时间轴与行动顺序/20_时间轴与行动顺序设计_v2.md",
    "30-战场与战棋规则/30_战场与战棋规则设计_v2.md",
    "40-技能系统/40_技能系统设计_v2.md",
    "50-行动槽与连携/50_行动槽与连携设计_v2.md",
    "80-技能与库存联动/80_技能与库存联动设计_v2.md",
    "90-敌人与AI/90_敌人与AI设计_v2.md",
    "A0-战斗目标与结果/A0_战斗目标与结果设计_v2.md",
    "06_战斗索引_v2.md",
]


def main():
    for rel, old, new in FIXES:
        path = os.path.join(COMBAT, rel.replace("/", os.sep))
        if not os.path.isfile(path):
            print("跳过:", rel)
            continue
        text = io.open(path, encoding="utf-8").read()
        if old not in text:
            print("未命中:", rel, "|", old)
            continue
        io.open(path, "w", encoding="utf-8", newline="\n").write(text.replace(old, new))
        print("已修正:", rel, "->", new.split("/")[-1])

    for rel in DROP:
        path = os.path.join(COMBAT, rel.replace("/", os.sep))
        if os.path.isfile(path):
            os.remove(path)
            print("已移除被取代的中间版本:", rel)


if __name__ == "__main__":
    main()
