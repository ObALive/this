#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CO01：从各代码设计案抽取上游缺口条目，汇总为需求申报草稿。

用法：
    python3 extract_gaps.py [--root /home/ob-alive/策划书] [--out 输出路径]
"""

import argparse
import os
import re
import sys
from collections import defaultdict

FIELDS = ["编号", "提出单元", "缺口内容", "影响", "为何不能自行决定", "建议承接方", "建议补充产出", "优先级"]
FIELD_RE = re.compile(r"^\s*[-*\s]*(" + "|".join(FIELDS) + r")\s*[:：]\s*(.*)$")
PENDING_RE = re.compile(r"待上游补充[：:]\s*([^。\n]+)")
REQ_INLINE_RE = re.compile(r"REQ-[A-Z]+-\d+")


def iter_docs(root):
    base = os.path.join(root, "Code_Design")
    for dirpath, _d, filenames in os.walk(base):
        for name in sorted(filenames):
            if name.endswith(".md") and name != "README.md":
                yield os.path.join(dirpath, name)


def parse(path, text):
    records, cur = [], None
    for raw in text.splitlines():
        line = raw.rstrip()
        m = FIELD_RE.match(line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if key == "编号":
            if cur:
                records.append(cur)
            cur = {f: "" for f in FIELDS}
            cur["编号"] = val
            cur["_file"] = os.path.relpath(path, root)
        elif cur is not None:
            cur[key] = val
    if cur:
        records.append(cur)
    return records


def main():
    global root
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/home/ob-alive/策划书")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    root = args.root

    all_records, loose = [], []
    for path in iter_docs(root):
        text = open(path, encoding="utf-8").read()
        all_records.extend(parse(path, text))
        rel = os.path.relpath(path, root)
        gaps = PENDING_RE.findall(text)
        if gaps:
            loose.append((rel, sorted(set(g.strip() for g in gaps))))

    by_owner = defaultdict(list)
    for r in all_records:
        owner = r.get("建议承接方", "") or "未填"
        if "架构" in owner and "系统设计" not in owner:
            key = "架构设计案"
        elif "系统设计" in owner:
            key = "系统设计文档"
        else:
            key = "待判定"
        by_owner[key].append(r)

    print("结构化缺口条目 %d 条；涉及 %d 份文档。" % (len(all_records), len({r["_file"] for r in all_records})))
    for key in ["系统设计文档", "架构设计案", "待判定"]:
        print("  %s：%d 条" % (key, len(by_owner.get(key, []))))
    print()
    for key in ["系统设计文档", "架构设计案", "待判定"]:
        rows = by_owner.get(key, [])
        if not rows:
            continue
        print("## %s（%d 条）" % (key, len(rows)))
        for r in sorted(rows, key=lambda x: (x.get("优先级", ""), x.get("编号", ""))):
            print("- %s ｜ %s ｜ %s ｜ 影响：%s ｜ 承接：%s ｜ 优先级：%s" % (
                r.get("编号", ""), r.get("提出单元", "") or r["_file"], r.get("缺口内容", ""),
                r.get("影响", ""), r.get("建议承接方", ""), r.get("优先级", "")))
        print()

    if loose:
        print("## 只写了「待上游补充」而未见结构化条目的文档（%d 份）" % len(loose))
        for rel, items in loose:
            print("- %s：%s" % (rel, "；".join(items[:6]) + (" 等" if len(items) > 6 else "")))
        print()

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            for r in all_records:
                fh.write("| %s | %s | %s | %s | %s | %s | %s |\n" % (
                    r.get("编号", ""), r.get("提出单元", "") or r["_file"], r.get("缺口内容", ""),
                    r.get("影响", ""), r.get("为何不能自行决定", ""), r.get("建议承接方", ""), r.get("优先级", "")))
        print("明细已写入 %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
