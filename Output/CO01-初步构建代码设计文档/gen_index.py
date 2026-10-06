#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CO01：从已落盘的代码设计案生成 Code_Design/README.md 的索引表与状态统计。

用法：
    python3 gen_index.py [--root /home/ob-alive/策划书] [--out 索引片段路径]
"""

import argparse
import os
import re
import sys

# 相对 Code_Design/ 的路径 → (单元码, 类型, 主模块, 层级, 批次)
UNITS = {
    "00-架构单元/M01_核心与基础设施代码设计案.md": ("M01", "架构单元", "M01", "L1、L2", 1),
    "01-通用系统/50_存档与持久化代码设计案.md": ("SAVE", "设计库系统", "M01", "L1、L2", 1),
    "01-通用系统/60_设置与辅助功能代码设计案.md": ("OPTION", "设计库系统", "M01", "L1、L5", 1),
    "00-架构单元/M09_全局能力代码设计案.md": ("M09", "架构单元", "M09", "L3", 1),
    "06-战斗/75_元效果系统代码设计案.md": ("EFFECT", "设计库系统", "M09", "L3", 1),
    "00-架构单元/M04_对象与经济代码设计案.md": ("M04", "架构单元", "M04", "L3、L4", 2),
    "05-运营与经济/05_物品系统代码设计案.md": ("ITEM", "设计库系统", "M04", "L3、L4", 2),
    "05-运营与经济/10_金钱与货物代码设计案.md": ("TRADE", "设计库系统", "M04", "L3", 2),
    "05-运营与经济/20_委托系统代码设计案.md": ("QUEST", "设计库系统", "M04", "L3", 2),
    "05-运营与经济/30_背包系统代码设计案.md": ("INVENTORY", "设计库系统", "M04", "L3、L5", 2),
    "05-运营与经济/40_仓库与银行代码设计案.md": ("STORAGE", "设计库系统", "M04", "未分配（远期）", 2),
    "06-战斗/60_装备系统代码设计案.md": ("EQUIP", "设计库系统", "M04", "L3", 2),
    "06-战斗/70_遗物系统代码设计案.md": ("RELIC", "设计库系统", "M04", "L3", 2),
    "00-架构单元/M07_队伍与角色代码设计案.md": ("M07", "架构单元", "M07", "L3", 3),
    "01-通用系统/40_角色与小队代码设计案.md": ("PARTY", "设计库系统", "M07", "L3", 3),
    "00-架构单元/M02_事件与生成代码设计案.md": ("M02", "架构单元", "M02", "L3、L4", 4),
    "02-时间与事件/10_时间机制代码设计案.md": ("TIME", "设计库系统", "M02", "L1、L3", 4),
    "02-时间与事件/20_日程系统代码设计案.md": ("SCHEDULE", "设计库系统", "M02", "L3、L5", 4),
    "02-时间与事件/30_事件系统代码设计案.md": ("EVENT", "设计库系统", "M02", "L3、L4", 4),
    "02-时间与事件/30-10_触发条件代码设计案.md": ("CONDITION", "设计库子系统", "M02", "L3", 4),
    "09-局生成/20_局生成与种子代码设计案.md": ("GENERATE", "设计库系统", "M02", "L3", 4),
    "00-架构单元/M03_探索与推进代码设计案.md": ("M03", "架构单元", "M03", "L3、L5", 5),
    "01-通用系统/10_区域与位移代码设计案.md": ("AREA", "设计库系统", "M03", "L3", 5),
    "02-时间与事件/40_探索系统代码设计案.md": ("EXPLORE", "设计库系统", "M03", "L3", 5),
    "00-架构单元/M05_战斗代码设计案.md": ("M05", "架构单元", "M05", "L3、L4", 6),
    "06-战斗/10_战斗总览代码设计案.md": ("BATTLE", "设计库系统", "M05", "L3、L5", 6),
    "06-战斗/20_时间轴与行动顺序代码设计案.md": ("TIMELINE", "设计库系统", "M05", "L3", 6),
    "06-战斗/30_战场与战棋规则代码设计案.md": ("FIELD", "设计库系统", "M05", "L3、L5", 6),
    "06-战斗/40_技能系统代码设计案.md": ("SKILL", "设计库系统", "M05", "L3", 6),
    "06-战斗/50_行动槽与连携代码设计案.md": ("ACTIONSLOT", "设计库系统", "M05", "L3", 6),
    "06-战斗/80_技能与库存联动代码设计案.md": ("SKILLITEM", "设计库系统", "M05", "L3", 6),
    "06-战斗/85_战斗行为系统代码设计案.md": ("BATTLEACT", "设计库系统", "M05", "L3", 6),
    "06-战斗/90_敌人与AI代码设计案.md": ("ENEMY", "设计库系统", "M05", "L3", 6),
    "06-战斗/A0_战斗目标与结果代码设计案.md": ("BATTLEGOAL", "设计库系统", "M05", "L3、L4", 6),
    "00-架构单元/M06_元进度与结算代码设计案.md": ("M06", "架构单元", "M06", "L3、L4", 7),
    "07-线索树与元进度/10_线索树核心代码设计案.md": ("CLUETREE", "设计库系统", "M06", "L3、L4", 7),
    "07-线索树与元进度/20_剪枝系统代码设计案.md": ("PRUNE", "设计库系统", "M06", "L3", 7),
    "07-线索树与元进度/30_概率池联动代码设计案.md": ("POOL", "设计库系统", "M06", "L3", 7),
    "07-线索树与元进度/40_局末结算与写入代码设计案.md": ("SETTLE", "设计库系统", "M06", "L4", 7),
    "00-架构单元/M08_界面与信息代码设计案.md": ("M08", "架构单元", "M08", "L5", 8),
    "01-通用系统/20_信息传递系统代码设计案.md": ("INFO", "设计库系统", "M08", "L5", 8),
    "00-架构单元/M10_流程编排代码设计案.md": ("M10", "架构单元", "M10", "L4", 9),
}

BATCH_NAMES = {
    1: "批次一 基础设施与公共能力",
    2: "批次二 对象与经济",
    3: "批次三 队伍与角色",
    4: "批次四 时间与事件",
    5: "批次五 地图与探索",
    6: "批次六 战斗",
    7: "批次七 元进度与结算",
    8: "批次八 界面与信息",
    9: "批次九 流程编排",
}

META_RE = {
    "name": re.compile(r"\|\s*系统名\s*\|\s*([^|\n]+?)\s*\|"),
    "domain": re.compile(r"\|\s*所属域\s*\|\s*([^|\n]+?)\s*\|"),
    "number": re.compile(r"\|\s*系统编号\s*\|\s*([^|\n]+?)\s*\|"),
    "upstream": re.compile(r"\|\s*对应设计文档\s*\|\s*([^|\n]+?)\s*\|"),
    "status": re.compile(r"\|\s*状态\s*\|\s*([^|\n]+?)\s*\|"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/home/ob-alive/策划书")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    base = os.path.join(args.root, "Code_Design")
    rows, missing, status_count, line_info = [], [], {}, []
    for relpath, (code, kind, module, layer, batch) in sorted(UNITS.items(), key=lambda kv: (kv[1][4], kv[0])):
        path = os.path.join(base, relpath)
        if not os.path.exists(path):
            missing.append(relpath)
            continue
        text = open(path, encoding="utf-8").read()
        meta = {}
        for key, rx in META_RE.items():
            m = rx.search(text)
            meta[key] = m.group(1).replace("`", "").strip() if m else "?"
        status = meta["status"]
        status_count[status] = status_count.get(status, 0) + 1
        lines = len(text.splitlines())
        rows.append((batch, "| %s %s | %s | %s | %s | `%s` | %s | %s |" % (
            meta["number"], meta["name"], kind, module, layer, relpath, meta["upstream"], status)))
        line_info.append((relpath, lines))

    # 按批次分段输出：每批一张七列表（列与 NR-06 §十二.7 登记的一致，行数只用于控制台核对）
    out = []
    last_batch = None
    for batch, row in rows:
        if batch != last_batch:
            if last_batch is not None:
                out.append("")
            out.append("#### %s" % BATCH_NAMES[batch])
            out.append("")
            out.append("| 单元 | 类型 | 主模块 | 层级 | 代码设计案 | 对应设计文档 | 状态 |")
            out.append("| --- | --- | --- | --- | --- | --- | --- |")
            last_batch = batch
        out.append(row)
    table = "\n".join(out)

    print(table)
    print()
    print("已落盘 %d / %d 份；状态分布：%s" % (len(rows), len(UNITS), "、".join("%s %d" % kv for kv in sorted(status_count.items()))))
    print("行数明细：" + "、".join("%s %d" % (p.split("/")[-1][:14], n) for p, n in line_info))
    if missing:
        print("未落盘 %d 份：" % len(missing))
        for m in missing:
            print("  " + m)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(table + "\n")
        print("索引片段已写入 %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
