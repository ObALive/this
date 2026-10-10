#!/usr/bin/env python3
"""修复被通用标点清洗误删的行尾分号（三库版）。

基线：各文件的转录 write 载荷（新建文档）或 write+edit 重放结果（改写文档）。
判定：仅当旧行以「；」结尾、当前行不以「；。|：）」结尾、且该行差异中没有被删的
越界引用痕迹时，把行尾分号补回。
"""
import glob, json, os, re, difflib, sys, tempfile

ROOT = "/home/typhoeus/this"
REC = os.path.join(ROOT, "Output/CO04-01-代码设计改进/_recover")
ORDER = ["MAIN", "M01-A", "M01-B", "M01-C", "ITEM", "EQUIP", "SKILL"]
SKIP_NEW = ("Code_Design/00-架构单元/M01-", "Code_Design/01-通用系统/30_", "Code_Design/01-通用系统/70_")
ILLEGAL = re.compile(r"Output/|Task/|Report/|Input/|Dsh/|C-\d\d-[a-z]{2}-\d\d|回答\s*\d|GAP-\d|R001|S0[12]\b|C0\d\b")
DRY = "--apply" not in sys.argv


def baselines():
    """返回 {相对路径: 清理前内容}。"""
    base = {}
    # 新建与重写文档：按转录顺序重放
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
            if not fp:
                continue
            seq.append((ORDER.index(tag) if tag in ORDER else 99, d.get("seq", 0), name, fp, args))
    seq.sort(key=lambda x: (x[0], x[1]))
    for _, _, name, fp, args in seq:
        if name == "write":
            c = args.get("content") or ""
            if c:
                base[fp] = c
        else:
            old, new = args.get("old_string", ""), args.get("new_string", "")
            if fp in base and old and old in base[fp]:
                base[fp] = base[fp].replace(old, new, 1)
    return base


def main():
    base = baselines()
    files = lines = skipped = 0
    for root in ("Code_Design", "系统设计文档", "架构设计文档"):
        for p in glob.glob(os.path.join(ROOT, root, "**", "*.md"), recursive=True):
            rel = os.path.relpath(p, ROOT)
            old = base.get(rel)
            if not old:
                continue
            new = open(p, encoding="utf-8").read()
            ol, nl = old.split("\n"), new.split("\n")
            sm = difflib.SequenceMatcher(None, ol, nl)
            out = list(nl)
            n = 0
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag != "replace" or (i2 - i1) != (j2 - j1):
                    continue
                for k, (a, b) in enumerate(zip(ol[i1:i2], nl[j1:j2])):
                    if not a.rstrip().endswith("；"):
                        continue
                    if b.rstrip().endswith(("；", "。", "|", "：", "）")):
                        continue
                    if ILLEGAL.search(a) or ILLEGAL.search(b):
                        skipped += 1
                        continue
                    out[j1 + k] = b.rstrip() + "；"
                    n += 1
            if not n:
                continue
            cand = "\n".join(out)
            if not cand.strip() or len(cand) < len(new) * 0.95:
                print("  守卫拒绝", rel)
                continue
            if not DRY:
                fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), suffix=".tmp")
                with os.fdopen(fd, "w", encoding="utf-8") as w:
                    w.write(cand)
                os.replace(tmp, p)
            files += 1
            lines += n
    print(f"{'DRY' if DRY else 'APPLY'}：补回分号 {lines} 行，涉及 {files} 份；跳过 {skipped} 行")


if __name__ == "__main__":
    main()
