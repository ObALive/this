#!/usr/bin/env python3
"""盘点三个设计库中的非法引用（指向 Task/Output/Report/Input/Tool 等外部位置）。"""
import os, re, glob, collections

ROOT = "/home/typhoeus/this"
LIBS = {
    "系统设计文档": 1,
    "架构设计文档": 2,
    "Code_Design": 3,
}

# 非法：Task/ Output/ Report/ Input/ Tool/ .uniwork/ 根目录散文件
ILLEGAL = re.compile(
    r"(?:^|[\s`（(【\[])((?:Task|Output|Report|Input|Tool|\.uniwork)/[^\s`）)】\]、，。；：｜|]*"
    r"|Dsh/[^\s`）)】\]、，。；：｜|]*"
    r"|codex-unity-mcp-research\.md)"
)


def main():
    hits = collections.defaultdict(list)
    for lib in LIBS:
        for p in glob.glob(os.path.join(ROOT, lib, "**", "*.md"), recursive=True) + \
                 glob.glob(os.path.join(ROOT, lib, "**", "*.csv"), recursive=True):
            try:
                s = open(p, encoding="utf-8").read()
            except Exception:
                continue
            for i, line in enumerate(s.split("\n"), 1):
                for m in ILLEGAL.finditer(line):
                    hits[p].append((i, m.group(1).strip(), line.strip()))
    total = sum(len(v) for v in hits.values())
    print(f"含非法引用的文件 {len(hits)} 份，引用点 {total} 处\n")
    per = collections.Counter()
    for p, items in sorted(hits.items()):
        rel = os.path.relpath(p, ROOT)
        print(f"--- {rel}（{len(items)} 处）")
        for i, ref, line in items[:6]:
            print(f"    L{i}: {ref}")
            print(f"         {line[:150]}")
        if len(items) > 6:
            print(f"    …其余 {len(items)-6} 处")
        for _, ref, _ in items:
            per[ref.split("/")[0]] += 1
    print("\n按目标目录统计：", dict(per))


if __name__ == "__main__":
    main()
