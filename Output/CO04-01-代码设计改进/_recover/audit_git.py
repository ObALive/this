#!/usr/bin/env python3
"""逐个校对 git 历史中的改动：找出「无意义的字符级改动」。

判据（逐对增删行）：
  A 去空白后完全相同        → 空白级噪声
  B 去空白后仅差标点        → 标点级噪声
扫描范围：指定提交的 diff，以及工作区未提交改动。
"""
import subprocess, re, sys, unicodedata

ROOT = "/home/typhoeus/this"
PUNCT = "；;，,。.、：:！!？?（）()「」\"' 　\t"


def unquote_path(p):
    """还原 git diff 中被引号包裹的路径（含八进制转义）。"""
    p = p.strip()
    if p.startswith('"') and p.endswith('"'):
        body = p[1:-1]
        out = bytearray()
        i = 0
        while i < len(body):
            if body[i] == "\\" and i + 3 < len(body) and body[i+1:i+4].isdigit():
                out.append(int(body[i+1:i+4], 8)); i += 4
            else:
                out.extend(body[i].encode("utf-8")); i += 1
        return out.decode("utf-8", errors="replace")
    return p


def norm(s):
    return re.sub(r"\s+", "", s)


def depunct(s):
    return "".join(ch for ch in norm(s) if ch not in PUNCT)


def pairs_from_diff(args):
    """把 diff 里的 -/+ 行按位置配对，返回 [(path, old, new)]。"""
    out = subprocess.run(["git", "diff", "-U0"] + args, capture_output=True, text=True, cwd=ROOT).stdout
    path = None
    dels, adds = [], []
    res = []

    def flush():
        for i in range(min(len(dels), len(adds))):
            res.append((path, dels[i], adds[i]))
        dels.clear(); adds.clear()

    for line in out.split("\n"):
        if line.startswith("+++ b/"):
            flush()
            path = unquote_path(line[6:].strip())
        elif line.startswith("--- "):
            continue
        elif line.startswith("-") and not line.startswith("---"):
            if adds:
                flush()
            dels.append(line[1:])
        elif line.startswith("+") and not line.startswith("+++"):
            adds.append(line[1:])
        else:
            flush()
    flush()
    return res


def main():
    scope = sys.argv[1:] or ["812f7fe^", "812f7fe"]
    rows = pairs_from_diff(scope)
    noise = []
    for path, old, new in rows:
        if not old.strip() or not new.strip():
            continue
        if norm(old) == norm(new):
            noise.append(("空白", path, old, new))
        elif depunct(old) == depunct(new):
            noise.append(("标点", path, old, new))
    print(f"扫描范围 {' '.join(scope)}：配对行 {len(rows)}，其中噪声 {len(noise)}")
    import collections
    c = collections.Counter(k for k, *_ in noise)
    print("  分类：", dict(c))
    for kind, path, old, new in noise[:25]:
        print(f"--- [{kind}] {path}")
        print("    旧:", old[:150])
        print("    新:", new[:150])


if __name__ == "__main__":
    main()
