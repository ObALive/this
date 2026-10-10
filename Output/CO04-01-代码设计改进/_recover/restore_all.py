#!/usr/bin/env python3
"""CO04-01 事故恢复（总）：按转录顺序重放 write/edit，重建本任务新建的 15 份文档。"""
import json, os, glob, sys

REC = "/home/typhoeus/this/Output/CO04-01-代码设计改进/_recover"
ROOT = "/home/typhoeus/this"

TARGETS = [
    "Code_Design/00-架构单元/M01_核心与基础设施代码设计案.md",
    "Code_Design/01-通用系统/30_元对象与组件代码设计案.md",
    "Code_Design/01-通用系统/70_元技能代码设计案.md",
    "系统设计文档/01-通用系统/30_元对象与组件设计补充说明.md",
    "系统设计文档/01-通用系统/70-元技能/70_元技能设计补充说明.md",
] + [f"Code_Design/00-架构单元/M01-{i:02d}_{n}代码设计案.md" for i, n in [
    (1, "单元装配声明"), (2, "数据域持有"), (3, "存档服务"), (4, "配置服务"),
    (5, "随机服务"), (6, "时间服务"), (7, "输入服务"), (8, "资源服务"),
    (9, "场景管理服务"), (10, "日志服务"), (11, "事件分发器")]]

DRY = "--apply" not in sys.argv
ORDER = ["MAIN", "M01-A", "M01-B", "M01-C", "ITEM", "EQUIP", "SKILL"]


def collect():
    seqs = {t: [] for t in ORDER}
    for tag in ORDER:
        p = os.path.join(REC, tag + ".jsonl")
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                if '"tool/call"' not in line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("type") != "tool/call":
                    continue
                data = d.get("data") or {}
                name = data.get("name")
                if name not in ("write", "edit"):
                    continue
                try:
                    args = json.loads(data.get("arguments") or "{}")
                except Exception:
                    continue
                fp = (args.get("file_path") or "").replace(ROOT + "/", "")
                if fp in TARGETS:
                    seqs[tag].append((d.get("seq", 0), name, fp, args))
        seqs[tag].sort(key=lambda x: x[0])
    return seqs


def main():
    seqs = collect()
    plan = {}
    for tag in ORDER:
        for _, name, fp, args in seqs[tag]:
            plan.setdefault(fp, []).append((name, len(args.get("content", "") or args.get("new_string", ""))))
    print(f"{'DRY' if DRY else 'APPLY'}：涉及文件 {len(plan)} 份")
    for fp, ops in sorted(plan.items()):
        cur = os.path.getsize(os.path.join(ROOT, fp)) if os.path.exists(os.path.join(ROOT, fp)) else -1
        print(f"  {fp}: 现有 {cur} 字节，重放 {len(ops)} 次（{''.join('w' if o[0]=='write' else 'e' for o in ops)}）")
    if DRY:
        return
    # 按顺序重放：先 write 建立基线，再逐条 edit
    for tag in ORDER:
        for _, name, fp, args in seqs[tag]:
            dest = os.path.join(ROOT, fp)
            cur = open(dest, encoding="utf-8").read() if os.path.exists(dest) else ""
            if name == "write":
                content = args.get("content", "")
                if content:
                    open(dest, "w", encoding="utf-8").write(content)
            else:
                old, new = args.get("old_string", ""), args.get("new_string", "")
                if old and old in cur:
                    open(dest, "w", encoding="utf-8").write(cur.replace(old, new, 1))
    print("重放完成")
    for fp in sorted(plan):
        print(f"  {len(open(os.path.join(ROOT, fp), encoding='utf-8').read())}  {fp}")


if __name__ == "__main__":
    main()
