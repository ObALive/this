# -*- coding: utf-8 -*-
"""从归档表重建回答归档 Markdown（归档后主表为空，dump_decisions 不再覆盖归档内容）。"""
import sqlite3, io, json, os, time
DB = "Output/R001/R001_系统设计精简缺口决策库_v1.sqlite"
SRC = "Output/R001/.artifact_runtime/decisions_round1.json"
OUT = "Output/R001/R001_回答归档_v1.md"
rounds = {g["gap_id"]: g for g in json.load(io.open(SRC, encoding="utf-8"))["gaps"]}

conn = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
conn.row_factory = sqlite3.Row
rows = conn.execute("""SELECT * FROM gaps_archived ORDER BY gap_id""").fetchall()
out = []
out.append("# R001 回答归档（第一轮）\n")
out.append("| 项目 | 内容 |")
out.append("| --- | --- |")
out.append("| 文档定位 | 第一轮全部缺口的裁定凭证：每条给出裁定方式、采纳结论、补充要求与设计落点 |")
out.append("| 数据来源 | `%s` 的归档表 |" % DB)
out.append("| 归档任务 | R001 |")
out.append("| 归档项数 | %d |" % len(rows))
out.append("| 归档时间 | %s |" % (rows[0]["archived_at"] if rows else ""))
out.append("| 导出时间 | %s |" % time.strftime("%Y-%m-%d %H:%M:%S"))
out.append("")
out.append("---")
out.append("")
for r in rows:
    src = rounds.get(r["gap_id"], {})
    dec = src.get("decision", {})
    out.append("## %s %s" % (r["gap_id"], r["title"]))
    out.append("")
    out.append("| 项目 | 内容 |")
    out.append("| --- | --- |")
    out.append("| 等级 | %s |" % r["level"])
    out.append("| 责任方 | %s |" % r["owner"])
    out.append("| 优先轮次 | %s |" % (r["priority_round"] or ""))
    out.append("| 裁定方式 | %s |" % r["decision_status"])
    out.append("| 采纳结论 | %s |" % (r["conclusion"] or ""))
    out.append("| 裁定时间 | %s |" % (r["filled_at"] or ""))
    if (r["extra_requirement"] or "").strip():
        out.append("| 补充要求 | %s |" % r["extra_requirement"].strip())
    if (r["decision_basis"] or "").strip():
        out.append("| 裁定理由 | %s |" % r["decision_basis"].strip())
    out.append("| 设计落点 | %s |" % (r["landed_at"] or ""))
    out.append("")
    body = (dec.get("chosen_detail") or "").strip() if r["decision_status"] == "已选候选" else (r["answer_text"] or "").strip()
    if body:
        out.append("裁定正文：%s" % body)
        out.append("")
    out.append("")
io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(out).rstrip("\n") + "\n")
print("已重建归档凭证：%s，%d 条" % (OUT, len(rows)))
conn.close()
