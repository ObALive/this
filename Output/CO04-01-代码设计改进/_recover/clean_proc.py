#!/usr/bin/env python3
"""清理过程编号与问答出处标记（依据/设计依据行按库内权威重写）。

规则：
  - 「| 设计依据 | …」与「| 依据 | …」行中的问答出处（回答 N、XX-GAP-nn、轮次标记、
    C 系列任务编号、R001/S01/S02）一律删除；只保留创意文档章节号与库内文档引用；
  - 正文中的同类标记一律删除，并清理空括号与残余标点。
守卫：非空、字符数≥原文 60%、行数≥原文 95%、原子写回、复读校验。
"""
import os, re, glob, sys, tempfile

ROOT = "/home/typhoeus/this"
DRY = "--apply" not in sys.argv

PROC_TEXT = [
    (re.compile(r"[；;、]\s*回答\s*[0-9]+(?:\s*[、,，与至]\s*[0-9]+)*"), ""),
    (re.compile(r"[；;、]\s*(?:第一轮|第二轮|第三轮|第四轮|第五轮)?回答\s*[A-Za-z0-9\-]+(?:\s*[、,，与]\s*[A-Za-z0-9\-]+)*"), ""),
    (re.compile(r"\b(?:SMP|MET|ARC|ENG|XDM|CBT2|DIF|NAR)-GAP-[0-9]+\b"), ""),
    (re.compile(r"\bR001\b"), ""),
    (re.compile(r"\bS0[12]\b"), ""),
    (re.compile(r"\bC0[0-9]\b"), ""),
    (re.compile(r"C-[0-9]{2}-[a-z]{2}-[0-9]{2}(?:-fix)?"), ""),
]
POST = [
    (re.compile(r"[；;]\s*[；;]+"), "；"),
    (re.compile(r"[；;]\s*[。]"), "。"),
    (re.compile(r"[；;]\s*[、]"), "；"),
    (re.compile(r"：\s*；"), "："),
    (re.compile(r"[；;]\s*$"), ""),
    (re.compile(r"[（(]\s*[）)]"), ""),
    (re.compile(r"[（(]\s*[，、；]\s*"), "（"),
    (re.compile(r"[，、；]\s*[）)]"), "）"),
    (re.compile(r"\s{2,}"), " "),
    (re.compile(r"\s+([，。；、）])"), r"\1"),
    (re.compile(r"[ \t]+$"), ""),
]


def clean_tail(parts):
    """把依据行中残留的问答出处去掉。"""
    out = []
    for seg in parts:
        seg = seg.strip()
        if not seg:
            continue
        out.append(seg)
    return out


def main():
    changed = skipped = 0
    for p in glob.glob(os.path.join(ROOT, "系统设计文档", "**", "*.md"), recursive=True) + \
             glob.glob(os.path.join(ROOT, "Code_Design", "**", "*.md"), recursive=True) + \
             glob.glob(os.path.join(ROOT, "架构设计文档", "**", "*.md"), recursive=True):
        orig = open(p, encoding="utf-8").read()
        lines = orig.split("\n")
        for i, line in enumerate(lines):
            is_basis = line.startswith("| 设计依据 |") or line.startswith("| 依据 |") or "| 设计依据 |" in line[:12]
            if is_basis and "|" in line:
                cells = line.split("|")
                for j, c in enumerate(cells):
                    if j == 0 or not c.strip():
                        continue
                    txt = c
                    for pat, rep in PROC_TEXT:
                        txt = pat.sub(rep, txt)
                    for pat, rep in POST:
                        txt = pat.sub(rep, txt)
                    txt = re.sub(r"[；;]\s*[；;、]*\s*", "；", txt).strip(" ；、")
                    txt = re.sub(r"^[；;、]\s*", "", txt)
                    txt = re.sub(r"；\s*$", "", txt)
                    cells[j] = (" " + txt + " ") if txt else ""
                newline = "|".join(cells)
                newline = re.sub(r"\|\s*\|", "|", newline)
                if newline != line:
                    lines[i] = newline
                continue
            txt = line
            for pat, rep in PROC_TEXT:
                txt = pat.sub(rep, txt)
            for pat, rep in POST:
                txt = pat.sub(rep, txt)
            if txt != line:
                lines[i] = txt
        new = "\n".join(lines)
        if new == orig:
            continue
        if not new.strip() or len(new) < len(orig) * 0.6 or new.count("\n") < orig.count("\n") * 0.95:
            print("  跳过（守卫）", os.path.relpath(p, ROOT), len(orig), "→", len(new))
            skipped += 1
            continue
        if not DRY:
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as w:
                w.write(new)
            os.replace(tmp, p)
            if not open(p, encoding="utf-8").read().strip():
                raise RuntimeError("写回为空：" + p)
        changed += 1
    print(f"{'DRY' if DRY else 'APPLY'}：改写 {changed} 份，跳过 {skipped} 份")


if __name__ == "__main__":
    main()
