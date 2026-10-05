# -*- coding: utf-8 -*-
"""从 Git HEAD 取回被本任务修改或删除的文档，作为修改前快照归档。"""
import io
import os
import subprocess

REPO = r"D:\myspace\Git\mygame"
SNAP = r"D:\myspace\Git\mygame\Dsh\Output\C-06-bb-02\归档\Design"


def git(*args, binary=False):
    out = subprocess.run(["git"] + list(args), cwd=REPO, capture_output=True)
    if out.returncode != 0:
        return None
    return out.stdout if binary else out.stdout.decode("utf-8")


def main():
    listing = git("-c", "core.quotepath=false", "status", "--porcelain", "Dsh/Design")
    if not listing:
        print("没有检测到改动")
        return
    saved = 0
    skipped = []
    for line in listing.splitlines():
        if len(line) < 4:
            continue
        code, path = line[:2].strip(), line[3:].strip().strip('"')
        if code not in ("M", "D", "MM", "R"):
            continue
        blob = git("show", "HEAD:" + path, binary=True)
        if blob is None:
            skipped.append(path)
            continue
        rel = path.split("Dsh/Design/", 1)[1]
        dst = os.path.join(SNAP, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as fh:
            fh.write(blob)
        saved += 1
        print("%-64s %d 字节" % (rel, len(blob)))
    print("\n共归档修改前版本:", saved)
    if skipped:
        print("跳过:", skipped)


if __name__ == "__main__":
    main()
