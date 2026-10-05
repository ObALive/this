# -*- coding: utf-8 -*-
"""只读检查：读出 C-aa-bb-01 决策库当前的裁定状态。"""
import glob
import io
import os
import sqlite3

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", ".."))
DB = glob.glob(os.path.join(ROOT, "Dsh", "Output", "C-aa-bb-01", "*决策库_v1.sqlite"))[0]
con = sqlite3.connect("file:///%s?mode=ro" % DB.replace("\\", "/"), uri=True)
cur = con.cursor()

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "current_state.txt")
lines = []
lines.append("库：%s" % DB)
lines.append("gaps=%d archived=%d" % (
    cur.execute("SELECT COUNT(*) FROM gaps").fetchone()[0],
    cur.execute("SELECT COUNT(*) FROM gaps_archived").fetchone()[0]))
lines.append("")
lines.append("== 主表 ==")
for r in cur.execute("SELECT gap_id, level, status, title FROM gaps ORDER BY gap_id"):
    lines.append(" | ".join(str(x) for x in r))
lines.append("")
lines.append("== 裁定表 ==")
for r in cur.execute("SELECT gap_id, status, chosen_option_id, answer_text, decision_basis,"
                     " extra_requirement, decided_by, decided_date, needs_followup"
                     " FROM decisions ORDER BY gap_id"):
    lines.append(" | ".join("" if x is None else str(x).replace("\n", "\\n") for x in r))
lines.append("")
lines.append("== meta ==")
for r in cur.execute("SELECT key, value FROM meta ORDER BY key"):
    lines.append(" | ".join(str(x) for x in r))

with io.open(out, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
con.close()
print("wrote", out, "lines", len(lines))
