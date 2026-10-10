#!/usr/bin/env python3
"""探查转录结构：找出工具调用记录的实际形态。"""
import json, os, re, sys

REC = "/home/typhoeus/this/Output/CO04-01-代码设计改进/_recover"
p = os.path.join(REC, "M01-A.jsonl")

KEYS = {}
hits = 0
with open(p, encoding="utf-8", errors="replace") as f:
    for i, line in enumerate(f):
        if i > 400:
            break
        if "file_path" not in line and "M01-01" not in line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        hits += 1
        if hits <= 3:
            print("=" * 70)
            print("顶层键：", list(d.keys()))
            print(json.dumps(d, ensure_ascii=False)[:1500])
print("\n前 400 行内命中 file_path/M01-01 的行数：", hits)

# 统计所有出现过的键名
def walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            KEYS[path + "/" + str(k)] = KEYS.get(path + "/" + str(k), 0) + 1
            walk(v, path + "/" + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            walk(v, path + "/*")

with open(p, encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            walk(json.loads(line))
        except Exception:
            pass
print("\n== 出现次数最多的键路径（前 40）==")
for k, v in sorted(KEYS.items(), key=lambda x: -x[1])[:40]:
    print(f"  {v:6d}  {k}")
