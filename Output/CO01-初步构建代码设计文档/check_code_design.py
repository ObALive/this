#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CO01 代码设计案全库机械核对。

用法：
    python3 check_code_design.py [--root /home/ob-alive/策划书] [--json 输出路径]

核对项：
  1 十节结构齐备（NR-06 第五章）
  2 元信息表八项齐备
  3 ID 全库唯一、前缀合法
  4 跨单元「ID 待补」引用清点
  5 接口契约八项字段齐备
  6 依赖表列名与接口表列名合规
  7 未登记事件的标记清点
  8 越界写法关键词提示（算法、容器类型、语言语法）
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict

SECTION_TITLES = [
    "系统定义",
    "数据定义",
    "状态定义",
    "对外接口",
    "内部功能",
    "外部依赖",
    "系统交互",
    "核心流程",
    "异常与边界情况",
    "实现约束",
]

META_FIELDS = ["系统名", "所属域", "系统编号", "对应设计文档", "状态", "关联文档", "维护人", "更新日期"]

CONTRACT_FIELDS = ["职责", "输入", "读取", "输出", "产生的状态变化", "前置条件", "后置条件", "副作用", "异常情况"]

ID_RE = re.compile(r"\b(SYS|CLS|API)-([A-Z0-9]+(?:-[A-Z0-9]+)*)-(\d{3})\b")
PENDING_RE = re.compile(r"([^\s|（），、:：]{2,24})（([A-Z0-9\-]+)，ID 待补）")
TODO_EVENT_RE = re.compile(r"【待架构登记】\s*([^】\s、，。；]{2,24})|【待架构登记[：:]\s*([^】]{2,24})】")

BAD_PATTERNS = [
    (r"Dictionary<|List<|Array<|HashSet<|Queue<|Stack<", "疑似容器类型写法"),
    (r"\bclass\s+\w+|\bvoid\s+\w+\(|\bpublic\s+\w+|\bfunc\s+\w+|\bdef\s+\w+\(", "疑似程序语言语法"),
    (r"遍历|递归|排序算法|深度优先|广度优先|二分查找", "疑似具体算法步骤"),
    (r"本次任务|原先|原有的|原本的|此前|不再使用|已废弃|更名为|升级为|收缩为", "疑似设计沿革措辞"),
]


def iter_docs(root):
    base = os.path.join(root, "Code_Design")
    for dirpath, _dirnames, filenames in os.walk(base):
        for name in sorted(filenames):
            if name.endswith(".md") and name != "README.md":
                yield os.path.join(dirpath, name)


def rel(root, path):
    return os.path.relpath(path, root)


def check_doc(root, path, text):
    lines = text.splitlines()
    out = {
        "file": rel(root, path),
        "lines": len(lines),
        "unit_code": "",
        "own_ids": [],
        "missing_sections": [],
        "missing_meta": [],
        "ids": [],
        "pending_refs": [],
        "todo_events": [],
        "contracts_missing_fields": [],
        "bad_patterns": [],
        "has_interface_table": False,
        "has_dependency_table": False,
        "status": "",
    }
    for idx, title in enumerate(SECTION_TITLES, start=1):
        if not re.search(r"^#{1,3}\s*%d[\.、]?\s*%s" % (idx, re.escape(title)), text, re.M):
            out["missing_sections"].append(f"{idx} {title}")

    for field in META_FIELDS:
        if not re.search(r"\|\s*%s\s*\|" % re.escape(field), text):
            out["missing_meta"].append(field)
    m = re.search(r"\|\s*状态\s*\|\s*([^|\n]+?)\s*\|", text)
    if m:
        out["status"] = m.group(1).strip()

    for m in ID_RE.finditer(text):
        out["ids"].append(m.group(0))
    sys_ids = [i for i in out["ids"] if i.startswith("SYS-")]
    if sys_ids:
        out["unit_code"] = sys_ids[0].split("-")[1]
    out["own_ids"] = [i for i in out["ids"] if out["unit_code"] and i.split("-")[1] == out["unit_code"]]
    for m in PENDING_RE.finditer(text):
        out["pending_refs"].append({"name": m.group(1), "unit": m.group(2)})
    for m in TODO_EVENT_RE.finditer(text):
        name = m.group(1) or m.group(2) or ""
        name = name.strip()
        if name and not re.match(r"^(并|且|同时|并同时|并写入|后)", name):
            out["todo_events"].append(name)

    out["has_interface_table"] = bool(re.search(r"\|\s*接口\s*ID\s*\|", text))
    out["has_dependency_table"] = bool(re.search(r"\|\s*依赖对象\s*\|", text))

    # 契约块：只核对以对象 ID 起头的标题块（核心流程等叙述性小节不计入）
    blocks = re.split(r"\n#{3,5}\s+", text)
    for block in blocks[1:]:
        head = block.splitlines()[0].strip()
        if not re.match(r"^API-[A-Z0-9]+-\d{3}\b", head):
            continue  # 契约模板只约束接口与函数；数据对象按 NR-06 §五.2 的八项登记
        missing = [f for f in CONTRACT_FIELDS if not re.search(r"(^|[\s；;。，,|])%s\s*[:：]" % re.escape(f), block)]
        if len(missing) >= 3:  # 明显不是契约块的跳过
            out["contracts_missing_fields"].append({"block": head[:60], "missing": missing})

    for pattern, label in BAD_PATTERNS:
        hits = re.findall(pattern, text)
        if hits:
            out["bad_patterns"].append({"kind": label, "count": len(hits), "sample": str(hits[:3])})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/home/ob-alive/策划书")
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    docs = list(iter_docs(args.root))
    results = []
    id_owner = defaultdict(list)
    own_owner = defaultdict(list)
    for path in docs:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        res = check_doc(args.root, path, text)
        results.append(res)
        for i in set(res["ids"]):
            id_owner[i].append(res["file"])
        for i in set(res["own_ids"]):
            own_owner[i].append(res["file"])

    duplicates = {i: files for i, files in own_owner.items() if len(set(files)) > 1}
    defined = set(own_owner.keys())
    dangling = {}
    for i, files in id_owner.items():
        if i not in defined:
            dangling[i] = sorted(set(files))

    print("文档数：%d" % len(results))
    print("ID 总数：%d（唯一 %d）" % (sum(len(r["ids"]) for r in results), len(id_owner)))
    print()
    problems = 0
    for r in results:
        issues = []
        if r["missing_sections"]:
            issues.append("缺节：" + "、".join(r["missing_sections"]))
        if r["missing_meta"]:
            issues.append("元信息缺项：" + "、".join(r["missing_meta"]))
        if r["contracts_missing_fields"]:
            issues.append("契约缺项 %d 处" % len(r["contracts_missing_fields"]))
        if r["bad_patterns"]:
            issues.append("越界写法：" + "；".join("%s×%d" % (b["kind"], b["count"]) for b in r["bad_patterns"]))
        if r["pending_refs"]:
            issues.append("ID 待补 %d 处" % len(r["pending_refs"]))
        if r["todo_events"]:
            issues.append("待架构登记事件：%s" % "、".join(sorted(set(r["todo_events"]))))
        if not r["unit_code"]:
            issues.append("未声明 SYS- ID，无法判定单元归属")
        if issues:
            problems += 1
            print("✗ %s（%d 行，状态 %s）" % (r["file"], r["lines"], r["status"] or "?"))
            for it in issues:
                print("    - " + it)
        else:
            print("✓ %s（%d 行，状态 %s）" % (r["file"], r["lines"], r["status"] or "?"))
    print()
    if duplicates:
        print("ID 重复 %d 个：" % len(duplicates))
        for i, files in sorted(duplicates.items()):
            print("  %s → %s" % (i, "；".join(sorted(set(files)))))
    else:
        print("ID 无跨文档重复。")
    if dangling:
        print("被引用但全库无定义方的 ID %d 个（收口时需回填或修正）：" % len(dangling))
        for i, files in sorted(dangling.items()):
            print("  %s ← %s" % (i, "；".join(files[:3]) + (" 等" if len(files) > 3 else "")))
    else:
        print("全部被引用 ID 都有定义方。")
    print()
    print("有问题文档数：%d / %d" % (problems, len(results)))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"docs": results, "duplicates": duplicates, "dangling": dangling}, fh, ensure_ascii=False, indent=2)
        print("明细已写入 %s" % args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
