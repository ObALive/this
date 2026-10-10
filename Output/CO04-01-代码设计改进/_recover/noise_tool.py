#!/usr/bin/env python3
"""校对 git 改动中的「无意义字符级改动」并还原。

用法：
  python3 noise_tool.py audit <rev_old> <rev_new>      # 只报告
  python3 noise_tool.py revert <rev_old> <rev_new>     # 还原噪声（不改实义改动）
  python3 noise_tool.py audit-wt                       # 报告工作区未提交改动中的噪声
  python3 noise_tool.py revert-wt                      # 还原工作区噪声

判据：一对增删行去空白后相同（空白噪声），或去空白后仅差标点（标点噪声）。
整文件都是噪声 → 整文件还原；混合 → 逐行把噪声行换回旧版。
"""
import subprocess, re, os, sys, tempfile

ROOT = "/home/typhoeus/this"
PUNCT = "；;，,。.、：:！!？?（）()「」\"' \t　"


def unquote_path(p):
    p = p.strip()
    if p.startswith('"') and p.endswith('"'):
        body = p[1:-1]
        out = bytearray()
        i = 0
        while i < len(body):
            if body[i] == "\\" and i + 3 < len(body) and body[i + 1:i + 4].isdigit():
                out.append(int(body[i + 1:i + 4], 8))
                i += 4
            else:
                out.extend(body[i].encode("utf-8"))
                i += 1
        return out.decode("utf-8", errors="replace")
    return p


def norm(s):
    return re.sub(r"\s+", "", s)


def depunct(s):
    return "".join(ch for ch in norm(s) if ch not in PUNCT)


def is_noise(old, new):
    if not old.strip() or not new.strip():
        return True          # 空行增删同属噪声
    return norm(old) == norm(new) or depunct(old) == depunct(new)


def parse_diff(args):
    out = subprocess.run(["git", "diff", "-U0"] + args, capture_output=True, text=True, cwd=ROOT).stdout
    res, path, dels, adds = {}, None, [], []

    def flush():
        if path:
            for i in range(min(len(dels), len(adds))):
                res.setdefault(path, []).append((dels[i], adds[i]))
        dels.clear(); adds.clear()

    for line in out.split("\n"):
        if line.startswith("diff --git "):
            flush()
            continue
        if line.startswith("+++ "):
            flush()
            raw = unquote_path(line[4:])
            if raw.startswith("b/"):
                raw = raw[2:]
            path = raw
        elif line.startswith("--- "):
            continue
        elif line.startswith("-"):
            if adds:
                flush()
            dels.append(line[1:])
        elif line.startswith("+"):
            adds.append(line[1:])
        else:
            flush()
    flush()
    return res


def report(pairs):
    whole, partial = [], []
    for path, ps in pairs.items():
        if all(is_noise(o, n) for o, n in ps):
            whole.append(path)
        else:
            nz = [(o, n) for o, n in ps if is_noise(o, n)]
            if nz:
                partial.append((path, nz))
    return whole, partial


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "audit"
    if mode in ("audit", "revert"):
        pairs = parse_diff([sys.argv[2], sys.argv[3]])
    else:
        pairs = parse_diff([])
    whole, partial = report(pairs)
    print(f"模式 {mode}：涉及 {len(pairs)} 文件；纯噪声文件 {len(whole)}；混合文件 {len(partial)}"
          f"（噪声行 {sum(len(x[1]) for x in partial)}）")
    if mode.startswith("audit"):
        for p in whole[:12]:
            print("   [纯噪声]", p)
        for p, nz in partial[:6]:
            print(f"   [混合] {p}（{len(nz)} 行噪声）")
            for o, n in nz[:2]:
                print("        旧:", o[:120])
                print("        新:", n[:120])
        return
    # revert
    if whole:
        if mode == "revert":
            r = subprocess.run(["git", "checkout", sys.argv[2], "--"] + whole,
                               capture_output=True, text=True, cwd=ROOT)
        else:
            r = subprocess.run(["git", "checkout", "HEAD", "--"] + whole,
                               capture_output=True, text=True, cwd=ROOT)
        print("   整文件还原：", "OK" if r.returncode == 0 else r.stderr[:300])
    done = 0
    for path, nz in partial:
        fp = os.path.join(ROOT, path)
        if not os.path.exists(fp):
            continue
        s = open(fp, encoding="utf-8").read()
        n = 0
        for old, new in nz:
            if new and new in s:
                s = s.replace(new, old, 1)
                n += 1
        if n:
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(fp), suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as w:
                w.write(s)
            os.replace(tmp, fp)
            done += n
    print(f"   逐行还原噪声 {done} 行")


if __name__ == "__main__":
    main()
