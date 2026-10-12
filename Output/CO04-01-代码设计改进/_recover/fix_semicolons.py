#!/usr/bin/env python3
"""修复被通用标点清洗误删的行尾分号。

判定依据：以各文件的转录 write 载荷为基线（恢复前状态），做行级配对比较；
只在「旧行以「；」结尾、且该行不含任何被删的越界引用」时，把行尾分号补回。
同行含有被删引用（旧行与新行差异中出现 Output/Task/Report/Input/Dsh、C-xx-xx-xx、
回答 N、GAP 编号）时不补，避免把已清除引用的孤立体。
"""
import glob, json, os, re, difflib, sys, tempfile

ROOT = "/home/typhoeus/this"
REC = os.path.join(ROOT, "Output/CO04-01-代码设计改进/_recover")
DRY = "--apply" not in sys.argv
ILLEGAL = re.compile(r"Output/|Task/|Report/|Input/|Dsh/|C-\d\d-[a-z]{2}-\d\d|回答\s*\d|GAP-\d|R001|S0[12]\b|C0\d\b")


def baseline(path_rel):
    """从转录中取该文件 write 载荷的最长版本。"""
    best = None
    for p in glob.glob(os.path.join(REC, "*.jsonl")):
        for line in open(p, encoding="utf-8", errors="replace"):
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
            if args.get("file_path", "").replace(ROOT + "/", "") != path_rel:
                continue
            c = args.get("content") or ""
            if c and (best is None or len(c) > len(best)):
                best = c
    return best


def main():
    fixed_files = fixed_lines = skipped = 0
    for root in ("Code_Design", "系统设计文档", "架构设计文档"):
         for p in glob.glob(os.path.join(ROOT, root, "**", "*.md"), recursive=True):
            rel = os.path.relpath(p, ROOT)
            old = baseline(rel)
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
                    # 该行差异里若出现被删引用痕迹，则不补
                    if ILLEGAL.search(a) or ILLEGAL.search(b):
                        skipped += 1
                        continue
                    out[j1 + k] = b.rstrip() + "；"
                    n += 1
            if n:
                cand = "\n".join(out)
                if not cand.strip() or len(cand) < len(new) * 0.95:
                    print("  守卫拒绝", rel)
                    continue
                if not DRY:
                    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), suffix=".tmp")
                    with os.fdopen(fd, "w", encoding="utf-8") as w:
                        w.write(cand)
                    os.replace(tmp, p)
                fixed_files += 1
                fixed_lines += n
        print(f"{'DRY' if DRY else 'APPLY'}：补回分号 {fixed_lines} 行，涉及 {fixed_files} 份；因含被删引用而跳过 {skipped} 行")


if __name__ == "__main__":
    main()
