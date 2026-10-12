#!/usr/bin/env python3
"""还原「无意义的字符级改动」。

对给定提交区间，逐文件判断：
  * 该文件的全部改动对都满足「去空白后相同」或「去标点后相同」→ 整文件还原为改动前版本；
  * 文件中既有实义改动又有噪声对 → 逐行还原噪声对（把新行换回旧行）。
输出：还原的文件数、还原的行数、保留的实义改动文件数。
"""
import subprocess, re, sys, os, tempfile

ROOT = "/home/typhoeus/this"
PUNCT = "；;，,。.、：:！!？?（）()「」\"' \t　"


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


def is_noise(old, new):
    if not old.strip() or not new.strip():
        return False
    return norm(old) == norm(new) or depunct(old) == depunct(new)


def diff_pairs(rev_old, rev_new):
    """返回 {path: [(old,new), ...]}，以 rev_old→rev_new 的 diff 为准。"""
    out = subprocess.run(["git", "diff", "-U0", rev_old, rev_new],
                         capture_output=True, text=True, cwd=ROOT).stdout
    res = {}
    path = None
    dels, adds = [], []

    def flush():
        if path and (dels or adds):
            res.setdefault(path, []).extend(zip(dels[:], adds[:]))
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
    rev_old, rev_new = sys.argv[1], sys.argv[2]
    apply = "--apply" in sys.argv
    pairs = diff_pairs(rev_old, rev_new)
    whole, partial = [], []
    for path, ps in pairs.items():
        if not ps:
            continue
        if all(is_noise(o, n) for o, n in ps):
            whole.append(path)
        else:
            nz = [(o, n) for o, n in ps if is_noise(o, n)]
            if nz:
                partial.append((path, nz))
    print(f"{rev_old}→{rev_new}：涉及 {len(pairs)} 文件")
    print(f"  纯噪声文件（整文件还原）：{len(whole)}")
    print(f"  混合文件（逐行还原噪声对）：{len(partial)}，噪声行 {sum(len(x[1]) for x in partial)}")
    if not apply:
        print("\n--- 纯噪声文件示例（前 10）")
        for p in whole[:10]:
            print("   ", p)
        print("--- 混合文件示例（前 5）")
        for p, nz in partial[:5]:
            print(f"    {p}（{len(nz)} 行噪声）")
            for o, n in nz[:2]:
                print("       旧:", o[:110])
                print("       新:", n[:110])
        return
    # 整文件还原
    if whole:
        r = subprocess.run(["git", "checkout", rev_old, "--"] + whole,
                           capture_output=True, text=True, cwd=ROOT)
        print("  git checkout 还原：", "OK" if r.returncode == 0 else r.stderr[:200])
    # 逐行还原
    for path, nz in partial:
        fp = os.path.join(ROOT, path)
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
        print(f"  {path}：还原 {n}/{len(nz)} 行")


if __name__ == "__main__":
    main()
