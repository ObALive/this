# -*- coding: utf-8 -*-
"""归档已裁定项：把主表中已裁定的缺口移入归档表，主表只保留尚未澄清的问题。

用法：
  python archive_decided.py                              # 归档全部已裁定项
  python archive_decided.py --db <库路径>                # 指定决策库
  python archive_decided.py --check                      # 只预览将归档的项，不写入
  python archive_decided.py --by C-xx-bb-03              # 记录归档人，缺省为当前任务编号提示
  python archive_decided.py --conclusion 结论摘要        # 为本次归档的项补一条结论摘要

归档语义：
  gaps 主表   只保留尚未澄清的问题，填写器只呈现这些项；
  gaps_archived 归档表  保留已澄清问题连同裁定结果、结论摘要与设计落点；
  decisions 表 中已归档项的状态保持不变，仍可查询，不会被删除。

与 import_answers.py --archive 的区别：
  --archive 只把 decisions 的当前状态同步进归档表，主表不动；
  本脚本执行完整的归档动作，即同步归档表并把已裁定项从主表移出。
  两者产出的归档记录结构一致，可先用 dump_decisions.py 核对后再执行。
"""
import argparse
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "建库工具"))
from db_locator import discover_databases, resolve_db, to_rel  # noqa: E402

STATUS_PENDING = "待裁定"


def default_db():
    items = discover_databases()
    if not items:
        raise SystemExit("工作区内没有找到决策库，请用 --db 指定")
    return items[0]


def pending_and_decided(cur):
    rows = list(cur.execute(
        "SELECT g.gap_id, g.title, g.level, g.priority_round, g.owner, g.source_ref,"
        " g.impact_scope, g.close_condition, g.analysis_doc,"
        " d.status, d.chosen_option_id, d.answer_text, d.decision_basis,"
        " d.extra_requirement, d.filled_at"
        " FROM gaps g JOIN decisions d ON d.gap_id = g.gap_id ORDER BY g.gap_id"))
    decided = [r for r in rows if r[9] != STATUS_PENDING]
    pending = [r[0] for r in rows if r[9] == STATUS_PENDING]
    return decided, pending


def archive_rows(cur, decided, archived_by, conclusion):
    written = 0
    for (gap_id, title, level, pr, owner, source_ref, impact, close_cond, analysis_doc,
         status, opt_id, answer, basis, extra, filled) in decided:
        chosen_title = ""
        if opt_id:
            row = cur.execute("SELECT summary_title FROM solution_options WHERE option_id=?",
                              (opt_id,)).fetchone()
            chosen_title = row[0] if row else ""
        label = opt_id.rsplit("-", 1)[-1] if opt_id else ""
        summary = conclusion or answer or chosen_title or ""
        cur.execute(
            "INSERT OR REPLACE INTO gaps_archived (gap_id, title, level, priority_round,"
            " owner, decision_status, chosen_option_id, chosen_label, chosen_title,"
            " answer_text, decision_basis, extra_requirement, filled_at, conclusion,"
            " landed_at, archived_by, archived_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now','localtime'))",
            (gap_id, title, level, pr, owner, status, opt_id or None, label or None,
             chosen_title or None, answer or None, basis or None, extra or None, filled,
             summary, close_cond, archived_by))
        written += 1
    return written


def main():
    parser = argparse.ArgumentParser(description="归档已裁定项")
    parser.add_argument("--db", help="决策库路径，缺省时自动选取")
    parser.add_argument("--check", action="store_true", help="只预览不写入")
    parser.add_argument("--by", default="", help="归档人，写入归档表的 archived_by 字段")
    parser.add_argument("--conclusion", default="", help="为本次归档项补一条统一结论摘要")
    parser.add_argument("--keep-gaps", action="store_true",
                        help="只同步归档表，不从主表移出（与 import_answers --archive 等价）")
    args = parser.parse_args()

    db_path = resolve_db(args.db or default_db())
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    if cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='gaps_archived'"
                   ).fetchone() is None:
        conn.close()
        raise SystemExit("该库没有 gaps_archived 表，请先用建库工具建库")

    decided, pending = pending_and_decided(cur)
    label = args.by or "archive_decided.py"
    report = {
        "库": to_rel(db_path),
        "模式": "仅预览" if args.check else "已归档",
        "将归档项": [r[0] for r in decided],
        "归档项数": len(decided),
        "归档后主表保留": pending,
        "主表保留项数": len(pending),
    }

    if not args.check and decided:
        archive_rows(cur, decided, label, args.conclusion)
        if not args.keep_gaps:
            ids = [(r[0],) for r in decided]
            cur.executemany("DELETE FROM solution_options WHERE gap_id=?", ids)
            cur.executemany("DELETE FROM decisions WHERE gap_id=?", ids)
            cur.executemany("DELETE FROM gaps WHERE gap_id=?", ids)
        conn.commit()
    conn.close()
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
