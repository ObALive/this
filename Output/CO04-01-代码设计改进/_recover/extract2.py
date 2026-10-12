#!/usr/bin/env python3
"""CO04-01 事故恢复：从会话转录中抽取 write 工具载荷，重建被清空的新建文档。"""
import json, os, glob

REC = "/home/typhoeus/this/Output/CO04-01-代码设计改进/_recover"
OUT = os.path.join(REC, "files")
os.makedirs(OUT, exist_ok=True)


def iter_dicts(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from iter_dicts(v)
    elif isinstance(o, list):
        for v in o:
            yield from iter_dicts(v)


def main():
    summary = {}
    for p in sorted(glob.glob(os.path.join(REC, "*.jsonl"))):
        tag = os.path.basename(p)[:-6]
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                for node in iter_dicts(d):
                    fp = node.get("file_path")
                    content = node.get("content")
                    if not isinstance(fp, str) or not isinstance(content, str):
                        continue
                    if len(content) < 500:          # 过滤 edit 的片段
                        continue
                    rel = fp.replace("/home/typhoeus/this/", "")
                    dest = os.path.join(OUT, rel)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    prev = os.path.getsize(dest) if os.path.exists(dest) else -1
                    if len(content) >= prev:
                        with open(dest, "w", encoding="utf-8") as w:
                            w.write(content)
                        summary.setdefault(rel, []).append((tag, len(content)))
    print("== 重建的文件 ==")
    for rel, ops in sorted(summary.items()):
        print(f"  {rel}  <- {ops}")
    print("\n共", len(summary), "份")


if __name__ == "__main__":
    main()
