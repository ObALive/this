#!/usr/bin/env python3
"""CO04-01 事故恢复：从 MAIN 转录按序重放对指定文件的 write/edit 操作，补回写后编辑。"""
import json, os, sys

REC = "/home/typhoeus/this/Output/CO04-01-代码设计改进/_recover"
ROOT = "/home/typhoeus/this"
TARGETS = [
    "Code_Design/01-通用系统/30_元对象与组件代码设计案.md",
    "Code_Design/01-通用系统/70_元技能代码设计案.md",
    "Code_Design/00-架构单元/M01_核心与基础设施代码设计案.md",
    "Code_Design/06-战斗/30_战场与战棋规则代码设计案.md",
]
DRY = "--apply" not in sys.argv


def ops_for():
    """按出现顺序产出 (op, path, payload)。"""
    out = []
    for tag in ["MAIN"]:
        p = os.path.join(REC, tag + ".jsonl")
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
                fp = args.get("file_path", "").replace(ROOT + "/", "")
                if fp not in TARGETS:
                    continue
                out.append((name, fp, args, d.get("seq")))
    return out


def main():
    ops = ops_for()
    counts = {}
    for name, fp, args, seq in ops:
        counts.setdefault(fp, {}).setdefault(name, 0)
        counts[fp][name] += 1
    print("待重放操作统计：")
    for fp, c in counts.items():
        print(f"  {fp}: write {c.get('write',0)} 次, edit {c.get('edit',0)} 次")
    if DRY:
        print("\n（干跑；加 --apply 执行）")
        return
    applied = 0
    for name, fp, args, seq in ops:
        dest = os.path.join(ROOT, fp)
        cur = open(dest, encoding="utf-8").read() if os.path.exists(dest) else ""
        if name == "write":
            content = args.get("content", "")
            if len(content) >= len(cur):
                open(dest, "w", encoding="utf-8").write(content)
                applied += 1
        else:
            old, new = args.get("old_string", ""), args.get("new_string", "")
            if old and old in cur:
                open(dest, "w", encoding="utf-8").write(cur.replace(old, new, 1))
                applied += 1
                cur = cur.replace(old, new, 1)
    print("重放成功操作数：", applied)


if __name__ == "__main__":
    main()
