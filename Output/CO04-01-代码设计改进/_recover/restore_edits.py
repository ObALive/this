#!/usr/bin/env python3
"""CO04-01 事故恢复（补）：重放对被清空旧文档的 edit 操作。"""
import json, os, glob, sys

REC = "/home/typhoeus/this/Output/CO04-01-代码设计改进/_recover"
ROOT = "/home/typhoeus/this"
DRY = "--apply" not in sys.argv
ORDER = ["MAIN", "M01-A", "M01-B", "M01-C", "ITEM", "EQUIP", "SKILL"]

# 本次恢复已用转录重建的新文档，不在此脚本中重复处理
SKIP_PREFIX = ("Code_Design/00-架构单元/M01-", "Code_Design/01-通用系统/30_", "Code_Design/01-通用系统/70_")


def main():
    ops = []
    for tag in ORDER:
        p = os.path.join(REC, tag + ".jsonl")
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                if '"edit"' not in line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("type") != "tool/call":
                    continue
                data = d.get("data") or {}
                if data.get("name") != "edit":
                    continue
                try:
                    args = json.loads(data.get("arguments") or "{}")
                except Exception:
                    continue
                fp = (args.get("file_path") or "").replace(ROOT + "/", "")
                if not fp or fp.startswith(SKIP_PREFIX):
                    continue
                if not os.path.exists(os.path.join(ROOT, fp)):
                    continue
                ops.append((tag, d.get("seq", 0), fp, args))
    ops.sort(key=lambda x: (ORDER.index(x[0]), x[1]))
    stat = {}
    for tag, seq, fp, args in ops:
        cur = open(os.path.join(ROOT, fp), encoding="utf-8").read()
        old = args.get("old_string", "")
        hit = bool(old) and old in cur
        stat.setdefault(fp, [0, 0, 0])
        if hit:
            stat[fp][0] += 1
        elif not old:
            stat[fp][2] += 1
        else:
            stat[fp][1] += 1
        if hit and not DRY:
            open(os.path.join(ROOT, fp), "w", encoding="utf-8").write(
                cur.replace(old, args.get("new_string", ""), 1)
            )
    print(f"{'DRY' if DRY else 'APPLY'}：edit 操作 {len(ops)} 条，涉及 {len(stat)} 份文件")
    tot_ok = sum(v[0] for v in stat.values())
    tot_miss = sum(v[1] for v in stat.values())
    print(f"  命中 {tot_ok} 条，未命中 {tot_miss} 条，空 old_string {sum(v[2] for v in stat.values())} 条")
    print("\n未命中的文件（需人工核对）：")
    for fp, (ok, miss, empty) in sorted(stat.items(), key=lambda x: -x[1][1]):
        if miss:
            print(f"  {miss:3d} 未命中 / {ok:3d} 命中  {fp}")


if __name__ == "__main__":
    main()
