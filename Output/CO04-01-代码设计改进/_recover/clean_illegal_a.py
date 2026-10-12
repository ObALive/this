#!/usr/bin/env python3
"""清理三个设计库内的非法外部引用（Task/Output/Report/Input/Tool/Dsh）。

规则：三库最多只引用自身与上游文档（系统设计 → 架构设计 → 代码设计）。
对「删除后不能完备描述现版本正文」的引用，把被引内容的实质搬入本处。

安全：逐文件读入 → 替换 → 守卫（非空、字符数≥原文 80%）→ 原子写回 → 复读校验。
"""
import os, re, sys, glob, tempfile

ROOT = "/home/typhoeus/this"
DRY = "--apply" not in sys.argv


def guard_ok(orig, new):
    if not new.strip():
        return False
    if len(new) < len(orig) * 0.80:
        return False
    if new.count("\n") < orig.count("\n") * 0.95:
        return False
    return True


def apply_file(p, fn):
    orig = open(p, encoding="utf-8").read()
    new = fn(orig)
    if new == orig:
        return False, "无变化"
    if not guard_ok(orig, new):
        return False, f"守卫拒绝 {len(orig)}→{len(new)}"
    if DRY:
        return True, "干跑"
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as w:
        w.write(new)
    os.replace(tmp, p)
    back = open(p, encoding="utf-8").read()
    if not back.strip():
        raise RuntimeError("写回后为空：" + p)
    return True, f"改写 {len(orig)}→{len(new)}"


def rx(pattern, repl):
    pat = re.compile(pattern)

    def f(s):
        return pat.sub(repl, s)
    return f


TASKS = []

# 一、代码设计案的单元说明/分工说明：删除对编制约定的引用，保留角色陈述
GENERIC = re.compile(r"[（(]按\s*`?Output/CO01-初步构建代码设计文档/CO01_编制约定_v1\.md`?\s*§[一二三四五六七八九十\.0-9]*[^（）()]*[）)]")
GENERIC2 = re.compile(r"本文档按《CO01 编制约定 v1》§[一二三四五六七八九十\.0-9]*")
GENERIC3 = re.compile(r"\s*[（(]按\s*`?Output/CO03-需求调整1/CO03_回填执行约定_v1\.md`?[^（）()]*[）)]")


def clean_preamble(s):
    s = GENERIC.sub("", s)
    s = GENERIC2.sub("本文档", s)
    s = GENERIC3.sub("", s)
    s = re.sub(r"[（(]\s*[）)]", "", s)
    return s


for p in glob.glob(os.path.join(ROOT, "Code_Design", "**", "*.md"), recursive=True):
    TASKS.append((p, clean_preamble))


def run():
    changed = skipped = 0
    for p, fn in TASKS:
        try:
            did, why = apply_file(p, fn)
        except Exception as e:
            print("  错误", p, e)
            skipped += 1
            continue
        if did:
            changed += 1
        else:
            skipped += 1
    print(f"{'DRY' if DRY else 'APPLY'}：改写 {changed} 份，未变/跳过 {skipped} 份")


if __name__ == "__main__":
    run()
