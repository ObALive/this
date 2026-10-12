#!/usr/bin/env python3
"""核查结论落地：① 恢复被删的行尾分号 ② 还原空白噪声。

对每一处改动先判定：
  * 行尾分号删除（旧行以「；」结尾、新行仅少了它）→ 恢复分号；
  * 去空白后完全相同 → 还原旧行原样；
  * 其余一律不动（非法引用清除、过程编号清除、归属改写、用户要求的成段删除）。
每个文件写回后复读校验非空与长度守卫。
"""
import subprocess, re, os, sys, difflib, tempfile

ROOT = "/home/typhoeus/this"
REF = sys.argv[1] if len(sys.argv) > 1 else "499941c"
APPLY = "--apply" in sys.argv


def norm(s):
    return re.sub(r"\s+", "", s)


def changed_files():
    out = subprocess.run(["git", "diff", "--name-only", "-z", REF, "HEAD"],
                         capture_output=True, cwd=ROOT).stdout.decode("utf-8").split("\0")
    out += subprocess.run(["git", "diff", "--name-only", "-z", "HEAD"],
                          capture_output=True, cwd=ROOT).stdout.decode("utf-8").split("\0")
    return sorted({f for f in out if f and f.endswith(".md")})


def main():
    files = changed_files()
    semi = ws = touched = 0
    for rel in files:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        old = subprocess.run(["git", "show", f"{REF}:{rel}"], capture_output=True,
                             cwd=ROOT).stdout.decode("utf-8", "replace")
        new = open(path, encoding="utf-8").read()
        if not old or old == new:
            continue
        nl = new.split("\n")
        ol = old.split("\n")
        sm = difflib.SequenceMatcher(None, ol, nl)
        idx = {}
        for l in ol:
            k = norm(l)
            if k:
                idx.setdefault(k, l)
        n_semi = n_ws = 0
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            for k, (a, b) in enumerate(zip(ol[i1:i2], nl[j1:j2])):
                if a.rstrip().endswith("；") and b.rstrip() == a.rstrip()[:-1]:
                    nl[j1 + k] = a.rstrip()          # 恢复行尾分号
                    n_semi += 1
                elif norm(a) == norm(b) and a != b and a.strip():
                    nl[j1 + k] = a                   # 还原空白/缩进
                    n_ws += 1
            if len(ol[i1:i2]) == len(nl[j1:j2]):
                continue
            # 空白噪声也可能表现为块内行相同但不配对，用去空白键兜底
            for k in range(j1, j2):
                l = nl[k]
                key = norm(l)
                if key and key in idx and idx[key] != l and l.strip() and idx[key].strip():
                    if norm(idx[key]) == key and not l.rstrip().endswith("；"):
                        nl[k] = idx[key]
                        n_ws += 1
        if n_semi or n_ws:
            out = "\n".join(nl)
            if not out.strip() or len(out) < len(new) * 0.95:
                print("  守卫拒绝", rel)
                continue
            if APPLY:
                fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
                with os.fdopen(fd, "w", encoding="utf-8") as w:
                    w.write(out)
                os.replace(tmp, path)
            semi += n_semi
            ws += n_ws
            touched += 1
    print(f"{'APPLY' if APPLY else 'DRY'}：恢复行尾分号 {semi} 行，还原空白 {ws} 行，涉及 {touched} 份")


if __name__ == "__main__":
    main()
