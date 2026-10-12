#!/usr/bin/env python3
"""探查工具调用参数的实际存放位置。"""
import json, os

REC = "/home/typhoeus/this/Output/CO04-01-代码设计改进/_recover"
p = os.path.join(REC, "M01-A.jsonl")

shown = 0
with open(p, encoding="utf-8", errors="replace") as f:
    for line in f:
        if "M01-01_单元装配声明" not in line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        t = d.get("type")
        if t in ("user/message", "agent/inbox/spliced"):
            continue
        print("=" * 72)
        print("type:", t, "| keys:", list(d.keys()))
        s = json.dumps(d, ensure_ascii=False)
        print(s[:2000])
        shown += 1
        if shown >= 4:
            break
