# -*- coding: utf-8 -*-
"""修正第三轮归档项的设计落点，并导出回答归档 v3 与全部归档明细 v3。"""
import glob
import io
import json
import os
import sqlite3

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", ".."))
DB = glob.glob(os.path.join(ROOT, "Dsh", "Output", "C-aa-bb-01", "*决策库_v1.sqlite"))[0]
OUTDIR = os.path.join(ROOT, "Dsh", "Output", "C-aa-bb-02")

LANDING = {
    "XDM-GAP-021": "07-线索树与元进度/40-局末结算与写入/40_局末结算与写入设计_v2.6.md §3.7、§3.13；07-线索树与元进度/40-局末结算与写入/40_结算组件表_v1.csv 新增达成记录与大关进度组件；术语表新增触发起因、达成记录与大关进度组件；决策 69；交互逻辑 77",
}

con = sqlite3.connect(DB)
cur = con.cursor()
updated = 0
for gap_id, landing in LANDING.items():
    cur.execute("UPDATE gaps_archived SET landed_at=? WHERE gap_id=?", (landing, gap_id))
    updated += cur.rowcount
con.commit()
rows = cur.execute(
    "SELECT gap_id, title, level, decision_status, chosen_label, chosen_title, answer_text,"
    " decision_basis, extra_requirement, conclusion, landed_at"
    " FROM gaps_archived ORDER BY gap_id").fetchall()
pending = [r[0] for r in cur.execute("SELECT gap_id FROM gaps ORDER BY gap_id")]
con.close()


def render(items, title, note):
    lines = [
        "# %s" % title, "",
        "| 项目 | 内容 |", "| --- | --- |",
        "| 文档定位 | 汇总 C-aa-bb-01 决策库中已裁定问题的结论、理由与设计落点 |",
        "| 归档落点 | `Dsh/Output/C-aa-bb-01/C-aa-bb-01_跨域遗留问题决策库_v1.sqlite` 的 gaps_archived 表 |",
        "| 设计落点 | `Dsh/Design/` 下 00-总览与 01 至 07 域的现行文档 |",
        "| 主表状态 | 归档 %d 项；主表保留 %s |" % (
            len(items), "、".join(pending) if pending else "无，主表已清零"),
        "| 归档人 | C-aa-bb-02 |", "| 归档日期 | 2026-09-27 |", "",
        note, "", "---", "", "## 一、归档明细", "",
        "| 编号 | 原问题 | 等级 | 裁定方式 | 结论 | 裁定理由与补充要求 | 设计落点 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for (gap_id, gap_title, level, status, label, chosen_title, answer, basis, extra,
         conclusion, landed) in items:
        if status == "已选候选":
            conclusion_text = "采用%s：%s" % (label or "", chosen_title or "")
        else:
            conclusion_text = answer or ""
        note_text = "；".join(x for x in [basis, extra] if x) or "无"
        lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            gap_id, gap_title, level, status,
            conclusion_text.replace("\n", " "), note_text.replace("\n", " "), landed))
    lines += [
        "", "## 二、变更记录", "",
        "| 版本 | 日期 | 变更 | 依据任务 |", "| --- | --- | --- | --- |",
        "| v1 | 2026-09-27 | %s | C-aa-bb-02 |" % note,
    ]
    return "\n".join(lines) + "\n"


round3 = [r for r in rows if r[0] in LANDING]
with io.open(os.path.join(OUTDIR, "C-aa-bb-02_回答归档_v3.md"), "w",
             encoding="utf-8", newline="") as fh:
    fh.write(render(round3, "C-aa-bb-02 回答归档（v3）",
                    "本轮归档 1 项（XDM-GAP-021），采用候选 A；归档后库内累计归档 %d 项，主表清零。"
                    % len(rows)))

with io.open(os.path.join(OUTDIR, "C-aa-bb-01_全部归档明细_v3.md"), "w",
             encoding="utf-8", newline="") as fh:
    fh.write(render(rows, "C-aa-bb-01 跨域遗留问题决策库 归档明细（v3）",
                    "库内累计归档 %d 项（第一轮 16 项、第二轮 4 项、第三轮 1 项），主表无待裁定项。"
                    % len(rows)))

print(json.dumps({"更新落点": updated, "归档总数": len(rows), "主表": pending},
                 ensure_ascii=False))
