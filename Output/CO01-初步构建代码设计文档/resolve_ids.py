#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CO01：回填「{名称}（{单元码}，ID 待补）」形式的跨单元引用。

做法：
  1 扫描全部代码设计案，建立「单元码 → 对象名 → ID」索引（ID 与名称的相邻出现）；
  2 扫描全部「{名称}（{单元码}，ID 待补）」引用；
  3 按名称在目标单元内匹配，给出回填建议；匹配不到时列出人工处理清单。

用法：
    python3 resolve_ids.py [--root ...] [--apply] [--report 路径]
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict

PENDING_RE = re.compile(r"([^\s|（），、:：]{2,24})（([A-Z0-9\-]+)，ID 待补）")
ID_NEAR_NAME = re.compile(r"\b((?:SYS|CLS|API)-[A-Z0-9]+-\d{3})\b[\s`|]*([^\s|`（），、:：]{2,24})")
HEAD_ID_NAME = re.compile(r"^#{3,5}\s*((?:SYS|CLS|API)-[A-Z0-9]+-\d{3})\s*(.+?)\s*$", re.M)
TABLE_ID_NAME = re.compile(r"^\|\s*((?:SYS|CLS|API)-[A-Z0-9]+-\d{3})\s*\|\s*([^|]+?)\s*\|", re.M)
TICK_ID_NAME = re.compile(r"`((?:SYS|CLS|API)-[A-Z0-9]+-\d{3})`\s*([^\s`（），、:：]{2,24})")



UNIT_ALIAS = {
    "01-10": "AREA", "01-20": "INFO", "01-40": "PARTY", "01-50": "SAVE", "01-60": "OPTION",
    "02-10": "TIME", "02-20": "SCHEDULE", "02-30": "EVENT", "02-30-10": "CONDITION", "30-10": "CONDITION", "02-40": "EXPLORE",
    "05-05": "ITEM", "05-10": "TRADE", "05-20": "QUEST", "05-30": "INVENTORY", "05-40": "STORAGE",
    "06-10": "BATTLE", "06-20": "TIMELINE", "06-30": "FIELD", "06-40": "SKILL", "06-50": "ACTIONSLOT",
    "06-60": "EQUIP", "06-70": "RELIC", "06-75": "EFFECT", "06-80": "SKILLITEM", "06-85": "BATTLEACT",
    "06-90": "ENEMY", "06-A0": "BATTLEGOAL", "A0": "BATTLEGOAL", "07-10": "CLUETREE", "07-20": "PRUNE",
    "07-30": "POOL", "07-40": "SETTLE", "09-20": "GENERATE",
    "M01": "M01", "M02": "M02", "M03": "M03", "M04": "M04", "M05": "M05",
    "M06": "M06", "M07": "M07", "M08": "M08", "M09": "M09", "M10": "M10",
}

def norm(s):
    return re.sub(r"[\s`·、,，。．\.\-—_/（）()\[\]【】「」]", "", s or "")


def iter_docs(root):
    base = os.path.join(root, "Code_Design")
    for dirpath, _d, files in os.walk(base):
        for name in sorted(files):
            if name.endswith(".md") and name != "README.md":
                yield os.path.join(dirpath, name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/home/ob-alive/策划书")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--report", default="")
    args = ap.parse_args()

    docs, unit_of = {}, {}
    for path in iter_docs(args.root):
        text = open(path, encoding="utf-8").read()
        rel = os.path.relpath(path, args.root)
        docs[rel] = text
        m = re.search(r"\bSYS-([A-Z0-9]+)-\d{3}\b", text)
        unit_of[rel] = m.group(1) if m else ""

    # 单元码 → {规范化名称: ID}
    index = defaultdict(dict)
    for rel, text in docs.items():
        unit = unit_of[rel]
        for rx in (HEAD_ID_NAME, TABLE_ID_NAME, TICK_ID_NAME, ID_NEAR_NAME):
            for m in rx.finditer(text):
                i, name = m.group(1), m.group(2)
                owner = i.split("-")[1]
                if unit and owner != unit:
                    continue
                key = norm(name)
                if 2 <= len(key) <= 24:
                    index[owner].setdefault(key, i)

    proposals, unresolved = [], []
    for rel, text in docs.items():
        for m in PENDING_RE.finditer(text):
            name, target_unit = m.group(1), m.group(2)
            target_unit = UNIT_ALIAS.get(target_unit, target_unit)
            table = index.get(target_unit, {})
            key = norm(name)
            hit = table.get(key)
            if not hit:
                hit = None  # 只认精确匹配；前缀兜底会误配同类不同对象，宁可留待人工
            if hit:
                proposals.append({"file": rel, "name": name, "unit": target_unit, "id": hit,
                                  "old": m.group(0), "new": "%s（%s）" % (name, hit)})
            else:
                unresolved.append({"file": rel, "name": name, "unit": target_unit, "old": m.group(0)})

    print("单元索引：%d 个单元、%d 个对象名。" % (len(index), sum(len(v) for v in index.values())))
    print("可回填建议：%d 条；未匹配：%d 条。" % (len(proposals), len(unresolved)))
    for p in proposals[:40]:
        print("  %s  %s → %s" % (p["file"].split("/")[-1], p["old"], p["new"]))
    if unresolved:
        print("未匹配（需人工或核对执行体处理）：")
        for u in unresolved[:40]:
            print("  %s  %s（目标单元 %s）" % (u["file"].split("/")[-1], u["name"], u["unit"]))

    if args.apply and proposals:
        by_file = defaultdict(list)
        for p in proposals:
            by_file[p["file"]].append(p)
        for rel, items in by_file.items():
            text = docs[rel]
            for p in items:
                text = text.replace(p["old"], p["new"])
            open(os.path.join(args.root, rel), "w", encoding="utf-8").write(text)
        print("已回填 %d 条。" % len(proposals))

    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump({"proposals": proposals, "unresolved": unresolved}, fh, ensure_ascii=False, indent=2)
        print("明细已写入 %s" % args.report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
