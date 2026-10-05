# -*- coding: utf-8 -*-
"""读出决策库中的裁定结果，供审阅与归档使用。

三种输出：
  默认：在终端打印逐项裁定摘要与进度统计
  --json：导出结构化 JSON，便于后续脚本处理
  --markdown：导出裁定结论 Markdown，可直接作为回答归档的素材

用法：
  python dump_decisions.py                                  # 打印摘要
  python dump_decisions.py --db <库路径>                    # 指定决策库
  python dump_decisions.py --json --out <文件>              # 导出 JSON
  python dump_decisions.py --markdown --out <文件>          # 导出 Markdown
  python dump_decisions.py --pending                        # 只列出未裁定项
"""
import argparse
import io
import json
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "建库工具"))
from db_locator import discover_databases, resolve_db, to_rel, write_text  # noqa: E402

STATUS_PENDING = "待裁定"


def default_db():
    items = discover_databases()
    if not items:
        raise SystemExit("工作区内没有找到决策库，请用 --db 指定")
    return items[0]


def load(db_path):
    conn = sqlite3.connect("file:%s?mode=ro" % db_path.replace("\\", "/"), uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    gaps = []
    for row in cur.execute(
            "SELECT gap_id, title, level, priority_round, owner FROM gaps ORDER BY gap_id"):
        gaps.append({"gap_id": row["gap_id"], "title": row["title"], "level": row["level"],
                     "priority_round": row["priority_round"] or "", "owner": row["owner"],
                     "decision": None})
    index = {g["gap_id"]: g for g in gaps}
    for row in cur.execute(
            "SELECT gap_id, chosen_option_id, answer_text, decision_basis,"
            " extra_requirement, status, filled_at, needs_followup FROM decisions"):
        gap = index.get(row["gap_id"])
        if gap is None:
            continue
        gap["decision"] = {
            "status": row["status"] or STATUS_PENDING,
            "chosen_option_id": row["chosen_option_id"] or "",
            "chosen_label": (row["chosen_option_id"] or "").rsplit("-", 1)[-1],
            "answer_text": row["answer_text"] or "",
            "decision_basis": row["decision_basis"] or "",
            "extra_requirement": row["extra_requirement"] or "",
            "filled_at": row["filled_at"] or "",
            "needs_followup": bool(row["needs_followup"]),
        }
    for gap in gaps:
        if gap["decision"] is None:
            gap["decision"] = {"status": STATUS_PENDING, "chosen_option_id": "",
                               "chosen_label": "", "answer_text": "", "decision_basis": "",
                               "extra_requirement": "", "filled_at": "",
                               "needs_followup": False}
        if gap["decision"]["chosen_option_id"]:
            row = cur.execute("SELECT detail FROM solution_options WHERE option_id=?",
                              (gap["decision"]["chosen_option_id"],)).fetchone()
            gap["decision"]["chosen_detail"] = row[0] if row else ""
        else:
            gap["decision"]["chosen_detail"] = ""
    stats = {
        "total": len(gaps),
        "decided": sum(1 for g in gaps if g["decision"]["status"] != STATUS_PENDING),
        "pending": sum(1 for g in gaps if g["decision"]["status"] == STATUS_PENDING),
    }
    conn.close()
    return {"db": to_rel(db_path), "gaps": gaps, "stats": stats}


def to_markdown(data):
    decided = [g for g in data["gaps"] if g["decision"]["status"] != STATUS_PENDING]
    lines = [
        "# 裁定结论（%s）" % os.path.basename(data["db"]), "",
        "| 项目 | 内容 |", "| --- | --- |",
        "| 数据来源 | `%s` |" % data["db"],
        "| 缺口总数 | %d |" % data["stats"]["total"],
        "| 已裁定 | %d |" % data["stats"]["decided"],
        "| 未裁定 | %d |" % data["stats"]["pending"],
        "| 导出时间 | %s |" % time.strftime("%Y-%m-%d %H:%M:%S"), "",
        "---", "",
    ]
    for gap in decided:
        d = gap["decision"]
        how = ("候选 %s" % d["chosen_label"]) if d["status"] == "已选候选" else "自定义方案"
        lines += ["## %s %s" % (gap["gap_id"], gap["title"]), "",
                  "| 字段 | 内容 |", "| --- | --- |",
                  "| 等级 | %s |" % gap["level"],
                  "| 责任方 | %s |" % gap["owner"],
                  "| 裁定方式 | %s |" % how]
        if d["chosen_detail"]:
            lines.append("| 采纳方案 | %s |" % d["chosen_detail"].replace("|", "／"))
        if d["answer_text"]:
            lines.append("| 预期方案 | %s |" % d["answer_text"].replace("|", "／"))
        if d["decision_basis"]:
            lines.append("| 裁定理由 | %s |" % d["decision_basis"].replace("|", "／"))
        if d["extra_requirement"]:
            lines.append("| 补充要求 | %s |" % d["extra_requirement"].replace("|", "／"))
        if d["needs_followup"]:
            lines.append("| 备注 | 同时填了候选与预期方案，需要复核以哪一项为准 |")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="读出决策库的裁定结果")
    parser.add_argument("--db", help="决策库路径，缺省时自动选取")
    parser.add_argument("--json", action="store_true", help="导出结构化 JSON")
    parser.add_argument("--markdown", action="store_true", help="导出裁定结论 Markdown")
    parser.add_argument("--out", help="输出文件路径，缺省打印到终端")
    parser.add_argument("--pending", action="store_true", help="只列出未裁定项")
    args = parser.parse_args()

    data = load(resolve_db(args.db or default_db()))

    if args.pending:
        pending = [g["gap_id"] for g in data["gaps"]
                   if g["decision"]["status"] == STATUS_PENDING]
        print(json.dumps({"库": data["db"], "未裁定": pending, "数量": len(pending)},
                         ensure_ascii=False, indent=1))
        return

    if args.json:
        text = json.dumps(data, ensure_ascii=False, indent=1)
    elif args.markdown:
        text = to_markdown(data)
    else:
        print("库      :", data["db"])
        print("进度    : %d/%d 已裁定" % (data["stats"]["decided"], data["stats"]["total"]))
        print("-" * 72)
        for gap in data["gaps"]:
            d = gap["decision"]
            if d["status"] == STATUS_PENDING:
                print("%-16s %-8s 待裁定" % (gap["gap_id"], gap["level"]))
                continue
            answer = d["answer_text"][:36] + ("…" if len(d["answer_text"]) > 36 else "")
            print("%-16s %-8s %-10s %s %s"
                  % (gap["gap_id"], gap["level"], d["status"],
                     d["chosen_option_id"] or "-", answer))
        return

    if args.out:
        write_text(args.out, text)
        print("已输出:", args.out, os.path.getsize(args.out), "字节")
    else:
        print(text)


if __name__ == "__main__":
    main()
