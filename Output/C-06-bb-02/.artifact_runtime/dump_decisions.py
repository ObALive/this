# -*- coding: utf-8 -*-
"""读出决策库中的所有裁定结果，并给出结构化汇总。"""
import io
import json
import os
import sqlite3
import sys

TASK_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUTPUT_DIR = os.path.dirname(TASK_DIR)
DB = os.path.join(OUTPUT_DIR, "C-06-bb-01", "C-06-bb-01_战斗系统缺口决策库_v1.sqlite")


def main():
    conn = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
    cur = conn.cursor()
    out = {"db": os.path.basename(DB), "gaps": [], "pending": [], "stats": {}}

    total = cur.execute("SELECT COUNT(*) FROM gaps").fetchone()[0]
    decided = cur.execute(
        "SELECT COUNT(*) FROM decisions WHERE status <> '待裁定'").fetchone()[0]
    out["stats"] = {"total": total, "decided": decided, "pending": total - decided}

    rows = list(cur.execute(
        "SELECT g.gap_id, g.title, g.level, g.priority_round, g.owner,"
        " d.status, COALESCE(d.chosen_option_id,''), COALESCE(d.answer_text,''),"
        " COALESCE(d.decision_basis,''), COALESCE(d.extra_requirement,''),"
        " d.needs_followup, COALESCE(d.filled_at,'')"
        " FROM gaps g JOIN decisions d ON d.gap_id = g.gap_id"
        " ORDER BY g.gap_id"))
    for (gap_id, title, level, pr, owner, status, opt_id, answer, basis, extra,
         followup, filled_at) in rows:
        if status == "待裁定":
            out["pending"].append(gap_id)
            continue
        label = ""
        opt_title = ""
        if opt_id:
            label = opt_id.rsplit("-", 1)[-1]
            row = cur.execute(
                "SELECT summary_title, detail, tradeoff FROM solution_options"
                " WHERE option_id=?", (opt_id,)).fetchone()
            if row:
                opt_title, detail, tradeoff = row[0], row[1], row[2]
            else:
                detail = tradeoff = ""
        else:
            detail = tradeoff = ""
        out["gaps"].append({
            "gap_id": gap_id, "title": title, "level": level,
            "priority_round": pr, "owner": owner, "status": status,
            "chosen_option_id": opt_id, "chosen_label": label,
            "chosen_title": opt_title, "chosen_detail": detail,
            "chosen_tradeoff": tradeoff, "answer_text": answer,
            "decision_basis": basis, "extra_requirement": extra,
            "needs_followup": bool(followup), "filled_at": filled_at,
        })
    conn.close()

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "decisions_dump.json")
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, ensure_ascii=False, indent=1))

    print("total", out["stats"]["total"], "decided", out["stats"]["decided"],
          "pending", out["stats"]["pending"])
    for g in out["gaps"]:
        print("%s | %s | %s | %s" % (
            g["gap_id"], g["status"],
            g["chosen_option_id"] or "-",
            (g["answer_text"][:40] + "...") if len(g["answer_text"]) > 40 else g["answer_text"]))
    if out["pending"]:
        print("pending:", " ".join(out["pending"]))
    print("dump:", path)


if __name__ == "__main__":
    main()
