# -*- coding: utf-8 -*-
"""只读复核：打印候选表的推荐标记原始数据。"""
import glob
import io
import os
import sqlite3

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", ".."))
DB = glob.glob(os.path.join(ROOT, "Dsh", "Output", "C-aa-bb-01", "*决策库_v1.sqlite"))[0]
con = sqlite3.connect("file:///%s?mode=ro" % DB.replace("\\", "/"), uri=True)
rows = con.execute("SELECT gap_id, option_label, is_recommended, is_custom"
                   " FROM solution_options ORDER BY gap_id, seq").fetchall()
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recommend_flags.txt")
with io.open(out, "w", encoding="utf-8") as fh:
    for r in rows:
        fh.write("%s | %s | rec=%s | custom=%s\n" % r)
con.close()
print("wrote", out, "rows", len(rows))
