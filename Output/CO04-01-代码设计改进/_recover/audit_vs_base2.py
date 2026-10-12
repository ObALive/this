#!/usr/bin/env python3
"""对照基线提交逐类核查改动（路径用 -z 解析，避免八进制转义）。

分类：
  实义改动  删除行含非法引用/过程编号，或新增行带来新内容
  半角分号删除  旧行以「；」结尾、新行为其去掉尾分号
  空白噪声  去空白后完全相同（需还原）
  其它      需人工判断
另报告：每个文件的净增删行数与「删除显著多于新增」的可疑位置。
"""
import subprocess, re, os, sys, difflib, collections

ROOT = "/home/typhoeus/this"
REF = sys.argv[1] if len(sys.argv) > 1 else "499941c"
ILLEGAL = re.compile(r"Output/|Task/|Report/|Input/|Tool/|Dsh/|C-\d\d-[a-z]{2}-\d\d|回答\s*\d|GAP-\d|R001|S0[12]\b|C0\d\b|《CO0\d|编制约定|回填执行约定")
PUNCT = "；;，,。.、：:！!？?（）()「」\"' \t"


def norm(s):
    return re.sub(r"\s+", "", s)


def depunct(s):
    return "".join(c for c in norm(s) if c not in PUNCT)


def changed_files():
    out = subprocess.run(["git", "diff", "--name-only", "-z", REF, "HEAD"],
                         capture_output=True, cwd=ROOT).stdout.decode("utf-8").split("\0")
    out += subprocess.run(["git", "diff", "--name-only", "-z", "HEAD"],
                          capture_output=True, cwd=ROOT).stdout.decode("utf-8").split("\0")
    return sorted({f for f in out if f and f.endswith(".md")})


def main():
    files = changed_files()
    cat = collections.Counter()
    semi, ws, susp, other_files = [], [], [], []
    for rel in files:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        old = subprocess.run(["git", "show", f"{REF}:{rel}"], capture_output=True,
                             cwd=ROOT).stdout.decode("utf-8", "replace")
        new = open(path, encoding="utf-8").read()
        if not old or old == new:
            continue
        ol, nl = old.split("\n"), new.split("\n")
        sm = difflib.SequenceMatcher(None, ol, nl)
        s = w = il = ot = 0
        ot_samples = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            o, n = ol[i1:i2], nl[j1:j2]
            for a, b in zip(o, n):
                if ILLEGAL.search(a) and not ILLEGAL.search(b):
                    il += 1
                elif a.rstrip().endswith("；") and b.rstrip() == a.rstrip()[:-1]:
                    s += 1
                elif norm(a) == norm(b):
                    w += 1
                elif depunct(a) == depunct(b):
                    s += 1
                else:
                    ot += 1
                    if len(ot_samples) < 2:
                        ot_samples.append((a, b))
            if tag == "delete" and len(o) >= 3:
                clean = [l for l in o if not ILLEGAL.search(l)]
                if len(clean) >= 3:
                    susp.append((len(clean), rel, clean[0][:90]))
        cat["实义改动"] += il
        cat["行尾分号删除"] += s
        cat["空白噪声"] += w
        cat["其它"] += ot
        if s:
            semi.append((s, rel))
        if w:
            ws.append((w, rel))
        if ot:
            other_files.append((ot, rel, ot_samples))
    print(f"基线 {REF}：核查 {len(files)} 份文件")
    for k, v in cat.items():
        print(f"   {k}: {v}")
    print("\n--- 行尾分号删除最多的文件")
    for d, rel in sorted(semi, reverse=True)[:12]:
        print(f"    -{d}  {rel}")
    print("\n--- 空白噪声（需还原）")
    print("    无" if not ws else "")
    for d, rel in sorted(ws, reverse=True)[:10]:
        print(f"    {d} 行  {rel}")
    print("\n--- 含未被引用清理解释的删除块（≥3 行，需人工判断）")
    print("    无" if not susp else "")
    for d, rel, smp in sorted(susp, reverse=True)[:10]:
        print(f"    -{d} 行  {rel}\n         {smp}")
    print("\n--- 其它改动样例")
    for d, rel, smp in sorted(other_files, reverse=True)[:6]:
        print(f"    {d} 行  {rel}")
        for a, b in smp:
            print("       旧:", a[:110])
            print("       新:", b[:110])


if __name__ == "__main__":
    main()
