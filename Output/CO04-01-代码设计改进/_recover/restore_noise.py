#!/usr/bin/env python3
"""还原两类无意义字符改动（相对给定提交的状态）：

1) 缩进/空白损坏：旧行与工作区行的去空白内容完全一致，只有空白不同 → 恢复旧行原样；
   对应地，把行尾分号统一去除，与库内既定惯例一致。
2) 行尾分号：行尾 `；` 是历史遗留写法，库内其他文档一律不加 → 统一去除。

用法：python3 restore_noise.py <ref> [--apply]
"""
import subprocess, re, os, sys, tempfile

ROOT = "/home/typhoeus/this"
REF = sys.argv[1] if len(sys.argv) > 1 else "812f7fe^"
APPLY = "--apply" in sys.argv


def norm(s):
    return re.sub(r"\s+", "", s)


def main():
    files = subprocess.run(["git", "diff", "--name-only", REF, "HEAD"],
                           capture_output=True, text=True, cwd=ROOT).stdout.split()
    # 合并区间内各提交的改动文件
    files += subprocess.run(["git", "diff", "--name-only", REF, "HEAD"],
                            capture_output=True, text=True, cwd=ROOT).stdout.split()
    files = [f for f in files if f.endswith(".md")]
    # 加上工作区未提交改动
    wt = subprocess.run(["git", "diff", "--name-only"], capture_output=True, text=True, cwd=ROOT).stdout.split()
    files = sorted(set(files) | set(wt))
    fixed_indent = fixed_semi = files_changed = 0
    for rel in files:
        fp = os.path.join(ROOT, rel)
        if not os.path.exists(fp):
            continue
        old = subprocess.run(["git", "show", f"{REF}:{rel}"],
                             capture_output=True, text=True, errors="replace", cwd=ROOT).stdout
        if not old:
            continue
        new = open(fp, encoding="utf-8").read()
        ol, nl = old.split("\n"), new.split("\n")
        # 以去空白键建立旧行索引（仅取唯一键）
        idx, dup = {}, set()
        for l in ol:
            k = norm(l)
            if not k:
                continue
            if k in idx:
                dup.add(k)
            else:
                idx[k] = l
        for k in dup:
            idx.pop(k, None)
        changed = False
        for i, l in enumerate(nl):
            k = norm(l)
            if not k:
                continue
            # 1) 缩进恢复
            if k in idx and idx[k] != l and norm(idx[k]) == k:
                nl[i] = idx[k]
                fixed_indent += 1
                changed = True
                l = nl[i]
            # 2) 行尾分号去除
            if l.rstrip().endswith("；"):
                nl[i] = l.rstrip()[:-1]
                fixed_semi += 1
                changed = True
        if changed:
            out = "\n".join(nl)
            if not out.strip() or len(out) < len(new) * 0.9:
                print("  守卫拒绝", rel)
                continue
            if APPLY:
                fd, tmp = tempfile.mkstemp(dir=os.path.dirname(fp), suffix=".tmp")
                with os.fdopen(fd, "w", encoding="utf-8") as w:
                    w.write(out)
                os.replace(tmp, fp)
            files_changed += 1
    print(f"{'APPLY' if APPLY else 'DRY'}（基线 {REF}）：恢复缩进 {fixed_indent} 行，去除行尾分号 {fixed_semi} 行，涉及 {files_changed} 份")


if __name__ == "__main__":
    main()
