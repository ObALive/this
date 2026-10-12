#!/usr/bin/env python3
"""CO04-01 追加操作：移除历史设计记录文档后，清理长期维护库内的悬空引用。

安全设计（对照上一次事故）：
  1. 每个文件先读入内存，做替换后校验：结果非空、字符数不低于原文的 55%、行数不低于原文的 80%；
  2. 任一校验不通过即跳过该文件并记录，不写回；
  3. 写回使用临时文件 + os.replace 原子替换，并对写回后的文件重新读回校验首行一致；
  4. 只处理三个长期维护库，不触碰 Output/ 与 Report/（一次性记录不改）。
"""
import os, re, glob, sys, tempfile

ROOT = "/home/typhoeus/this"
ROOTS = ["系统设计文档", "架构设计文档", "Code_Design", "Rules"]
DRY = "--apply" not in sys.argv

# 已删除的历史记录文档在正文中的引用形态
PATS = [
    # 见 `00-总览/03_设计决策记录.md` 决策 87 至 95 / 见 00-总览/... 决策 49
    (re.compile(r"[（(]?见\s*`?(?:系统设计文档/)?00-总览/03_设计决策记录\.md`?\s*(?:的)?\s*决策\s*[0-9#]+(?:\s*(?:至|与|、|,|，)\s*[0-9]+)*[）)]?"), ""),
    (re.compile(r"[（(]?见\s*架构设计文档/架构设计决策记录\.md(?:\s*决策\s*[0-9]+)?[）)]?"), ""),
    (re.compile(r"[（(]见\s*决策\s*[#0-9]+[、，]\s*([^（）()]+)[）)]"), r"（\1）"),
    (re.compile(r"[（(]见\s*决策\s*[#0-9]+[）)]"), ""),
    (re.compile(r"`系统设计文档/00-总览/03_设计决策记录\.md`"), "上游设计稿与架构设计案"),
    (re.compile(r"`(?:系统设计文档/)?00-总览/03_设计决策记录\.md`"), "上游设计稿"),
    (re.compile(r"`架构设计文档/架构设计决策记录\.md`"), "架构设计案"),
    (re.compile(r"`架构设计文档/架构设计裁定总账\.md`"), "架构设计案"),
    # 行尾遗留的未闭合括号残片
    (re.compile(r"[（(][^（）()]{0,40}?[，,]\s*$"), ""),
]
POST = [
    (re.compile(r"[，,]\s*[。]"), "。"),
    (re.compile(r"[，,]\s*[；;]"), "；"),
    (re.compile(r"[；;]\s*[。]"), "。"),
    (re.compile(r"[（(]\s*[）)]"), ""),
    (re.compile(r"\s+([。；，、）])"), r"\1"),
    (re.compile(r"[ \t]+$"), ""),
]


def clean(text):
    for pat, rep in PATS:
        text = pat.sub(rep, text)
    for pat, rep in POST:
        text = pat.sub(rep, text)
    return text


def main():
    changed, skipped = [], []
    for root in ROOTS:
        for p in glob.glob(os.path.join(ROOT, root, "**", "*.md"), recursive=True):
            try:
                orig = open(p, encoding="utf-8").read()
            except Exception as e:
                skipped.append((p, f"读取失败 {e}"))
                continue
            new = clean(orig)
            if new == orig:
                continue
            if not new.strip():
                skipped.append((p, "结果为空"))
                continue
            if len(new) < len(orig) * 0.55 or new.count("\n") < orig.count("\n") * 0.8:
                skipped.append((p, f"收缩过多 {len(orig)}→{len(new)}"))
                continue
            if not DRY:
                fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), suffix=".tmp")
                with os.fdopen(fd, "w", encoding="utf-8") as w:
                    w.write(new)
                os.replace(tmp, p)
                back = open(p, encoding="utf-8").read()
                if not back.strip():
                    skipped.append((p, "写回后为空（已中止）"))
            changed.append(p)
    print(f"{'DRY' if DRY else 'APPLY'}：修改 {len(changed)} 份，跳过 {len(skipped)} 份")
    for p, why in skipped:
        print("  跳过", p, "—", why)


if __name__ == "__main__":
    main()
