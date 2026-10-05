# -*- coding: utf-8 -*-
"""缺口决策库模板：供各章节建立与信息缺口分析配套的决策库。

本模块是缺口决策系统的建库内核，工具位于 `Dsh/Tool/缺口决策系统/`。

三层结构：
  gaps              缺口主表，只保留尚未澄清的问题，填写器只呈现这一层
  solution_options  候选方案，每项 2 至 3 条候选加一条自定义预留行
  decisions         裁定结果，采用候选写入 chosen_option_id，自定义方案写入 answer_text
  gaps_archived     归档表，已澄清问题连同结论与设计落点移入此处，便于回顾

典型流程：
  建库 → 填写器或作答模板填写 → 导入裁定 → 导出结论 → 归档（把已裁定项移入归档表）
  归档动作可用本模块的 archive_decided()，也可用 `审阅工具/archive_decided.py`。

最小用法：
    from decision_db import GapRecord, OptionRecord, build_decision_db

    build_decision_db(
        path="Dsh/Output/C-aa-bb-01/C-aa-bb-01_某系统缺口决策库_v1.sqlite",
        meta={"title": "…", "chapter": "C-aa-bb-01", "domain": "…",
              "analysis_doc": "…", "created_at": "2026-09-25"},
        gaps=[GapRecord(gap_id="XXX-GAP-001", title="…", level="B0", …)],
        options={"XXX-GAP-001": [OptionRecord("A", "…", "…", "…", True), …]},
    )

更省事的方式是走工具入口：把数据写成 JSON，用 `建库工具/build_decision_db.py` 建库。
"""
import os
import sqlite3

STATUS_PENDING = "待裁定"
STATUS_CHOSEN = "已选候选"
STATUS_CUSTOM = "自定义方案"
# 开放填写缺口：分析阶段认定属于明显设计空缺、没有提供候选的依据，
# 因此不设候选项，由自定义输入框直接承载需要设计的内容。带该状态的缺口不受
# “每项缺口 2 至 3 条候选”的校验约束。
STATUS_OPEN = "开放填写"

LABELS = ("A", "B", "C", "D")
CUSTOM_SEQ = 99

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE gaps (
    gap_id          TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    level           TEXT NOT NULL,
    status          TEXT NOT NULL,
    source_ref      TEXT NOT NULL,
    impact_scope    TEXT NOT NULL,
    close_condition TEXT NOT NULL,
    owner           TEXT NOT NULL,
    priority_round  TEXT,
    analysis_doc    TEXT NOT NULL
);

CREATE TABLE solution_options (
    option_id       TEXT PRIMARY KEY,
    gap_id          TEXT NOT NULL REFERENCES gaps(gap_id),
    seq             INTEGER NOT NULL,
    option_label    TEXT NOT NULL,
    summary_title   TEXT NOT NULL,
    detail          TEXT NOT NULL,
    tradeoff        TEXT NOT NULL,
    is_recommended  INTEGER NOT NULL DEFAULT 0,
    is_selected     INTEGER NOT NULL DEFAULT 0,
    is_custom       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE decisions (
    gap_id               TEXT PRIMARY KEY REFERENCES gaps(gap_id),
    chosen_option_id     TEXT,
    answer_text          TEXT,
    decision_basis       TEXT,
    extra_requirement    TEXT,
    decided_by           TEXT,
    decided_date         TEXT,
    status               TEXT NOT NULL DEFAULT '待裁定',
    filled_at            TEXT,
    needs_followup       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE gaps_archived (
    gap_id           TEXT PRIMARY KEY,
    title            TEXT NOT NULL,
    level            TEXT NOT NULL,
    priority_round   TEXT,
    owner            TEXT NOT NULL,
    decision_status  TEXT NOT NULL,
    chosen_option_id TEXT,
    chosen_label     TEXT,
    chosen_title     TEXT,
    answer_text      TEXT,
    decision_basis   TEXT,
    extra_requirement TEXT,
    filled_at        TEXT,
    conclusion       TEXT NOT NULL,
    landed_at        TEXT NOT NULL,
    archived_by      TEXT NOT NULL,
    archived_at      TEXT NOT NULL
);

CREATE INDEX idx_options_gap ON solution_options(gap_id, seq);

CREATE VIEW v_gap_decision AS
SELECT  g.gap_id,
        g.level,
        g.owner,
        g.priority_round,
        g.status                                    AS gap_status,
        g.title,
        d.status                                    AS decision_status,
        d.chosen_option_id,
        (SELECT COUNT(*) FROM solution_options o
          WHERE o.gap_id = g.gap_id AND o.is_custom = 0)   AS candidate_count,
        CASE
            WHEN d.answer_text IS NOT NULL AND TRIM(d.answer_text) <> '' THEN d.answer_text
            WHEN d.chosen_option_id IS NOT NULL                            THEN d.chosen_option_id
            ELSE NULL
        END                                         AS final_answer,
        d.needs_followup
FROM gaps g
LEFT JOIN decisions d ON d.gap_id = g.gap_id;
"""

REQUIRED_TABLES = ("meta", "gaps", "solution_options", "decisions", "gaps_archived")
REQUIRED_VIEWS = ("v_gap_decision",)


class GapRecord(object):
    """一项缺口的登记信息。"""

    def __init__(self, gap_id, title, level="B1", status=STATUS_PENDING,
                 source_ref="", impact_scope="", close_condition="", owner="主策划",
                 priority_round=None):
        self.gap_id = gap_id
        self.title = title
        self.level = level
        self.status = status
        self.source_ref = source_ref
        self.impact_scope = impact_scope
        self.close_condition = close_condition
        self.owner = owner
        self.priority_round = priority_round


class OptionRecord(object):
    """一条候选方案。"""

    def __init__(self, label, summary_title, detail, tradeoff, recommended=False):
        self.label = label
        self.summary_title = summary_title
        self.detail = detail
        self.tradeoff = tradeoff
        self.recommended = recommended


def build_decision_db(path, meta, gaps, options):
    """建立决策库。同路径文件会被覆盖，请先确认是否已有旧版。"""
    if os.path.exists(path):
        os.remove(path)
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)

    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.executescript(SCHEMA)

    for key, value in meta.items():
        cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                    (key, str(value)))
    analysis_doc = meta.get("analysis_doc", "")

    problems = []
    for gap in gaps:
        cur.execute(
            "INSERT INTO gaps (gap_id, title, level, status, source_ref, impact_scope,"
            " close_condition, owner, priority_round, analysis_doc)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (gap.gap_id, gap.title, gap.level, gap.status, gap.source_ref,
             gap.impact_scope, gap.close_condition, gap.owner, gap.priority_round,
             analysis_doc))
        cur.execute("INSERT INTO decisions (gap_id, status) VALUES (?, ?)",
                    (gap.gap_id, STATUS_PENDING))

        records = options.get(gap.gap_id) or []
        if gap.status != STATUS_OPEN and not 2 <= len(records) <= len(LABELS):
            problems.append("%s 的候选数量为 %d，应为 2 至 3 条" % (gap.gap_id, len(records)))
        recommended = [r for r in records if r.recommended]
        if len(recommended) > 1:
            problems.append("%s 标记了 %d 条推荐候选，应至多一条" % (gap.gap_id, len(recommended)))

        for index, record in enumerate(records):
            label = record.label or LABELS[index]
            cur.execute(
                "INSERT INTO solution_options (option_id, gap_id, seq, option_label,"
                " summary_title, detail, tradeoff, is_recommended)"
                " VALUES (?,?,?,?,?,?,?,?)",
                ("%s-OPT-%s" % (gap.gap_id, label), gap.gap_id, index + 1, label,
                 record.summary_title, record.detail, record.tradeoff,
                 1 if record.recommended else 0))
        cur.execute(
            "INSERT INTO solution_options (option_id, gap_id, seq, option_label,"
            " summary_title, detail, tradeoff, is_recommended, is_custom)"
            " VALUES (?,?,?,?,?,?,?,0,1)",
            ("%s-OPT-CUSTOM" % gap.gap_id, gap.gap_id, CUSTOM_SEQ, "自定义",
             "自行填写预期设计方案", "", ""))

    conn.commit()
    summary = verify_decision_db(conn)
    conn.close()
    summary["problems"] = problems
    summary["path"] = path
    return summary


def append_decision_db(path, gaps, options, analysis_doc=None):
    """把新一批缺口追加进既有库，保留主表、归档表与全部既有数据。

    追加语义：编号不得与主表或归档表重复；重复编号直接拒绝，不覆盖既有记录。
    返回与 build_decision_db 同结构的自检结果，另加 added 与 duplicate 两个字段。
    """
    if not os.path.exists(path):
        raise SystemExit("库不存在，请先用 build_decision_db 建库：%s" % path)

    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()
    if analysis_doc is None:
        row = cur.execute("SELECT value FROM meta WHERE key='analysis_doc'").fetchone()
        analysis_doc = row[0] if row else ""

    existing = {r[0] for r in cur.execute("SELECT gap_id FROM gaps")}
    existing |= {r[0] for r in cur.execute("SELECT gap_id FROM gaps_archived")}

    problems, duplicate, added = [], [], 0
    for gap in gaps:
        if gap.gap_id in existing:
            duplicate.append(gap.gap_id)
            problems.append("%s 的编号已存在，追加操作不覆盖既有记录" % gap.gap_id)
            continue
        cur.execute(
            "INSERT INTO gaps (gap_id, title, level, status, source_ref, impact_scope,"
            " close_condition, owner, priority_round, analysis_doc)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (gap.gap_id, gap.title, gap.level, gap.status, gap.source_ref,
             gap.impact_scope, gap.close_condition, gap.owner, gap.priority_round,
             analysis_doc))
        cur.execute("INSERT INTO decisions (gap_id, status) VALUES (?, ?)",
                    (gap.gap_id, STATUS_PENDING))

        records = options.get(gap.gap_id) or []
        if gap.status != STATUS_OPEN and not 2 <= len(records) <= len(LABELS):
            problems.append("%s 的候选数量为 %d，应为 2 至 3 条" % (gap.gap_id, len(records)))
        if len([r for r in records if r.recommended]) > 1:
            problems.append("%s 标记了多条推荐候选，应至多一条" % gap.gap_id)

        for index, record in enumerate(records):
            label = record.label or LABELS[index]
            cur.execute(
                "INSERT INTO solution_options (option_id, gap_id, seq, option_label,"
                " summary_title, detail, tradeoff, is_recommended)"
                " VALUES (?,?,?,?,?,?,?,?)",
                ("%s-OPT-%s" % (gap.gap_id, label), gap.gap_id, index + 1, label,
                 record.summary_title, record.detail, record.tradeoff,
                 1 if record.recommended else 0))
        cur.execute(
            "INSERT INTO solution_options (option_id, gap_id, seq, option_label,"
            " summary_title, detail, tradeoff, is_recommended, is_custom)"
            " VALUES (?,?,?,?,?,?,?,0,1)",
            ("%s-OPT-CUSTOM" % gap.gap_id, gap.gap_id, CUSTOM_SEQ, "自定义",
             "自行填写预期设计方案", "", ""))
        existing.add(gap.gap_id)
        added += 1

    conn.commit()
    summary = verify_decision_db(conn)
    conn.close()
    summary["added"] = added
    summary["duplicate"] = duplicate
    summary["problems"] = problems
    summary["path"] = path
    return summary


def verify_decision_db(conn):
    """校验结构、内容与引用完整性，返回可打印的自检结果。"""
    if isinstance(conn, str):
        conn = sqlite3.connect("file:%s?mode=ro" % conn.replace("\\", "/"), uri=True)
        close_after = True
    else:
        close_after = False
    cur = conn.cursor()
    tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    views = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='view'")}
    result = {
        "missing_tables": sorted(set(REQUIRED_TABLES) - tables),
        "missing_views": sorted(set(REQUIRED_VIEWS) - views),
        "integrity": cur.execute("PRAGMA integrity_check").fetchone()[0],
        "foreign_key_errors": len(list(cur.execute("PRAGMA foreign_key_check"))),
    }
    if result["missing_tables"]:
        if close_after:
            conn.close()
        return result
    result.update({
        "gaps": cur.execute("SELECT COUNT(*) FROM gaps").fetchone()[0],
        "candidates": cur.execute(
            "SELECT COUNT(*) FROM solution_options WHERE is_custom=0").fetchone()[0],
        "custom_rows": cur.execute(
            "SELECT COUNT(*) FROM solution_options WHERE is_custom=1").fetchone()[0],
        "decisions": cur.execute("SELECT COUNT(*) FROM decisions").fetchone()[0],
        "pending": cur.execute(
            "SELECT COUNT(*) FROM decisions WHERE status=?", (STATUS_PENDING,)).fetchone()[0],
        "archived": cur.execute("SELECT COUNT(*) FROM gaps_archived").fetchone()[0],
        "gaps_with_wrong_candidate_count": cur.execute(
            "SELECT COUNT(*) FROM (SELECT o.gap_id FROM solution_options o"
            " JOIN gaps g ON g.gap_id = o.gap_id WHERE o.is_custom=0"
            " GROUP BY o.gap_id HAVING COUNT(*) NOT BETWEEN 2 AND 3)").fetchone()[0],
        "gaps_without_one_recommendation": cur.execute(
            "SELECT COUNT(*) FROM (SELECT g.gap_id FROM gaps g"
            " LEFT JOIN solution_options o ON o.gap_id = g.gap_id AND o.is_recommended=1"
            " WHERE g.status <> ? GROUP BY g.gap_id HAVING COUNT(o.gap_id) <> 1)",
            (STATUS_OPEN,)).fetchone()[0],
        "open_gaps": cur.execute(
            "SELECT COUNT(*) FROM gaps WHERE status=?", (STATUS_OPEN,)).fetchone()[0],
        "open_gaps_with_candidates": cur.execute(
            "SELECT COUNT(*) FROM (SELECT g.gap_id FROM gaps g"
            " JOIN solution_options o ON o.gap_id = g.gap_id AND o.is_custom=0"
            " WHERE g.status = ? GROUP BY g.gap_id)", (STATUS_OPEN,)).fetchone()[0],
        "empty_detail": cur.execute(
            "SELECT COUNT(*) FROM solution_options WHERE is_custom=0 AND"
            " (TRIM(COALESCE(detail,''))='' OR TRIM(COALESCE(tradeoff,''))='')").fetchone()[0],
        "orphan_options": cur.execute(
            "SELECT COUNT(*) FROM solution_options o LEFT JOIN gaps g"
            " ON g.gap_id=o.gap_id WHERE g.gap_id IS NULL").fetchone()[0],
    })
    if close_after:
        conn.close()
    return result


def ensure_meta(path, meta):
    """为已有决策库补建 meta 表并写入元信息，不改动其余数据。"""
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    for key, value in meta.items():
        cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                    (key, str(value)))
    conn.commit()
    count = cur.execute("SELECT COUNT(*) FROM meta").fetchone()[0]
    conn.close()
    return count


def ensure_archive_table(path):
    """为早期版本建立的决策库补建归档表，结构与新建库一致。"""
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS gaps_archived (
        gap_id           TEXT PRIMARY KEY,
        title            TEXT NOT NULL,
        level            TEXT NOT NULL,
        priority_round   TEXT,
        owner            TEXT NOT NULL,
        decision_status  TEXT NOT NULL,
        chosen_option_id TEXT,
        chosen_label     TEXT,
        chosen_title     TEXT,
        answer_text      TEXT,
        decision_basis   TEXT,
        extra_requirement TEXT,
        filled_at        TEXT,
        conclusion       TEXT NOT NULL,
        landed_at        TEXT NOT NULL,
        archived_by      TEXT NOT NULL,
        archived_at      TEXT NOT NULL)""")
    conn.commit()
    conn.close()
    return True


def archive_decided(cur, archived_by, conclusion_map=None, drop_from_gaps=True):
    """把已裁定项移入归档表；drop_from_gaps 为真时同时从主表移出。

    conclusion_map 可以是 {gap_id: 结论摘要}，用于给归档项补写可读结论；
    未提供时以预期方案或所采纳候选的标题作为结论摘要。
    返回 (归档项数, 归档后主表剩余项数)。
    """
    conclusion_map = conclusion_map or {}
    rows = list(cur.execute(
        "SELECT g.gap_id, g.title, g.level, g.priority_round, g.owner, g.close_condition,"
        " d.status, d.chosen_option_id, d.answer_text, d.decision_basis,"
        " d.extra_requirement, d.filled_at"
        " FROM gaps g JOIN decisions d ON d.gap_id = g.gap_id ORDER BY g.gap_id"))
    decided = [r for r in rows if r[6] != STATUS_PENDING]
    for (gap_id, title, level, pr, owner, close_cond, status, opt_id, answer, basis,
         extra, filled) in decided:
        chosen_title = ""
        if opt_id:
            row = cur.execute("SELECT summary_title FROM solution_options WHERE option_id=?",
                              (opt_id,)).fetchone()
            chosen_title = row[0] if row else ""
        label = opt_id.rsplit("-", 1)[-1] if opt_id else ""
        summary = conclusion_map.get(gap_id) or answer or chosen_title or ""
        cur.execute(
            "INSERT OR REPLACE INTO gaps_archived (gap_id, title, level, priority_round,"
            " owner, decision_status, chosen_option_id, chosen_label, chosen_title,"
            " answer_text, decision_basis, extra_requirement, filled_at, conclusion,"
            " landed_at, archived_by, archived_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now','localtime'))",
            (gap_id, title, level, pr, owner, status, opt_id or None, label or None,
             chosen_title or None, answer or None, basis or None, extra or None, filled,
             summary, close_cond, archived_by))
    if drop_from_gaps and decided:
        ids = [(r[0],) for r in decided]
        cur.executemany("DELETE FROM solution_options WHERE gap_id=?", ids)
        cur.executemany("DELETE FROM decisions WHERE gap_id=?", ids)
        cur.executemany("DELETE FROM gaps WHERE gap_id=?", ids)
    remaining = cur.execute("SELECT COUNT(*) FROM gaps").fetchone()[0]
    return len(decided), remaining


def main():
    """命令行用法：
    python decision_db.py --check <库路径>
    python decision_db.py --ensure-meta <库路径> [--title 标题] [--chapter 章节]
    python decision_db.py --ensure-archive <库路径>
    """
    import argparse
    import json
    import time
    parser = argparse.ArgumentParser(description="决策库模板与校验工具")
    parser.add_argument("--check", metavar="DB", help="校验一个已有决策库")
    parser.add_argument("--ensure-meta", metavar="DB", help="为已有决策库补建 meta 表")
    parser.add_argument("--ensure-archive", metavar="DB", help="为已有决策库补建归档表")
    parser.add_argument("--title", default="", help="补建 meta 表时写入的库标题")
    parser.add_argument("--chapter", default="", help="补建 meta 表时写入的章节编号")
    parser.add_argument("--domain", default="", help="补建 meta 表时写入的所属域")
    parser.add_argument("--analysis-doc", default="", help="补建 meta 表时写入的分析文档路径")
    args = parser.parse_args()

    if args.ensure_archive:
        ensure_archive_table(args.ensure_archive)
        print(json.dumps({"path": args.ensure_archive, "archive_table": "已就绪"},
                         ensure_ascii=False, indent=1))
        return

    if args.ensure_meta:
        meta = {
            "title": args.title or os.path.splitext(os.path.basename(args.ensure_meta))[0],
            "chapter": args.chapter, "domain": args.domain,
            "analysis_doc": args.analysis_doc,
            "meta_added_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        count = ensure_meta(args.ensure_meta, meta)
        print(json.dumps({"path": args.ensure_meta, "meta_rows": count},
                         ensure_ascii=False, indent=1))
        return

    if args.check:
        print(json.dumps(verify_decision_db(args.check), ensure_ascii=False, indent=1))
        return

    print(__doc__)


if __name__ == "__main__":
    main()
