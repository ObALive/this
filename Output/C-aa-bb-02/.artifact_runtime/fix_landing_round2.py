# -*- coding: utf-8 -*-
"""修正第二轮归档项的设计落点，并按库内归档表重新导出完整回答归档与新增归档增量。"""
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
    "XDM-GAP-017": "07-线索树与元进度/40-局末结算与写入/40_局末结算与写入设计_v2.5.md §3.3；新建 07-线索树与元进度/40-局末结算与写入/40_结算组件表_v1.csv；术语表新增结算组件表并修订结算组件、节点解锁检查组件；决策 66；交互逻辑 74",
    "XDM-GAP-018": "02-时间与事件/02_时间与事件索引_v1.13.md 事件片段说明；07-线索树与元进度/40-局末结算与写入 与 06-战斗/60-装备系统/60_装备系统设计_v7.2.md §4 的引述统一；术语表事件片段定义补充同义关系；决策 67；交互逻辑 75",
    "XDM-GAP-019": "07-线索树与元进度/40-局末结算与写入/40_局末结算与写入设计_v2.5.md §3.7、§3.9、§3.13；06-战斗/10-战斗总览/10_战斗总览设计_v4.2.md §3.2；06-战斗/A0-战斗目标与结果/A0_战斗目标与结果设计_v3.3.md §3.4；01-通用系统/20-信息传递系统/20_信息传递系统设计_v2.5.md §3.4；术语表新增未通关结局并登记死亡结局、失败结局为已移除术语；决策 68；交互逻辑 76；后续澄清见 XDM-GAP-021",
    "XDM-GAP-020": "本轮已按候选 B 处理：术语表结算组件定义与节点解锁检查组件定义改写并新增结算组件表条目；06-70 与 06-A0 的过期引用改写为不依赖版本的表述；决策 65；交互逻辑无新增",
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
            len(items), "、".join(pending) if pending else "无"),
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


round2 = [r for r in rows if r[0] in LANDING]
with io.open(os.path.join(OUTDIR, "C-aa-bb-02_回答归档_v2.md"), "w",
             encoding="utf-8", newline="") as fh:
    fh.write(render(round2, "C-aa-bb-02 回答归档（v2）",
                    "本轮归档 4 项（XDM-GAP-017 至 020），全部已裁定，其中采用候选 3 项、"
                    "自定义方案 1 项；归档后库内累计归档 %d 项。" % len(rows)))

with io.open(os.path.join(OUTDIR, "C-aa-bb-01_全部归档明细_v2.md"), "w",
             encoding="utf-8", newline="") as fh:
    fh.write(render(rows, "C-aa-bb-01 跨域遗留问题决策库 归档明细（v2）",
                    "库内累计归档 %d 项（第一轮 16 项加第二轮 4 项），主表保留第三轮 1 项。"
                    % len(rows)))

print(json.dumps({"更新落点": updated, "归档总数": len(rows), "主表": pending},
                 ensure_ascii=False))
