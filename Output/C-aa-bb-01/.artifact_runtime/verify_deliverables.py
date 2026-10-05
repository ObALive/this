# -*- coding: utf-8 -*-
"""只读复核：核对决策库内容与分析文档的一致性，并模拟填写器的读取。"""
import io
import json
import os
import re
import sqlite3

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
DB = os.path.join(ROOT, "Dsh", "Output", "C-aa-bb-01",
                  "C-aa-bb-01_跨域遗留问题决策库_v1.sqlite")
DOC = os.path.join(ROOT, "Dsh", "Output", "C-aa-bb-01",
                   "C-aa-bb-01_跨域遗留问题信息缺口分析_v1.md")

con = sqlite3.connect("file:///%s?mode=ro" % DB.replace("\\", "/"), uri=True)
print("库路径：", DB, os.path.exists(DB))
cur = con.cursor()
rows = cur.execute(
    "SELECT g.gap_id, g.level, g.status, COUNT(o.option_id),"
    " SUM(CASE WHEN o.is_recommended=1 THEN 1 ELSE 0 END)"
    " FROM gaps g LEFT JOIN solution_options o"
    " ON o.gap_id=g.gap_id AND o.is_custom=0 GROUP BY g.gap_id ORDER BY g.gap_id"
).fetchall()
print("库内缺口 %d 项：" % len(rows))
for r in rows:
    print("  %-13s %-3s %-6s 候选 %d 推荐 %s" % r)
print("视图 v_gap_decision 待裁定：",
      cur.execute("SELECT COUNT(*) FROM v_gap_decision WHERE decision_status='待裁定'").fetchone()[0])
con.close()

text = io.open(DOC, encoding="utf-8").read()
doc_ids = sorted(set(re.findall(r"XDM-GAP-\d{3}", text)))
db_ids = sorted(r[0] for r in rows)
print("文档编号 %d 个，库内编号 %d 个，一致：%s" % (len(doc_ids), len(db_ids), doc_ids == db_ids))

data = json.load(io.open(os.path.join(ROOT, "Dsh", "Output", "C-aa-bb-01",
                                      "C-aa-bb-01_决策库数据_v1.json"), encoding="utf-8"))
print("数据文件 db_path：", data["db_path"])
print("数据文件缺口数：", len(data["gaps"]))
missing = [g["gap_id"] for g in data["gaps"] if not g["options"] and g["status"] != "开放填写"]
print("候选为空但状态不是开放填写的项：", missing)
