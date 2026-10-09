"""玩家反馈主题与具体映射的 SQLite 存取层。仅使用 Python 标准库。"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path


TOOL_DIR = Path(__file__).resolve().parent
WORKSPACE = TOOL_DIR.parents[1]
DEFAULT_DB = TOOL_DIR / "数据" / "玩家反馈映射.sqlite"
SOURCE_MD = WORKSPACE / "Output" / "玩家动作与游戏反馈映射重做" / "玩家动作与游戏反馈映射重做_反馈依赖清单_v2.md"

TOPIC_ID_RE = re.compile(r"^[A-Z][A-Z0-9-]{1,39}$")

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS topics (
    topic_id TEXT PRIMARY KEY,
    player_behavior TEXT NOT NULL CHECK (length(trim(player_behavior)) > 0),
    feedback_topic TEXT NOT NULL CHECK (length(trim(feedback_topic)) > 0),
    code_owner TEXT NOT NULL DEFAULT '',
    source_ref TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS mappings (
    mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id TEXT NOT NULL REFERENCES topics(topic_id) ON DELETE CASCADE,
    player_action TEXT NOT NULL CHECK (length(trim(player_action)) > 0),
    program_feedback TEXT NOT NULL CHECK (length(trim(program_feedback)) > 0),
    context TEXT NOT NULL DEFAULT '',
    condition_text TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_mappings_topic_order
    ON mappings(topic_id, sort_order, mapping_id);
PRAGMA user_version = 1;
"""


def connect(path: Path = DEFAULT_DB) -> sqlite3.Connection:
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"数据库不存在：{path}；先运行 init_db.py")
    con = sqlite3.connect(path.as_uri() + "?mode=rw", uri=True, timeout=5)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA busy_timeout = 5000")
    return con


def topic_from_row(row: sqlite3.Row) -> dict:
    return dict(row)


def _clean(value, field: str, *, required: bool = False, limit: int = 10000) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} 必须是文本")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{field} 不能为空")
    if len(value) > limit:
        raise ValueError(f"{field} 最多 {limit} 字符")
    return value


def _order(value) -> int:
    if isinstance(value, bool):
        raise ValueError("排序值必须是整数")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("排序值必须是整数") from exc
    if result < 0 or result > 1_000_000:
        raise ValueError("排序值必须在 0 至 1000000 之间")
    return result


def _topic_values(data: dict, *, creating: bool) -> dict:
    topic_id = _clean(data.get("topic_id", ""), "编号", required=True, limit=40)
    if not TOPIC_ID_RE.fullmatch(topic_id):
        raise ValueError("编号只能使用大写英文字母、数字和连字符，且不能以数字开头")
    return {
        "topic_id": topic_id,
        "player_behavior": _clean(data.get("player_behavior", ""), "玩家行为范围", required=True, limit=500),
        "feedback_topic": _clean(data.get("feedback_topic", ""), "反馈主题", required=True, limit=500),
        "code_owner": _clean(data.get("code_owner", ""), "代码归属", limit=500),
        "source_ref": _clean(data.get("source_ref", ""), "依据", limit=2000),
        "sort_order": _order(data.get("sort_order", 0)),
    }


def _mapping_values(data: dict) -> dict:
    return {
        "player_action": _clean(data.get("player_action", ""), "具体玩家操作", required=True),
        "program_feedback": _clean(data.get("program_feedback", ""), "程序反馈", required=True),
        "context": _clean(data.get("context", ""), "阶段与上下文"),
        "condition_text": _clean(data.get("condition_text", ""), "触发条件"),
        "notes": _clean(data.get("notes", ""), "备注"),
        "sort_order": _order(data.get("sort_order", 0)),
    }


def list_topics(con: sqlite3.Connection, query: str = "") -> list[dict]:
    query = query.strip()
    if query:
        pattern = f"%{query}%"
        rows = con.execute("""
            SELECT t.*, COUNT(m.mapping_id) AS mapping_count
            FROM topics t LEFT JOIN mappings m ON m.topic_id = t.topic_id
            WHERE t.topic_id LIKE ? OR t.player_behavior LIKE ?
               OR t.feedback_topic LIKE ? OR t.code_owner LIKE ? OR t.source_ref LIKE ?
               OR EXISTS (
                   SELECT 1 FROM mappings mm WHERE mm.topic_id = t.topic_id
                     AND (mm.player_action LIKE ? OR mm.program_feedback LIKE ?
                          OR mm.context LIKE ? OR mm.condition_text LIKE ? OR mm.notes LIKE ?)
               )
            GROUP BY t.topic_id ORDER BY t.sort_order, t.topic_id
        """, (pattern,) * 10).fetchall()
    else:
        rows = con.execute("""
            SELECT t.*, COUNT(m.mapping_id) AS mapping_count
            FROM topics t LEFT JOIN mappings m ON m.topic_id = t.topic_id
            GROUP BY t.topic_id ORDER BY t.sort_order, t.topic_id
        """).fetchall()
    return [topic_from_row(row) for row in rows]


def get_topic(con: sqlite3.Connection, topic_id: str) -> dict | None:
    row = con.execute("SELECT * FROM topics WHERE topic_id = ?", (topic_id,)).fetchone()
    if row is None:
        return None
    topic = topic_from_row(row)
    topic["mappings"] = [dict(item) for item in con.execute(
        "SELECT * FROM mappings WHERE topic_id = ? ORDER BY sort_order, mapping_id",
        (topic_id,),
    )]
    return topic


def create_topic(con: sqlite3.Connection, data: dict) -> dict:
    values = _topic_values(data, creating=True)
    with con:
        con.execute("""
            INSERT INTO topics(topic_id, player_behavior, feedback_topic,
                               code_owner, source_ref, sort_order)
            VALUES (:topic_id, :player_behavior, :feedback_topic,
                    :code_owner, :source_ref, :sort_order)
        """, values)
    return get_topic(con, values["topic_id"])


def update_topic(con: sqlite3.Connection, topic_id: str, data: dict) -> dict | None:
    values = _topic_values({**data, "topic_id": topic_id}, creating=False)
    with con:
        cursor = con.execute("""
            UPDATE topics SET player_behavior=:player_behavior,
                feedback_topic=:feedback_topic, code_owner=:code_owner,
                source_ref=:source_ref, sort_order=:sort_order,
                updated_at=CURRENT_TIMESTAMP
            WHERE topic_id=:topic_id
        """, values)
    return get_topic(con, topic_id) if cursor.rowcount else None


def delete_topic(con: sqlite3.Connection, topic_id: str) -> bool:
    with con:
        cursor = con.execute("DELETE FROM topics WHERE topic_id = ?", (topic_id,))
    return bool(cursor.rowcount)


def create_mapping(con: sqlite3.Connection, topic_id: str, data: dict) -> dict:
    values = _mapping_values(data)
    values["topic_id"] = topic_id
    with con:
        cursor = con.execute("""
            INSERT INTO mappings(topic_id, player_action, program_feedback,
                                 context, condition_text, notes, sort_order)
            VALUES (:topic_id, :player_action, :program_feedback,
                    :context, :condition_text, :notes, :sort_order)
        """, values)
    return dict(con.execute("SELECT * FROM mappings WHERE mapping_id = ?", (cursor.lastrowid,)).fetchone())


def update_mapping(con: sqlite3.Connection, mapping_id: int, data: dict) -> dict | None:
    values = _mapping_values(data)
    values["mapping_id"] = mapping_id
    with con:
        cursor = con.execute("""
            UPDATE mappings SET player_action=:player_action,
                program_feedback=:program_feedback, context=:context,
                condition_text=:condition_text, notes=:notes,
                sort_order=:sort_order, updated_at=CURRENT_TIMESTAMP
            WHERE mapping_id=:mapping_id
        """, values)
    row = con.execute("SELECT * FROM mappings WHERE mapping_id = ?", (mapping_id,)).fetchone()
    return dict(row) if cursor.rowcount and row else None


def delete_mapping(con: sqlite3.Connection, mapping_id: int) -> bool:
    with con:
        cursor = con.execute("DELETE FROM mappings WHERE mapping_id = ?", (mapping_id,))
    return bool(cursor.rowcount)


def export_data(con: sqlite3.Connection) -> dict:
    topics = list_topics(con)
    for topic in topics:
        topic["mappings"] = get_topic(con, topic["topic_id"])["mappings"]
    return {"schema_version": 1, "topics": topics}
