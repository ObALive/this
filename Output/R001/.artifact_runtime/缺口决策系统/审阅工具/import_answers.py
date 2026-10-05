# -*- coding: utf-8 -*-
"""把作答模板或等价 JSON 中的裁定结果导入决策库，并可同步归档状态。

用法：
  python import_answers.py                      # 自动选取工作区内第一个决策库
  python import_answers.py --db <库路径>        # 指定决策库
  python import_answers.py --answers <作答文件> # 指定作答文件（模板 md 或 JSON）
  python import_answers.py --check              # 只校验不写入
  python import_answers.py --archive            # 把已裁定项同步到归档表

模板解析规则：
  以 "## 缺口编号 " 开头的行开启一个缺口的作答区；
  区内查找 [候选]、[预期方案]、[裁定理由]、[补充要求] 四个标记，标记后的同行内容即为答案；
  留空表示未裁定。

写入规则：
  填了候选字母且该候选存在时写入 decisions.chosen_option_id 并把状态改为 已选候选；
  填了预期方案时写入 decisions.answer_text 并把状态改为 自定义方案；
  两者都填时以预期方案为准并把 needs_followup 置 1；
  候选字母无法识别时判为冲突，跳过该缺口并计入报告。
"""
import argparse
import io
import json
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "建库工具"))
from db_locator import discover_databases, resolve_db, to_abs, to_rel  # noqa: E402

GAP_HEAD = re.compile(r"^##\s+(\S+)\s")
MARKS = {
    "candidate": "[候选]",
    "custom": "[预期方案]",
    "basis": "[裁定理由]",
    "extra": "[补充要求]",
}
STATUS_PENDING = "待裁定"
STATUS_CHOSEN = "已选候选"
STATUS_CUSTOM = "自定义方案"


def default_db():
    items = discover_databases()
    if not items:
        raise SystemExit("工作区内没有找到决策库，请用 --db 指定")
    return items[0]


def default_answers(db_rel):
    task_dir = os.path.dirname(to_abs(db_rel))
    if not os.path.isdir(task_dir):
        return None
    for name in sorted(os.listdir(task_dir)):
        if "作答模板" in name and name.endswith(".md"):
            return os.path.join(task_dir, name)
    return None


def parse_template(path):
    answers, current = {}, None
    for raw in io.open(path, encoding="utf-8"):
        line = raw.rstrip("\n")
        head = GAP_HEAD.match(line.strip()) if line.startswith("##") else None
        if head:
            current = head.group(1)
            answers[current] = {k: "" for k in MARKS}
            continue
        if current is None:
            continue
        stripped = line.strip()
        for key, mark in MARKS.items():
            if stripped.startswith(mark):
                value = stripped[len(mark):].strip().strip("`").strip()
                if value:
                    answers[current][key] = value
    return answers


def parse_json(path):
    data = json.load(io.open(path, encoding="utf-8"))
    items = data.get("answers", data if isinstance(data, list) else [])
    answers = {}
    for item in items:
        gap_id = item.get("gap_id")
        if not gap_id:
            continue
        answers[gap_id] = {
            "candidate": (item.get("chosen_option") or "").strip(),
            "custom": (item.get("answer_text") or "").strip(),
            "basis": (item.get("decision_basis") or "").strip(),
            "extra": (item.get("extra_requirement") or "").strip(),
        }
    return answers


def archive_decided(cur, archived_by):
    """把已裁定项同步到归档表。"""
    rows = list(cur.execute(
        "SELECT g.gap_id, g.title, g.level, g.priority_round, g.owner,"
        " d.status, d.chosen_option_id, d.answer_text, d.decision_basis,"
        " d.extra_requirement, d.filled_at"
        " FROM gaps g JOIN decisions d ON d.gap_id = g.gap_id"
        " WHERE d.status <> ?", (STATUS_PENDING,)))
    for (gap_id, title, level, pr, owner, status, opt_id, answer, basis, extra, filled) in rows:
        chosen_title = ""
        if opt_id:
            row = cur.execute("SELECT summary_title FROM solution_options WHERE option_id=?",
                              (opt_id,)).fetchone()
            chosen_title = row[0] if row else ""
        label = opt_id.rsplit("-", 1)[-1] if opt_id else ""
        cur.execute(
            "INSERT OR REPLACE INTO gaps_archived (gap_id, title, level, priority_round,"
            " owner, decision_status, chosen_option_id, chosen_label, chosen_title,"
            " answer_text, decision_basis, extra_requirement, filled_at, conclusion,"
            " landed_at, archived_by, archived_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now','localtime'))",
            (gap_id, title, level, pr, owner, status, opt_id, label, chosen_title,
             answer, basis, extra, filled, (answer or chosen_title or ""), "", archived_by))
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description="把作答结果导入决策库")
    parser.add_argument("--db", help="决策库路径，缺省时自动选取")
    parser.add_argument("--answers", help="作答文件路径，缺省时取库同目录下的作答模板")
    parser.add_argument("--check", action="store_true", help="只校验不写入")
    parser.add_argument("--archive", action="store_true", help="把已裁定项同步到归档表")
    parser.add_argument("--archived-by", default="import_answers.py", help="归档标记")
    args = parser.parse_args()

    db_rel = args.db or default_db()
    db_path = resolve_db(db_rel)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    report = {"库": to_rel(db_path), "模式": "仅校验" if args.check else "已写入"}

    if args.archive:
        count = 0 if args.check else archive_decided(cur, args.archived_by)
        if not args.check:
            conn.commit()
        report["归档同步项数"] = count
        print(json.dumps(report, ensure_ascii=False, indent=1))
        conn.close()
        return

    answers_path = args.answers or default_answers(db_rel)
    if not answers_path or not os.path.isfile(answers_path):
        raise SystemExit("找不到作答文件，请用 --answers 指定")

    answers = (parse_json(answers_path) if str(answers_path).lower().endswith(".json")
               else parse_template(answers_path))
    valid_options = {r[0] for r in cur.execute("SELECT option_id FROM solution_options")}
    known_gaps = {r[0] for r in cur.execute("SELECT gap_id FROM gaps")}

    applied, empty, conflicts = [], [], []
    for gap_id in sorted(known_gaps):
        ans = answers.get(gap_id)
        if not ans or not (ans["candidate"] or ans["custom"]):
            empty.append(gap_id)
            continue
        option_id = None
        if ans["candidate"]:
            label = ans["candidate"].strip().upper()
            label = label.replace("候选", "").replace("OPT-", "").strip("- ")
            if label in ("A", "B", "C", "D"):
                option_id = "%s-OPT-%s" % (gap_id, label)
        if ans["candidate"] and option_id not in valid_options and not ans["custom"]:
            conflicts.append({"缺口": gap_id, "原因": "候选字母无法识别: %s" % ans["candidate"]})
            continue
        status = STATUS_CUSTOM if ans["custom"] else STATUS_CHOSEN
        followup = 1 if (ans["candidate"] and ans["custom"]) else 0
        applied.append((gap_id, option_id, ans["custom"] or None, ans["basis"] or None,
                        ans["extra"] or None, status, followup))

    if not args.check:
        for gap_id, option_id, custom, basis, extra, status, followup in applied:
            cur.execute(
                "UPDATE decisions SET chosen_option_id=?, answer_text=?, decision_basis=?,"
                " extra_requirement=?, status=?, filled_at=datetime('now','localtime'),"
                " needs_followup=? WHERE gap_id=?",
                (option_id, custom, basis, extra, status, followup, gap_id))
            cur.execute("UPDATE solution_options SET is_selected=0 WHERE gap_id=?", (gap_id,))
            if option_id and status == STATUS_CHOSEN:
                cur.execute("UPDATE solution_options SET is_selected=1 WHERE option_id=?",
                            (option_id,))
        conn.commit()

    report.update({
        "作答文件": os.path.basename(answers_path),
        "写入项数": len(applied),
        "未填写项数": len(empty),
        "冲突": conflicts or "无",
    })
    print(json.dumps(report, ensure_ascii=False, indent=1))
    conn.close()


if __name__ == "__main__":
    main()
