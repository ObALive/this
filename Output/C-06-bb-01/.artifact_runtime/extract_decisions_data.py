# -*- coding: utf-8 -*-
"""把 C-06-bb-01 决策库的内容提取为结构化数据文件。

提取范围：
  主表 gaps（当前未澄清问题）与归档表 gaps_archived（已澄清问题）中的缺口元数据；
  候选方案取自主表的 solution_options。

产物：Dsh/Output/C-06-bb-01/decisions_data.json
"""
import io
import json
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.abspath(os.path.join(HERE, ".."))
OUTPUT_DIR = os.path.dirname(TASK_DIR)
DB = os.path.join(TASK_DIR, "C-06-bb-01_战斗系统缺口决策库_v1.sqlite")
DATA = os.path.join(TASK_DIR, "C-06-bb-01_战斗系统缺口决策数据_v1.json")


def main():
    conn = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
    cur = conn.cursor()

    meta = {k: v for k, v in cur.execute("SELECT key, value FROM meta")}

    gaps = {}
    # 主表：当前未澄清问题（这些有候选方案）
    for (gap_id, title, level, status, source_ref, impact, close_cond, owner, pr) in cur.execute(
            "SELECT gap_id, title, level, status, source_ref, impact_scope, close_condition,"
            " owner, priority_round FROM gaps"):
        gaps[gap_id] = {
            "gap_id": gap_id, "title": title, "level": level, "status": status,
            "source_ref": source_ref, "impact_scope": impact,
            "close_condition": close_cond, "owner": owner, "priority_round": pr,
            "options": [],
        }
    for (gap_id, label, title, detail, tradeoff, rec) in cur.execute(
            "SELECT gap_id, option_label, summary_title, detail, tradeoff, is_recommended"
            " FROM solution_options WHERE is_custom=0 ORDER BY gap_id, seq"):
        if gap_id in gaps:
            gaps[gap_id]["options"].append({
                "label": label, "title": title, "detail": detail,
                "tradeoff": tradeoff, "recommended": bool(rec)})

    # 归档表：已澄清问题，补齐候选来源说明
    archived = []
    for row in cur.execute(
            "SELECT gap_id, title, level, priority_round, owner, decision_status,"
            " chosen_option_id, chosen_label, chosen_title, answer_text, conclusion,"
            " landed_at, archived_by FROM gaps_archived ORDER BY gap_id"):
        archived.append({
            "gap_id": row[0], "title": row[1], "level": row[2], "priority_round": row[3],
            "owner": row[4], "decision_status": row[5], "chosen_option_id": row[6],
            "chosen_label": row[7], "chosen_title": row[8], "answer_text": row[9],
            "conclusion": row[10], "landed_at": row[11], "archived_by": row[12],
        })
    conn.close()

    report = {
        "meta": {
            "title": meta.get("title", "C-06-bb-01 战斗系统缺口决策库"),
            "chapter": "C-06-bb-01",
            "domain": "06-战斗",
            "analysis_doc": "Dsh/Output/C-06-bb-01/C-06-bb-01_战斗系统信息缺口分析_v1.md",
            "created_at": meta.get("meta_added_at", "2026-09-25")[:10],
            "note": "本文件由 extract_decisions_data.py 从既有决策库提取，"
                    "保留未澄清问题与已归档问题两部分的完整内容，便于回溯库的来源",
        },
        "db_path": "Dsh/Output/C-06-bb-01/C-06-bb-01_战斗系统缺口决策库_v1.sqlite",
        "open_gaps": sorted(gaps.values(), key=lambda g: g["gap_id"]),
        "archived_gaps": archived,
        "stats": {"open": len(gaps), "archived": len(archived)},
    }
    io.open(DATA, "w", encoding="utf-8", newline="\n").write(
        json.dumps(report, ensure_ascii=False, indent=1))
    print(json.dumps(report["stats"], ensure_ascii=False))
    print("已输出:", os.path.basename(DATA), os.path.getsize(DATA), "字节")


if __name__ == "__main__":
    main()
