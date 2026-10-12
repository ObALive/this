#!/usr/bin/env python3
"""清理过程编号被删后留下的语言残片，并恢复这些行的行尾分号。

残片形态（删除过程标记后遗留）：
  「任务书 ：」「任务书 -20-02：」「与 回答 ：」「回答 ：」「C-aa-bb-02 第二轮回答）」
  「关联 06-10、06-80，（…）」「来源：C-aa-bb-02 第二轮回答」
处理：删掉残片本身与相邻的多余标点/空格；若该行在基线中以「；」结尾，则补回。
"""
import subprocess, re, os, sys, difflib, tempfile

ROOT = "/home/typhoeus/this"
REF = sys.argv[1] if len(sys.argv) > 1 else "499941c"
APPLY = "--apply" in sys.argv

RESIDUE = [
    (re.compile(r"任务书\s*[、，]?\s*[：:]?\s*(?=[\u4e00-\u9fff])"), ""),
    (re.compile(r"任务书\s*$", re.M), ""),
    (re.compile(r"^\s*-\s*："), "-"),
    (re.compile(r"[与和、，]\s*回答\s*[、，]?\s*[：:]?"), ""),
    (re.compile(r"回答\s*第?[一二三四五六七八九十]*轮?\s*[、，]?\s*[：:]?"), ""),
    (re.compile(r"\bR001\b|\bS0[12]\b|\bC0\d\b"), ""),
    (re.compile(r"C-[0-9]{2}-[a-z]{2}-[0-9]{2}(?:-fix)?"), ""),
    (re.compile(r"\b(?:SMP|MET|ARC|ENG|XDM|CBT2)-GAP-[0-9]+\b"), ""),
    (re.compile(r"第[一二三四五六七八九十]+轮回答"), ""),
]
POST = [
    (re.compile(r"（\s*[、，；：]?\s*）"), ""),
    (re.compile(r"[（(]\s*[、，；：]\s*"), "（"),
    (re.compile(r"\s*[、，；]\s*[）)]"), "）"),
    (re.compile(r"[、，；]\s*[、，；]\s*"), "；"),
    (re.compile(r"[：:]\s*[、，；]\s*"), "："),
    (re.compile(r"第\s*[：:]"), ""),
    (re.compile(r"与\s*设计决策记录"), ""),
    (re.compile(r"^\s*-\s*[：:]\s*"), "- "),
    (re.compile(r"\s+([，。；、：）])"), r"\1"),
    (re.compile(r"任务书\s*[：:]\s*(?=[\u4e00-\u9fff])"), "任务书："),
    (re.compile(r"[ \t]+$"), ""),
]


def norm(s):
    return re.sub(r"\s+", "", s)


def changed_files():
    out = subprocess.run(["git", "diff", "--name-only", "-z", REF, "HEAD"],
                         capture_output=True, cwd=ROOT).stdout.decode("utf-8").split("\0")
    out += subprocess.run(["git", "diff", "--name-only", "-z", "HEAD"],
                          capture_output=True, cwd=ROOT).stdout.decode("utf-8").split("\0")
    return sorted({f for f in out if f and f.endswith(".md")})


def main():
    fixed_lines = fixed_semi = files_touched = 0
    for rel in changed_files():
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        old = subprocess.run(["git", "show", f"{REF}:{rel}"], capture_output=True,
                             cwd=ROOT).stdout.decode("utf-8", "replace")
        new = open(path, encoding="utf-8").read()
        if not old or old == new:
            continue
        nl = new.split("\n")
        ol = old.split("\n")
        sm = difflib.SequenceMatcher(None, ol, nl)
        # 基线行索引（去空白键）
        base = {}
        for l in ol:
            k = norm(l)
            if k:
                base.setdefault(k, l)
        n_line = n_semi = 0
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            for k, (a, b) in enumerate(zip(ol[i1:i2], nl[j1:j2])):
                orig = b
                t = b
                for pat, rep in RESIDUE:
                    t = pat.sub(rep, t)
                for pat, rep in POST:
                    t = pat.sub(rep, t)
                t = re.sub(r"[、，；]{2,}", "；", t)
                t = re.sub(r"[：:]\s*。", "。", t)
                t = re.sub(r"^(\s*-\s*)：", r"\1", t)
                # 该基线行以分号结尾 → 补回
                if a.rstrip().endswith("；") and not t.rstrip().endswith(("；", "。")):
                    t = t.rstrip() + "；"
                    n_semi += 1
                if t != orig:
                    nl[j1 + k] = t
                    n_line += 1
        if n_line:
            out = "\n".join(nl)
            if not out.strip() or len(out) < len(new) * 0.95:
                print("  守卫拒绝", rel)
                continue
            if APPLY:
                fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
                with os.fdopen(fd, "w", encoding="utf-8") as w:
                    w.write(out)
                os.replace(tmp, path)
            fixed_lines += n_line
            fixed_semi += n_semi
            files_touched += 1
    print(f"{'APPLY' if APPLY else 'DRY'}：修复残片 {fixed_lines} 行（其中补回行尾分号 {fixed_semi} 行），涉及 {files_touched} 份")


if __name__ == "__main__":
    main()
