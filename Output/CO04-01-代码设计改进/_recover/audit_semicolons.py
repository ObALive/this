#!/usr/bin/env python3
"""按转录重放 write+edit 得到"清理前"基线，用于核对清理是否误删了行尾分号。

只做核对与报告，不写文件。
"""
import glob, json, os, difflib, re, sys

ROOT = "/home/typhoeus/this"
REC = os.path.join(ROOT, "Output/CO04-01-代码设计改进/_recover")
ORDER = ["MAIN", "M01-A", "M01-B", "M01-C", "ITEM", "EQUIP", "SKILL"]
SKIP = ("Code_Design/00-架构单元/M01-", "Code_Design/01-通用系统/30_", "Code_Design/01-通用系统/70_")


def ops():
    seq = []
    for tag in ORDER:
        p = os.path.join(REC, tag + ".jsonl")
        if not os.path.exists(p):
            continue
        for line in open(p, encoding="utf-8", errors="replace"):
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
            if not fp or fp.startswith(SKIP) or not os.path.exists(os.path.join(ROOT, fp)):
                continue
            seq.append((ORDER.index(tag), d.get("seq", 0), name, fp, args))
    seq.sort(key=lambda x: (x[0], x[1]))
    return seq


def main():
    base = {}
    for _, _, name, fp, args in ops():
        if name == "write":
            c = args.get("content") or ""
            if c:
                base[fp] = c
        else:
            old, new = args.get("old_string", ""), args.get("new_string", "")
            if fp in base and old and old in base[fp]:
                base[fp] = base[fp].replace(old, new, 1)
    print("重建基线文件数：", len(base))
    tot = 0
    for fp, old in sorted(base.items()):
        new = open(os.path.join(ROOT, fp), encoding="utf-8").read()
        ol, nl = old.split("\n"), new.split("\n")
        sm = difflib.SequenceMatcher(None, ol, nl)
        lost = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "replace" and (i2 - i1) == (j2 - j1):
                for a, b in zip(ol[i1:i2], nl[j1:j2]):
                    if a.rstrip().endswith("；") and not b.rstrip().endswith(("；", "。", "|", "：", "）")):
                        lost.append((a[:80], b[:80]))
        if lost:
            print(f"--- {fp}：行尾分号丢失 {len(lost)} 行")
            for a, b in lost[:3]:
                print("     旧:", a)
                print("     新:", b)
            tot += len(lost)
    print("\n合计丢失行尾分号：", tot, "行")


if __name__ == "__main__":
    main()
