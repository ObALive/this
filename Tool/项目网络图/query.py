"""项目网络图库的只读查询入口。

用途：让后续任务用一条命令低成本读出工具保存的数据，不必通读 `数据/*.sqlite`
或整份 JSON。库结构与各字段的边界见 `读库说明.md`。

用法（默认读 `Tool/项目网络图/数据/项目网络图.sqlite`）：

    python3 Tool/项目网络图/query.py --outline
    python3 Tool/项目网络图/query.py --node n2
    python3 Tool/项目网络图/query.py --refs --unresolved
    python3 Tool/项目网络图/query.py --issues --level error
    python3 Tool/项目网络图/query.py --sql "SELECT * FROM v_edge LIMIT 5"

约定：
- 所有查询走只读连接，任何写入都会被数据库拒绝；
- 默认输出紧凑文本，加 `--json` 输出结构化数据，便于脚本二次处理；
- `--outline`、`--node` 等只读视图，不加载 model.py；`--issues`、`--view` 需要还原模型现算。
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

import db
import model as M
import store

DEFAULT_DB = store.DB_FILE

READONLY_KEYWORDS = ("select", "with", "pragma", "explain")


# --------------------------------------------------------------------------
# 基础
# --------------------------------------------------------------------------


def _dict(row) -> dict:
    return {key: row[key] for key in row.keys()}


def _rows(conn, sql: str, params=()) -> list[dict]:
    return [_dict(row) for row in conn.execute(sql, params)]


def _require(path) -> None:
    if not db.exists(path):
        raise SystemExit(
            "库不存在：{}\n"
            "先运行一次工具让库生成，或用 --db 指定其它库路径。".format(path)
        )


def open_db(path) -> sqlite3.Connection:
    _require(path)
    return db.connect(path, readonly=True)


def node_id_for(conn, ref: str) -> str | None:
    """接受条目 id（n2），也接受「路线名+编号」（瓦片地图2、地图2）。匹配不唯一时返回 None。"""
    ref = (ref or "").strip()
    if not ref:
        return None
    row = conn.execute("SELECT id FROM nodes WHERE id = ?", (ref,)).fetchone()
    if row is not None:
        return row["id"]

    matched = re.match(r"^(.*?)(\d+)$", ref)
    if not matched:
        return None
    name = matched.group(1).strip()
    number = int(matched.group(2))

    hits = _rows(
        conn,
        "SELECT n.id, s.title, s.path FROM v_node n JOIN v_section s ON s.id = n.section_id"
        " WHERE n.number = ? ORDER BY n.seq",
        (number,),
    )
    if not hits:
        return None
    exact = [h for h in hits if h["title"] == name]
    if len(exact) == 1:
        return exact[0]["id"]
    named = [
        h
        for h in hits
        if name
        and (h["title"].endswith(name) or h["path"].endswith(name) or name.endswith(h["title"]))
    ]
    if len(named) == 1:
        return named[0]["id"]
    return None


# --------------------------------------------------------------------------
# 查询：全部走视图，不还原模型
# --------------------------------------------------------------------------


def stats(conn) -> dict:
    row = conn.execute("SELECT * FROM v_stats").fetchone()
    return _dict(row) if row is not None else {}


def outline(conn) -> dict:
    """一屏拿到路线与条目的骨架：概要、依赖、对象、统计。"""
    refs: dict[str, list] = {}
    for row in _rows(
        conn,
        "SELECT node_id, raw, target_index_label, resolved, reason"
        " FROM v_ref ORDER BY node_id, seq",
    ):
        refs.setdefault(row["node_id"], []).append(row)

    objects: dict[str, list] = {}
    for row in _rows(
        conn,
        "SELECT node_id, name, has_path FROM v_object ORDER BY node_id, seq",
    ):
        objects.setdefault(row["node_id"], []).append(row)

    grouped: dict[str, list] = {}
    for node in _rows(
        conn,
        "SELECT id, section_id, seq, number, index_label, summary, ref_count,"
        " unresolved_ref_count, object_count, note_count, auto_position"
        " FROM v_node ORDER BY seq",
    ):
        node = dict(node)
        node["refs"] = refs.get(node["id"], [])
        node["objects"] = objects.get(node["id"], [])
        grouped.setdefault(node["section_id"], []).append(node)

    sections = []
    for section in _rows(conn, "SELECT * FROM v_section ORDER BY seq"):
        sections.append({**section, "nodes": grouped.get(section["id"], [])})

    return {
        "title": db.meta_value(conn, "title"),
        "source": db.meta_value(conn, "source"),
        "updated_at": db.meta_value(conn, "updated_at"),
        "last_reason": db.meta_value(conn, "last_reason"),
        "stats": stats(conn),
        "sections": sections,
    }


def node_detail(conn, node_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM v_node WHERE id = ?", (node_id,)).fetchone()
    if row is None:
        return None
    node = _dict(row)
    try:
        node["manual"] = json.loads(node["manual"])
    except (TypeError, ValueError):
        node["manual"] = {}
    node["refs"] = _rows(
        conn,
        "SELECT seq, raw, raw_section, raw_number, target_id, target_index_label,"
        " resolved, reason FROM v_ref WHERE node_id = ? ORDER BY seq",
        (node_id,),
    )
    node["objects"] = _rows(
        conn,
        "SELECT seq, name, note, path, has_path FROM v_object WHERE node_id = ? ORDER BY seq",
        (node_id,),
    )
    node["notes"] = [
        r["text"]
        for r in _rows(
            conn, "SELECT text FROM node_notes WHERE node_id = ? ORDER BY seq", (node_id,)
        )
    ]
    return node


def section_detail(conn, section_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM v_section WHERE id = ?", (section_id,)).fetchone()
    if row is None:
        return None
    section = _dict(row)
    section["nodes"] = _rows(
        conn,
        "SELECT id, seq, number, index_label, summary FROM v_node"
        " WHERE section_id = ? ORDER BY seq",
        (section_id,),
    )
    return section


def refs(conn, unresolved_only: bool = False, limit: int = 200) -> list[dict]:
    sql = (
        "SELECT n.seq AS node_seq, r.node_id, r.node_index_label AS node_index_label, r.seq,"
        " r.raw, r.raw_section, r.raw_number, r.target_id, r.target_index_label,"
        " r.resolved, r.reason"
        " FROM v_ref r JOIN v_node n ON n.id = r.node_id"
    )
    if unresolved_only:
        sql += " WHERE r.resolved = 0"
    sql += " ORDER BY n.seq, r.seq LIMIT ?"
    return _rows(conn, sql, (limit,))


def objects(conn, missing_path_only: bool = False, limit: int = 200) -> list[dict]:
    sql = (
        "SELECT n.seq AS node_seq, o.node_id, o.node_index_label, o.seq, o.name, o.note,"
        " o.path, o.has_path"
        " FROM v_object o JOIN v_node n ON n.id = o.node_id"
    )
    if missing_path_only:
        sql += " WHERE o.has_path = 0"
    sql += " ORDER BY n.seq, o.seq LIMIT ?"
    return _rows(conn, sql, (limit,))


def edges(conn, limit: int = 500) -> list[dict]:
    return _rows(
        conn,
        "SELECT f.seq AS from_seq, t.seq AS to_seq, e.from_id, e.to_id, e.kind, e.raw,"
        " e.from_index_label, e.to_index_label"
        " FROM v_edge e JOIN v_node f ON f.id = e.from_id JOIN v_node t ON t.id = e.to_id"
        " ORDER BY f.seq, t.seq LIMIT ?",
        (limit,),
    )


def find(conn, keyword: str, limit: int = 50) -> list[dict]:
    like = "%{}%".format((keyword or "").strip())
    return _rows(
        conn,
        "SELECT id, index_label, number, summary, body FROM v_node"
        " WHERE summary LIKE ? OR body LIKE ?"
        " OR id IN (SELECT node_id FROM node_objects WHERE name LIKE ?)"
        " ORDER BY seq LIMIT ?",
        (like, like, like, limit),
    )


def run_sql(conn, sql: str, limit: int = 200) -> dict:
    text = (sql or "").strip().rstrip(";").strip()
    if not text:
        raise SystemExit("--sql 需要一个查询语句")
    head = text.split(None, 1)[0].lower()
    if head not in READONLY_KEYWORDS:
        raise SystemExit(
            "只允许 SELECT / WITH / PRAGMA / EXPLAIN 查询；写操作请走工具界面或 server.py 接口"
        )
    cur = conn.execute(text)
    if cur.description is None:
        return {"columns": [], "rows": []}
    columns = [d[0] for d in cur.description]
    rows = [
        {name: value for name, value in zip(columns, row)} for row in cur.fetchmany(limit)
    ]
    return {"columns": columns, "rows": rows}


# --------------------------------------------------------------------------
# 查询：需要还原模型
# --------------------------------------------------------------------------


def issues(path, level: str | None = None) -> dict:
    model = db.load_model(path)
    check = M.validate(model)
    items = check["issues"]
    if level:
        items = [i for i in items if i["level"] == level]
    return {"issues": items, "stats": check["stats"]}


def view(path) -> dict:
    return M.serialize(db.load_model(path))


# --------------------------------------------------------------------------
# 文本渲染
# --------------------------------------------------------------------------


def render_outline(data: dict) -> list[str]:
    lines = ["项目网络图 · {}".format(data.get("title") or "（未命名）")]
    if data.get("source"):
        lines.append("源：{}".format(data["source"]))
    if data.get("updated_at"):
        lines.append(
            "最近写入：{}（{}）".format(data["updated_at"], data.get("last_reason") or "-")
        )
    lines.append("")
    for section in data["sections"]:
        indent = "  " * max(0, int(section["level"]) - 1)
        lines.append(
            "{}[{}] {}（{} 条，起始编号 {}）".format(
                indent, section["id"], section["title"], section["node_count"],
                section["start_number"],
            )
        )
        for node in section["nodes"]:
            lines.append(
                "{}  {}  {}  {}".format(
                    indent, node["id"].ljust(4), str(node["number"]).rjust(2),
                    node["summary"] or "（空）",
                )
            )
            detail = []
            if node["refs"]:
                detail.append(
                    "依赖: "
                    + "、".join(
                        r["raw"]
                        + ("(未解析)" if not r["resolved"] else "({})".format(r["target_index_label"] or "?"))
                        for r in node["refs"]
                    )
                )
            if node["objects"]:
                detail.append(
                    "对象: " + "、".join(o["name"] for o in node["objects"])
                )
            if node["note_count"]:
                detail.append("说明 {} 段".format(node["note_count"]))
            if detail:
                lines.append("{}       {}".format(indent, "  |  ".join(detail)))
        if not section["nodes"]:
            lines.append("{}  （无条目）".format(indent))
    s = data["stats"]
    lines.append("")
    lines.append(
        "统计：{} 路线 / {} 条目 / {} 边（链式 {} + 显式 {}）/ 未解析依赖 {} / "
        "对象 {} 名（{} 名已写实现路径）/ 快照 {}".format(
            s.get("sections", 0), s.get("nodes", 0), s.get("edges", 0),
            s.get("chain_edges", 0), s.get("explicit_edges", 0),
            s.get("unresolved_refs", 0), s.get("object_names", 0),
            s.get("object_names_with_path", 0), s.get("snapshots", 0),
        )
    )
    lines.append(
        "提示：单个条目用 --node <id>；未解析依赖用 --refs --unresolved；"
        "全部问题用 --issues；任意 SQL 用 --sql。"
    )
    return lines


def render_node(node: dict) -> list[str]:
    lines = [
        "[{}] {}".format(node["id"], node["index_label"]),
        "路线：{}（{}）".format(node["section_id"], node["section_path"]),
        "编号：{}".format(node["number"]),
        "概要：{}{}".format(
            node["summary"] or "（空）",
            "（自动推导）" if node["summary_is_auto"] else "（人工指定）",
        ),
        "正文：{}".format(node["body"] or "（空）"),
    ]
    if node["refs"]:
        lines.append("依赖：")
        for ref in node["refs"]:
            if ref["resolved"]:
                lines.append(
                    "  - {} -> {}（{}）".format(
                        ref["raw"], ref["target_id"], ref["target_index_label"]
                    )
                )
            else:
                lines.append(
                    "  - {} -> 未解析：{}".format(ref["raw"], ref["reason"] or "未知原因")
                )
    else:
        lines.append("依赖：无")
    if node["objects"]:
        lines.append("对象：")
        for obj in node["objects"]:
            lines.append(
                "  - {}{}{}".format(
                    obj["name"],
                    "（{}）".format(obj["note"]) if obj["note"] else "",
                    "" if obj["has_path"] else "  [实现路径未写]",
                )
            )
    else:
        lines.append("对象：无")
    for index, note in enumerate(node["notes"], 1):
        lines.append("说明 {}：{}".format(index, note))
    lines.append("手工挪位：{}".format(node["manual"] if not node["auto_position"] else "无"))
    return lines


def render_section(section: dict) -> list[str]:
    lines = [
        "[{}] {}（{}）".format(section["id"], section["title"], section["path"]),
        "层级：{}  父级：{}  起始编号：{}  条目数：{}".format(
            section["level"], section["parent_id"] or "-", section["start_number"],
            section["node_count"],
        ),
    ]
    if section["note"]:
        lines.append("标题附注：{}".format(section["note"]))
    for node in section["nodes"]:
        lines.append(
            "  {}  {}  {}".format(
                node["id"].ljust(4), str(node["number"]).rjust(2), node["summary"] or "（空）"
            )
        )
    if not section["nodes"]:
        lines.append("  （无条目）")
    return lines


def render_refs(rows: list[dict]) -> list[str]:
    if not rows:
        return ["没有符合条件的依赖引用"]
    lines = []
    for row in rows:
        lines.append(
            "{}  {}  ->  {}{}".format(
                row["node_index_label"],
                row["raw"],
                row["target_index_label"] or "未解析",
                "" if row["resolved"] else "（{}）".format(row["reason"] or "未知原因"),
            )
        )
    lines.append("共 {} 条".format(len(rows)))
    return lines


def render_objects(rows: list[dict]) -> list[str]:
    if not rows:
        return ["没有符合条件的对象声明"]
    lines = []
    for row in rows:
        lines.append(
            "{}  {}  {}{}".format(
                row["node_index_label"],
                row["name"],
                row["path"] or "（未写实现路径）",
                "  // {}".format(row["note"]) if row["note"] else "",
            )
        )
    lines.append("共 {} 条".format(len(rows)))
    return lines


def render_edges(rows: list[dict]) -> list[str]:
    if not rows:
        return ["没有依赖边"]
    lines = [
        "{}  ->  {}  [{}]{}".format(
            row["from_index_label"], row["to_index_label"], row["kind"],
            "  raw={}".format(row["raw"]) if row["raw"] else "",
        )
        for row in rows
    ]
    lines.append("共 {} 条（from 为前置，to 为依赖方）".format(len(rows)))
    return lines


def render_issues(data: dict) -> list[str]:
    items = data["issues"]
    if not items:
        return ["没有校验问题"]
    lines = [
        "{}  [{}]  {}".format(item["level"], item["kind"], item["text"]) for item in items
    ]
    lines.append(
        "共 {} 条（error {} / warning {} / info {}）".format(
            len(items),
            sum(1 for i in items if i["level"] == "error"),
            sum(1 for i in items if i["level"] == "warning"),
            sum(1 for i in items if i["level"] == "info"),
        )
    )
    return lines


def render_stats(row: dict) -> list[str]:
    return ["{}: {}".format(key, row[key]) for key in row]


def render_sql(result: dict) -> list[str]:
    if not result["columns"]:
        return ["（该语句没有返回结果集）"]
    lines = ["\t".join(result["columns"])]
    for row in result["rows"]:
        lines.append(
            "\t".join("" if row[c] is None else str(row[c]) for c in result["columns"])
        )
    lines.append("共 {} 行（--limit 可放开上限）".format(len(result["rows"])))
    return lines


def render_find(rows: list[dict]) -> list[str]:
    if not rows:
        return ["没有匹配的条目"]
    lines = []
    for row in rows:
        lines.append("[{}] {}  {}".format(row["id"], row["index_label"], row["summary"] or "（空）"))
        if row["body"]:
            lines.append("      {}".format(row["body"]))
    lines.append("共 {} 条".format(len(rows)))
    return lines


def render_schema(report: dict) -> list[str]:
    lines = []
    for kind, title in (("tables", "表"), ("views", "视图")):
        lines.append("== {} ==".format(title))
        for name, columns in report[kind].items():
            lines.append("  {}".format(name))
            for col in columns:
                lines.append(
                    "      {}{}{}".format(
                        col["name"],
                        " {}".format(col["type"]) if col["type"] else "",
                        "  PK" if col["pk"] else "",
                    )
                )
    return lines


def render_verify(result: dict) -> list[str]:
    lines = ["库：{}".format(result.get("path"))]
    if not result.get("exists"):
        lines.append("库不存在")
        return lines
    lines.append("SQLite：{}".format(result.get("sqlite_version")))
    if result.get("error"):
        lines.append("读取失败：{}".format(result["error"]))
        return lines
    lines.append(
        "结构：表缺失 {}，视图缺失 {}".format(
            result.get("missing_tables") or "无", result.get("missing_views") or "无"
        )
    )
    lines.append(
        "完整性：{}，外键错误 {}，重复编号 {}，孤立条目 {}，孤立引用 {}".format(
            result.get("integrity"), result.get("foreign_key_errors", "-"),
            result.get("duplicate_numbers", "-"), result.get("nodes_without_section", "-"),
            result.get("refs_without_node", "-"),
        )
    )
    lines.append("结构版本：{}  最近写入：{}".format(
        result.get("schema_version") or "-", result.get("updated_at") or "-"))
    lines.append("快照时间范围：{}".format(result.get("snapshot_span") or "无"))
    for key, value in (result.get("stats") or {}).items():
        lines.append("  {}: {}".format(key, value))
    return lines


# --------------------------------------------------------------------------
# 命令行
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="项目网络图库只读查询（默认输出紧凑文本，--json 输出结构化数据）"
    )
    parser.add_argument("--db", default=None, help="库路径，默认用工具自带的数据库")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出")
    parser.add_argument("--limit", type=int, default=200, help="列表与 SQL 的最大行数")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--outline", action="store_true", help="路线与条目骨架（默认）")
    group.add_argument("--node", metavar="ID", help="单个条目详情，接受 n2 或 路线名+编号")
    group.add_argument("--section", metavar="ID", help="单条路线详情")
    group.add_argument("--refs", action="store_true", help="全部依赖引用")
    group.add_argument("--objects", action="store_true", help="全部对象声明")
    group.add_argument("--edges", action="store_true", help="全部依赖边")
    group.add_argument("--issues", action="store_true", help="校验问题（需还原模型）")
    group.add_argument("--stats", action="store_true", help="统计汇总")
    group.add_argument("--find", metavar="KEYWORD", help="按概要、正文或对象名搜索条目")
    group.add_argument("--schema", action="store_true", help="列出表与视图的列")
    group.add_argument("--verify", action="store_true", help="库结构与完整性自检")
    group.add_argument("--view", action="store_true", help="整图数据（等价 /api/state）")
    group.add_argument("--sql", metavar="SQL", help="只读 SQL 查询")
    parser.add_argument("--unresolved", action="store_true", help="配合 --refs：只看未解析")
    parser.add_argument("--missing-path", action="store_true", help="配合 --objects：只看未写实现路径")
    parser.add_argument("--level", choices=("error", "warning", "info"), help="配合 --issues：只看某一级别")
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    args = build_parser().parse_args(argv)
    path = Path(args.db).resolve() if args.db else DEFAULT_DB

    # 纯视图查询：不还原模型
    if args.schema:
        _require(path)
        return _output(db.schema_report(path), args.json, render_schema)
    if args.verify:
        return _output(db.verify(path), args.json, render_verify)
    if args.issues:
        _require(path)
        return _output(issues(path, args.level), args.json, render_issues)
    if args.view:
        _require(path)
        return _output(view(path), True, None)

    conn = open_db(path)
    try:
        if args.node:
            node_id = node_id_for(conn, args.node)
            if node_id is None:
                raise SystemExit(
                    "找不到条目：{}（请改用条目 id，例如 --node n2）".format(args.node)
                )
            data = node_detail(conn, node_id)
            return _output(data, args.json, render_node)
        if args.section:
            data = section_detail(conn, args.section)
            if data is None:
                raise SystemExit("找不到开发路线：{}".format(args.section))
            return _output(data, args.json, render_section)
        if args.refs:
            data = refs(conn, args.unresolved, args.limit)
            return _output(data, args.json, render_refs)
        if args.objects:
            data = objects(conn, args.missing_path, args.limit)
            return _output(data, args.json, render_objects)
        if args.edges:
            data = edges(conn, args.limit)
            return _output(data, args.json, render_edges)
        if args.find:
            data = find(conn, args.find, args.limit)
            return _output(data, args.json, render_find)
        if args.stats:
            data = stats(conn)
            return _output(data, args.json, render_stats)
        if args.sql:
            data = run_sql(conn, args.sql, args.limit)
            return _output(data, args.json, render_sql)
        data = outline(conn)
        return _output(data, args.json, render_outline)
    finally:
        conn.close()


def _output(data, as_json: bool, renderer) -> int:
    if as_json or renderer is None:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    for line in renderer(data):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
