#!/usr/bin/env python3
"""CO04-01 事故恢复：抽取 write 工具载荷并直接写回工作区（仅在内容更长时覆盖）。"""
import json, os, glob, sys

REC = "/home/typhoeus/this/Output/CO04-01-代码设计改进/_recover"
ROOT = "/home/typhoeus/this"
DRY = "--apply" not in sys.argv

def main():
    seen = {}
    for p in sorted(glob.glob(os.path.join(REC, "*.jsonl"))):
        tag = os.path.basename(p)[:-6]
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                if '"write"' not in line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("type") != "tool/call":
                    continue
                data = d.get("data") or {}
                if data.get("name") != "write":
                    continue
                try:
                    args = json.loads(data.get("arguments") or "{}")
                except Exception:
                    continue
                fp = args.get("file_path")
                content = args.get("content")
                if not isinstance(fp, str) or not isinstance(content, str):
                    continue
                rel = fp.replace(ROOT + "/", "")
                cur = os.path.getsize(os.path.join(ROOT, rel)) if os.path.exists(os.path.join(ROOT, rel)) else -1
                if len(content) > cur:
                    seen.setdefault(rel, []).append((tag, len(content), cur))
    print(f"{'DRY-RUN' if DRY else 'APPLY'}：可恢复文件 {len(seen)} 份")
    for rel, ops in sorted(seen.items()):
        last = ops[-1]
        print(f"  {rel}: 现存 {last[2]} → 恢复 {last[1]} 字符（来自 {last[0]}）")
    if DRY:
        return
    for rel, ops in seen.items():
        tag, size, _ = ops[-1]
        # 取最长的一次载荷
        best = max(ops, key=lambda x: x[1])
        # 重新读取内容
        for p in sorted(glob.glob(os.path.join(REC, "*.jsonl"))):
            if os.path.basename(p)[:-6] != best[0]:
                continue
            with open(p, encoding="utf-8", errors="replace") as f:
                for line in f:
                    if '"write"' not in line:
                        continue
                    try:
                        d = json.loads(line)
                    except Exception:
                        continue
                    data = d.get("data") or {}
                    if d.get("type") != "tool/call" or data.get("name") != "write":
                        continue
                    try:
                        args = json.loads(data.get("arguments") or "{}")
                    except Exception:
                        continue
                    if args.get("file_path", "").replace(ROOT + "/", "") != rel:
                        continue
                    if len(args.get("content", "")) == best[1]:
                        dest = os.path.join(ROOT, rel)
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        with open(dest, "w", encoding="utf-8") as w:
                            w.write(args["content"])
                        print("  已恢复", rel, best[1], "字符")

if __name__ == "__main__":
    main()
