#!/usr/bin/env python3
"""对照基线提交，逐类核查当前工作区的改动。

输出四类：
  A 应当保留的实义改动（非法引用清除、过程编号清除、归属改写等）
  B 行尾分号删改（历史遗留字符，需按裁定恢复）
  C 空白/缩进改动（应为 0，若不为 0 则是需要还原的噪声）
  D 其它可疑改动（净删除且删除行不含非法引用 → 需人工判断是否误删）
"""
import subprocess, re, os, sys, collections

ROOT = "/home/typhoeus/this"
REF = sys.argv[1] if len(sys.argv) > 1 else "499941c"
ILLEGAL = re.compile(r"Output/|Task/|Report/|Input/|Tool/|Dsh/|C-\d\d-[a-z]{2}-\d\d|回答\s*\d|GAP-\d|R001|S0[12]\b|C0\d\b|《CO0\d|编制约定|回填执行约定")
PUNCT = "；;，,。.、：:！!？?（）()「」\"' \t"


def norm(s):
    return re.sub(r"\s+", "", s)


def depunct(s):
    return "".join(c for c in norm(s) if c not in PUNCT)


def files():
    tree = subprocess.run(["git", "ls-tree", "-r", "--name-only", "-z", REF],
                          capture_output=True, cwd=ROOT).stdout.decode("utf-8").split("\0")
    libs = [f for f in tree if f and f.split("/")[0] in ("系统设计文档", "Code_Design", "架构设计文档") and f.endswith(".md")]
    # 也在 HEAD 中但不在 REF 的新建文件
    tree2 = subprocess.run(["git", "ls-tree", "-r", "--name-only", "-z", "HEAD"],
                           capture_output=True, cwd=ROOT).stdout.decode("utf-8").split("\0")
    libs2 = [f for f in tree2 if f and f.split("/")[0] in ("系统设计文档", "Code_Design", "架构设计文档") and f.endswith(".md")]
    return sorted(set(libs) | set(libs2))


def main():
    cat = collections.Counter()
    semi_only = []
    ws_noise = []
    suspicious = []
    dirty = subprocess.run(["git", "diff", "--name-only", REF], capture_output=True, text=True, cwd=ROOT).stdout.split()
    # 并入本轮的改动文件（含新建）
    dirty += subprocess.run(["git", "diff", "--name-only", "499941c", "1e60296"],
                            capture_output=True, text=True, cwd=ROOT).stdout.split()
    dirty = sorted({d for d in dirty if d.endswith(".md")})
    for rel in dirty:
        if not rel.endswith(".md"):
            continue
        if not os.path.exists(os.path.join(ROOT, rel)):
            continue
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        old = subprocess.run(["git", "show", f"{REF}:{rel}"], capture_output=True, text=True,
                             errors="replace", cwd=ROOT).stdout
        new = open(path, encoding="utf-8").read()
        ol, nl = old.split("\n"), new.split("\n")
        sm = __import__("difflib").SequenceMatcher(None, ol, nl)
        semi = ws = illegal = other = 0
        other_samples = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            o, n = ol[i1:i2], nl[j1:j2]
            for a, b in zip(o, n):
                if ILLEGAL.search(a) and not ILLEGAL.search(b):
                    illegal += 1
                elif a.rstrip().endswith("；") and b.rstrip() == a.rstrip()[:-1]:
                    semi += 1
                elif norm(a) == norm(b) and a != b:
                    ws += 1
                elif depunct(a) == depunct(b):
                    semi += 1
                else:
                    other += 1
                    if len(other_samples) < 2:
                        other_samples.append((a, b))
            if len(o) != len(n):
                # 整块增删
                removed = [l for l in o if not ILLEGAL.search(l)]
                added = [l for l in n]
                if removed and len(removed) > len(added):
                    suspicious.append((len(removed) - len(added), rel, removed[0][:90]))
        cat["实义改动行"] += illegal
        cat["行尾分号行"] += semi
        cat["空白噪声行"] += ws
        cat["其它"] += other
        if semi:
            semi_only.append((semi, rel))
        if ws:
            ws_noise.append((ws, rel))
    print(f"基线 {REF}，工作区共 {len(dirty)} 份 md 差异")
    for k, v in cat.items():
        print(f"   {k}: {v}")
    print("\n--- 行尾分号减少最多的文件")
    for d, rel in sorted(semi_only, reverse=True)[:10]:
        print(f"    -{d}  {rel}")
    print("\n--- 空白噪声（需要还原）")
    if not ws_noise:
        print("    无")
    for d, rel in sorted(ws_noise, reverse=True)[:10]:
        print(f"    {d} 行  {rel}")
    print("\n--- 净删除较多的位置（需人工判断）")
    for d, rel, sample in sorted(suspicious, reverse=True)[:10]:
        print(f"    -{d} 行  {rel}\n         {sample}")


if __name__ == "__main__":
    main()
