# -*- coding: utf-8 -*-
"""回填后一致性检查：文件名与文内版本号、文档间引用可解析、库内状态。"""
import glob
import io
import os
import re
import sqlite3

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", ".."))
DESIGN = os.path.join(ROOT, "Dsh", "Design")

problems = []

# 1 文件名版本号与文内版本号一致
for base, dirs, files in os.walk(DESIGN):
    if "归档" in base or "_模板" in base:
        continue
    for name in files:
        if not name.endswith(".md"):
            continue
        m = re.search(r"_v(\d+(?:\.\d+)?)\.md$", name)
        if not m:
            continue
        file_ver = m.group(1)
        text = io.open(os.path.join(base, name), encoding="utf-8").read()
        head = re.search(r"^#\s+(.+?)（v(\d+(?:\.\d+)?)）", text, re.M)
        meta = re.search(r"\|\s*版本\s*\|\s*v(\d+(?:\.\d+)?)\s*\|", text)
        if head and head.group(2) != file_ver:
            problems.append("标题版本不一致：%s（文件 v%s / 标题 v%s）"
                            % (os.path.relpath(os.path.join(base, name), ROOT),
                               file_ver, head.group(2)))
        if meta and meta.group(1) != file_ver:
            problems.append("元信息版本不一致：%s（文件 v%s / 元信息 v%s）"
                            % (os.path.relpath(os.path.join(base, name), ROOT),
                               file_ver, meta.group(1)))

# 2 文档间引用可解析（跳过归档目录与历史版本文件本身的引用）
DOC_REF = re.compile(r"`([0-9_][^`]*?\.(?:md|csv))`")
missing = 0
for base, dirs, files in os.walk(DESIGN):
    if "归档" in base or "_模板" in base:
        continue
    for name in files:
        if not name.endswith(".md"):
            continue
        path = os.path.join(base, name)
        text = io.open(path, encoding="utf-8").read()
        for ref in set(DOC_REF.findall(text)):
            if ref.startswith("Dsh/"):
                candidates = [os.path.join(ROOT, ref.replace("/", os.sep))]
            else:
                parts = ref.split("/", 1)
                candidates = [os.path.join(base, ref.replace("/", os.sep))]
                if len(parts) == 2:
                    candidates.append(os.path.join(DESIGN, ref.replace("/", os.sep)))
                    candidates.append(os.path.join(
                        os.path.dirname(base), ref.replace("/", os.sep)))
                else:
                    candidates.append(os.path.join(DESIGN, ref))
            if not any(os.path.exists(c) for c in candidates):
                missing += 1
                problems.append("引用缺失：%s -> %s"
                                % (os.path.relpath(path, ROOT), ref))

# 3 库内状态
DB = glob.glob(os.path.join(ROOT, "Dsh", "Output", "C-aa-bb-01", "*决策库_v1.sqlite"))[0]
con = sqlite3.connect("file:///%s?mode=ro" % DB.replace("\\", "/"), uri=True)
state = {
    "主表待裁定": con.execute("SELECT COUNT(*) FROM gaps").fetchone()[0],
    "归档": con.execute("SELECT COUNT(*) FROM gaps_archived").fetchone()[0],
    "落点为空的归档项": con.execute(
        "SELECT COUNT(*) FROM gaps_archived WHERE landed_at IS NULL OR TRIM(landed_at)=''"
    ).fetchone()[0],
}
con.close()

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "consistency_report.txt")
with io.open(out, "w", encoding="utf-8") as fh:
    fh.write("问题数：%d（引用缺失 %d）\n\n" % (len(problems), missing))
    fh.write("\n".join(problems) if problems else "无")
    fh.write("\n\n库内状态：\n")
    for k, v in state.items():
        fh.write("  %s = %s\n" % (k, v))
print("wrote", out, "problems", len(problems), "missing_refs", missing)
for k, v in state.items():
    print("  %s = %s" % (k, v))
