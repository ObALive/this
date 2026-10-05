# -*- coding: utf-8 -*-
"""修正归档表的设计落点，并把归档明细导出为可读的结论文档。

归档脚本写入 landed_at 时使用的是缺口的关闭条件，本脚本按实际回填的设计稿改写该字段。
"""
import glob
import io
import json
import os
import sqlite3

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", ".."))
DB = glob.glob(os.path.join(ROOT, "Dsh", "Output", "C-aa-bb-01", "*决策库_v1.sqlite"))[0]

LANDING = {
    "XDM-GAP-001": "01-通用系统/40-角色与小队/40_角色与小队设计_v1.3.md §3.2；07-10 §3.2.1 与 3.7；决策 50；交互逻辑 65",
    "XDM-GAP-002": "07-线索树与元进度/10-线索树核心/10_线索树核心设计_v2.4.md §3.2.1；10_节点类型表_v2.csv 派生落点列；决策 51；交互逻辑 66",
    "XDM-GAP-003": "02-时间与事件/30-事件系统/30_事件系统设计_v4.3.md §4.6；决策 52；交互逻辑 72",
    "XDM-GAP-004": "07-线索树与元进度/40-局末结算与写入/40_局末结算与写入设计_v2.4.md §3.13、§3.14；决策 53",
    "XDM-GAP-005": "01-通用系统/40-角色与小队/40_角色与小队设计_v1.3.md §3.1；术语表新增主角；决策 54；交互逻辑 67",
    "XDM-GAP-006": "01-通用系统/40-角色与小队/40_角色与小队设计_v1.3.md §3.4；决策 55；交互逻辑 68",
    "XDM-GAP-007": "06-战斗/60-装备系统/60_装备系统设计_v7.2.md §4；物品操作总表 ITEM-EQP-001；决策 56；交互逻辑 69",
    "XDM-GAP-008": "07-线索树与元进度/40-局末结算与写入/40_局末结算与写入设计_v2.4.md §3.2、§3.3、§3.5、§3.6、§3.12；07-10 §3.11；01-50 §4；术语表新增结算组件、节点解锁检查组件；决策 57；交互逻辑 70；后续澄清见 XDM-GAP-017",
    "XDM-GAP-009": "05-运营与经济/05-物品系统/05_物品系统设计_v7.md §5.1；30_背包系统设计_v3.2.md §7；50_存档与持久化设计_v4.3.md §3、§4、§8；80_技能与库存联动设计_v6.2.md §5；物品操作总表三条记录；术语表新增落地物；决策 58；交互逻辑 71",
    "XDM-GAP-010": "07-线索树与元进度/40-局末结算与写入/40_局末结算与写入设计_v2.4.md §3.1；术语表关键行为摘要定义改写；决策 59",
    "XDM-GAP-011": "20-剪枝系统设计_v2.3.md §3.4；40_局末结算与写入设计_v2.4.md §3.5、§3.6；10_线索树核心设计_v2.4.md §3.5；决策 60；交互逻辑 70",
    "XDM-GAP-012": "01-通用系统/60-设置与辅助功能/60_设置与辅助功能设计_v1.5.md §2、§4；06-战斗/40-技能系统/40_技能系统设计_v4.2.md §3.2；01_通用系统索引_v1.15.md；术语表已移除术语；决策 61；交互逻辑 73",
    "XDM-GAP-013": "02-时间与事件/30-事件系统/30_事件系统设计_v4.3.md §4.11；10_金钱与货物设计_v4.2.md §4 与 §10；物品操作总表 ITEM-EVT-004；决策 62",
    "XDM-GAP-014": "05-运营与经济/05-物品系统/05_物品系统设计_v7.md §5.3；20_委托系统设计_v2.3.md §2.2 与 §5；决策 63",
    "XDM-GAP-015": "06-战斗/40-技能系统/40_技能系统设计_v4.2.md §4；70_遗物系统设计_v5.1.md §6；决策 64",
    "XDM-GAP-016": "本次已按候选 B 执行部分同步：00-总览、01 域、02 域、05 域、06 域与 07 域的索引、全景图、术语表与决策记录已更新；其余过期引用见 XDM-GAP-020；决策 65",
}

con = sqlite3.connect(DB)
cur = con.cursor()
updated = 0
for gap_id, landing in LANDING.items():
    cur.execute("UPDATE gaps_archived SET landed_at=? WHERE gap_id=?", (landing, gap_id))
    updated += cur.rowcount
cur.execute(
    "UPDATE gaps_archived SET conclusion='按 C-aa-bb-02 回答回填设计稿，落点见本行设计落点字段'"
    " WHERE gap_id LIKE 'XDM-GAP-%' AND (conclusion IS NULL OR conclusion='')")
con.commit()

rows = cur.execute(
    "SELECT gap_id, title, level, decision_status, chosen_label, chosen_title, answer_text,"
    " decision_basis, extra_requirement, conclusion, landed_at, archived_by, archived_at"
    " FROM gaps_archived ORDER BY gap_id").fetchall()
con.close()

header = [
    "# C-aa-bb-02 回答归档（v1）", "",
    "| 项目 | 内容 |", "| --- | --- |",
    "| 文档定位 | 汇总 C-aa-bb-01 决策库第一轮 16 项跨域遗留问题的裁定结论、理由与设计落点 |",
    "| 归档落点 | `Dsh/Output/C-aa-bb-01/C-aa-bb-01_跨域遗留问题决策库_v1.sqlite` 的 gaps_archived 表 |",
    "| 设计落点 | `Dsh/Design/` 下 01 至 07 域与 00-总览的现行文档 |",
    "| 主表状态 | 归档 16 项；主表保留第二轮新立的 4 项（XDM-GAP-017 至 020） |",
    "| 归档人 | C-aa-bb-02 |",
    "| 归档日期 | 2026-09-27 |", "",
    "共 16 项，全部已裁定。其中采用候选 8 项，自定义方案 8 项。", "",
    "---", "", "## 一、归档明细", "",
    "| 编号 | 原问题 | 等级 | 裁定方式 | 结论 | 裁定理由与补充要求 | 设计落点 |",
    "| --- | --- | --- | --- | --- | --- | --- |",
]
lines = list(header)
for (gap_id, title, level, status, label, chosen_title, answer, basis, extra, conclusion,
     landed, by, at) in rows:
    if status == "已选候选":
        conclusion_text = "采用%s：%s" % (label or "", chosen_title or "")
    else:
        conclusion_text = answer or ""
    note = "；".join(x for x in [basis, extra] if x) or "无"
    lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
        gap_id, title, level, status, conclusion_text.replace("\n", " "),
        note.replace("\n", " "), landed))

lines += [
    "", "## 二、变更记录", "",
    "| 版本 | 日期 | 变更 | 依据任务 |", "| --- | --- | --- | --- |",
    "| v1 | 2026-09-27 | 建立回答归档：16 项裁定的结论、理由与设计落点，修正归档表由关闭条件改写的设计落点 | C-aa-bb-02 |",
]

OUT = os.path.join(ROOT, "Dsh", "Output", "C-aa-bb-02", "C-aa-bb-02_回答归档_v1.md")
with io.open(OUT, "w", encoding="utf-8", newline="") as fh:
    fh.write("\n".join(lines) + "\n")

print("更新落点 %d 项，写出归档文档：%s" % (updated, OUT))
print(json.dumps({"archived": len(rows)}, ensure_ascii=False))
