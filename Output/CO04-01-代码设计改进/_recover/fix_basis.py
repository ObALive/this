#!/usr/bin/env python3
"""修复被清理后残缺的「设计依据 / 依据」行：只保留完整的上游出处，残片一律剔除。

保留规则（逐段判定）：
  - 含「创意文档 / 创意需求文档」且后接章节号的段：保留；
  - 含「战斗与装备的增量设计思路 / 战斗增量思路」：保留（去掉后续残片）；
  - 含库内文档路径（`xx/yy设计.md` 或 `Code_Design/`、`架构设计文档/`）：保留；
  - 其余（回答 N、GAP 编号、任务编号、孤立数字、空段）一律丢弃。
行尾若只剩空内容，写为统一的现行依据表述。
"""
import os, re, glob, sys, tempfile

ROOT = "/home/typhoeus/this"
DRY = "--apply" not in sys.argv
GOOD = re.compile(r"(创意(?:需求)?文档\s*§|战斗(?:与装备)?的?增量设计思路|增量思路|Code_Design/|架构设计文档/|系统设计文档/|`[^`]*设计\.md`|用户\s*20\d\d-\d\d-\d\d)")
FALLBACK = "创意需求文档的对应章节；本库的设计稿与架构设计案"

BAD_SEG = re.compile(r"^(?:[0-9]+(?:[、,，]\s*[0-9]+)*|第[一二三四五六七八九十]+轮|回答|裁定|任务书|、|；|。)*$")


def good_seg(seg):
    seg = seg.strip(" ；、。")
    if not seg:
        return False
    if BAD_SEG.match(seg):
        return False
    if any(x in seg for x in ("回答", "裁定", "任务书", "回答", "轮")):
        # 允许含「裁定」但必须另有完整出处
        if not GOOD.search(seg):
            return False
    if not GOOD.search(seg):
        return False
    # 段尾不得是孤立数字或标点
    if re.search(r"[0-9]+$", seg) and "§" not in seg and "设计" not in seg:
        seg = re.sub(r"[；;、,，]?\s*[0-9]+$", "", seg)
    return bool(seg.strip(" ；、。"))


def fix_cell(cell):
    parts = re.split(r"[；;]", cell)
    keep = []
    for p in parts:
        p = p.strip()
        if good_seg(p):
            keep.append(re.sub(r"[（(][^（）()]*?[）)]", "", p).strip(" ；、。"))
    keep = [k for k in keep if k]
    if not keep:
        return FALLBACK
    # 去重
    out = []
    for k in keep:
        if k not in out:
            out.append(k)
    return "；".join(out)


def main():
    changed = 0
    for root in ["系统设计文档", "Code_Design", "架构设计文档"]:
        for p in glob.glob(os.path.join(ROOT, root, "**", "*.md"), recursive=True):
            orig = open(p, encoding="utf-8").read()
            lines = orig.split("\n")
            for i, line in enumerate(lines):
                if not (line.startswith("| 设计依据 |") or line.startswith("| 依据 |")):
                    continue
                cells = line.split("|")
                for j, c in enumerate(cells):
                    if j < 2 or not c.strip():
                        continue
                    cells[j] = " " + fix_cell(c) + " "
                newline = "|".join(cells)
                if newline != line:
                    lines[i] = newline
            new = "\n".join(lines)
            if new == orig:
                continue
            if not new.strip() or len(new) < len(orig) * 0.9:
                print("  跳过", os.path.relpath(p, ROOT), len(orig), "→", len(new))
                continue
            if not DRY:
                fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), suffix=".tmp")
                with os.fdopen(fd, "w", encoding="utf-8") as w:
                    w.write(new)
                os.replace(tmp, p)
            changed += 1
    print(f"{'DRY' if DRY else 'APPLY'}：修复 {changed} 份")


if __name__ == "__main__":
    main()
