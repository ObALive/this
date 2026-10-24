"""项目网络图的 SQLite 存档层。

职责：
1. 定义库结构：9 张表与 6 个视图，承载网络图的全部权威数据；
2. 整模型读写：`save_model` 覆盖式写入，`load_model_dict` / `load_model` 读回并还原模型；
3. 快照：按时间限流写入整模型快照，滚动保留最近若干份，供误操作恢复；
4. 自检：`verify` 检查结构与引用完整性；
5. 只读连接：`connect(readonly=True)` 供查询工具与后续智能体低成本读取。

设计约定：
- 库是唯一事实来源，旧版 JSON 存档只作为一次性迁移来源；
- 依赖边、编号索引、对象索引、统计值都是派生数据，不落表，由视图现算；
- 写路径一律整模型覆盖，不做行级增量更新，避免读出半更新的库；
- 本模块只依赖标准库 sqlite3，与 model.py 一样不做任何输入输出之外的事情。

库结构、各列的来源与边界见 `读库说明.md`。
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

import model as M

SCHEMA_VERSION = 2
TOOL_NAME = "项目网络图"

SNAPSHOT_INTERVAL_SECONDS = 120
SNAPSHOT_KEEP = 30

REQUIRED_TABLES = (
    "meta",
    "model_meta",
    "aliases",
    "sections",
    "nodes",
    "node_refs",
    "node_objects",
    "node_notes",
    "snapshots",
)

REQUIRED_VIEWS = (
    "v_section",
    "v_node",
    "v_ref",
    "v_object",
    "v_edge",
    "v_stats",
)

# --------------------------------------------------------------------------
# 库结构
# --------------------------------------------------------------------------

SCHEMA = """
-- 库级标量：库结构版本、标题、来源任务书、前言、最近写入时间等
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- 模型的可扩展元信息（Model.meta），值以 JSON 编码存放
CREATE TABLE IF NOT EXISTS model_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- 引用别名：写进正文的非标准路线写法 -> 标准路线标题
CREATE TABLE IF NOT EXISTS aliases (
    alias  TEXT PRIMARY KEY,
    target TEXT NOT NULL
);

-- 开发路线（原有标题层级中的一级至三级标题）
CREATE TABLE IF NOT EXISTS sections (
    id           TEXT PRIMARY KEY,
    seq          INTEGER NOT NULL UNIQUE,
    title        TEXT NOT NULL,
    level        INTEGER NOT NULL,
    parent_id    TEXT REFERENCES sections(id) ON DELETE SET NULL,
    start_number INTEGER NOT NULL DEFAULT 1,
    note         TEXT NOT NULL DEFAULT ''
);

-- 实现目标条目（网络图节点），seq 为跨路线的全局文档顺序
CREATE TABLE IF NOT EXISTS nodes (
    id               TEXT PRIMARY KEY,
    seq              INTEGER NOT NULL UNIQUE,
    section_id       TEXT NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    number           INTEGER NOT NULL,
    summary          TEXT NOT NULL DEFAULT '',
    body             TEXT NOT NULL DEFAULT '',
    manual           TEXT NOT NULL DEFAULT '{}',
    summary_is_auto  INTEGER NOT NULL DEFAULT 1,
    status           TEXT NOT NULL DEFAULT '未实现' CHECK(status IN ('未实现', '实现中', '已实现'))
);

-- 条目声明的依赖引用，target_id 为空表示未解析
CREATE TABLE IF NOT EXISTS node_refs (
    node_id   TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    seq       INTEGER NOT NULL,
    raw       TEXT NOT NULL,
    section   TEXT NOT NULL DEFAULT '',
    number    INTEGER,
    target_id TEXT REFERENCES nodes(id) ON DELETE SET NULL,
    reason    TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (node_id, seq)
);

-- 条目声明需要一并实现的对象，path 可空
CREATE TABLE IF NOT EXISTS node_objects (
    node_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    seq     INTEGER NOT NULL,
    name    TEXT NOT NULL,
    note    TEXT NOT NULL DEFAULT '',
    path    TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (node_id, seq)
);

-- 从正文括号里摘出的说明性长文本，不参与成图
CREATE TABLE IF NOT EXISTS node_notes (
    node_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    seq     INTEGER NOT NULL,
    text    TEXT NOT NULL,
    PRIMARY KEY (node_id, seq)
);

-- 整模型快照，按时间限流写入，滚动保留最近 SNAPSHOT_KEEP 份
CREATE TABLE IF NOT EXISTS snapshots (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at   TEXT NOT NULL,
    created_unix REAL NOT NULL,
    reason       TEXT NOT NULL DEFAULT '',
    payload      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_nodes_section ON nodes(section_id, seq);
CREATE INDEX IF NOT EXISTS idx_refs_target ON node_refs(target_id);

-- 路线视图：补出章节路径与条目数
CREATE VIEW IF NOT EXISTS v_section AS
WITH RECURSIVE tree(id, path, depth) AS (
    SELECT s.id, s.title, 0
    FROM sections s
    WHERE s.parent_id IS NULL OR s.parent_id = ''
    UNION ALL
    SELECT c.id, t.path || '/' || c.title, t.depth + 1
    FROM sections c
    JOIN tree t ON c.parent_id = t.id
    WHERE t.depth < 8
)
SELECT s.id,
       s.seq,
       s.title,
       s.level,
       s.parent_id,
       s.start_number,
       s.note,
       COALESCE(t.path, s.title) AS path,
       (SELECT COUNT(*) FROM nodes n WHERE n.section_id = s.id) AS node_count
FROM sections s
LEFT JOIN (SELECT id, MIN(path) AS path FROM tree GROUP BY id) t ON t.id = s.id;

-- 条目视图：补出章节路径、编号索引与子项计数
CREATE VIEW IF NOT EXISTS v_node AS
SELECT n.id,
       n.seq,
       n.section_id,
       s.path AS section_path,
       s.path || ' ' || n.number AS index_label,
       n.number,
       n.summary,
       n.body,
       n.summary_is_auto,
       n.manual,
       n.status,
       CASE WHEN n.manual IS NULL OR n.manual IN ('', '{}') THEN 1 ELSE 0 END AS auto_position,
       (SELECT COUNT(*) FROM node_refs r WHERE r.node_id = n.id) AS ref_count,
       (SELECT COUNT(*) FROM node_refs r WHERE r.node_id = n.id AND r.target_id IS NULL) AS unresolved_ref_count,
       (SELECT COUNT(*) FROM node_objects o WHERE o.node_id = n.id) AS object_count,
       (SELECT COUNT(*) FROM node_notes t WHERE t.node_id = n.id) AS note_count
FROM nodes n
JOIN v_section s ON s.id = n.section_id;

-- 引用视图：解析结果与未解析原因
CREATE VIEW IF NOT EXISTS v_ref AS
SELECT r.node_id,
       n.index_label AS node_index_label,
       r.seq,
       r.raw,
       r.section AS raw_section,
       r.number AS raw_number,
       r.target_id,
       t.index_label AS target_index_label,
       CASE WHEN r.target_id IS NULL THEN 0 ELSE 1 END AS resolved,
       r.reason
FROM node_refs r
JOIN v_node n ON n.id = r.node_id
LEFT JOIN v_node t ON t.id = r.target_id;

-- 对象视图：对象声明及其宿主条目
CREATE VIEW IF NOT EXISTS v_object AS
SELECT o.node_id,
       n.index_label AS node_index_label,
       n.section_path,
       o.seq,
       o.name,
       o.note,
       o.path,
       CASE WHEN TRIM(COALESCE(o.path, '')) = '' THEN 0 ELSE 1 END AS has_path
FROM node_objects o
JOIN v_node n ON n.id = o.node_id;

-- 依赖边视图：链式边按同路线相邻推导，显式边来自已解析的引用
CREATE VIEW IF NOT EXISTS v_edge AS
WITH chain AS (
    SELECT id AS to_id,
           LAG(id) OVER (PARTITION BY section_id ORDER BY seq) AS from_id
    FROM nodes
),
base AS (
    SELECT from_id, to_id, 'chain' AS kind
    FROM chain
    WHERE from_id IS NOT NULL
    UNION ALL
    SELECT target_id AS from_id, node_id AS to_id, 'explicit' AS kind
    FROM node_refs
    WHERE target_id IS NOT NULL AND target_id <> node_id
),
merged AS (
    SELECT from_id,
           to_id,
           CASE
               WHEN SUM(kind = 'chain') > 0 AND SUM(kind = 'explicit') > 0 THEN 'chain+explicit'
               WHEN SUM(kind = 'explicit') > 0 THEN 'explicit'
               ELSE 'chain'
           END AS kind
    FROM base
    GROUP BY from_id, to_id
)
SELECT m.from_id,
       m.to_id,
       m.kind,
       (SELECT r.raw FROM node_refs r
         WHERE r.target_id = m.from_id AND r.node_id = m.to_id
         ORDER BY r.seq LIMIT 1) AS raw,
       f.index_label AS from_index_label,
       t.index_label AS to_index_label
FROM merged m
JOIN v_node f ON f.id = m.from_id
JOIN v_node t ON t.id = m.to_id;

-- 统计视图：单行汇总，供一屏速览
CREATE VIEW IF NOT EXISTS v_stats AS
SELECT
    (SELECT COUNT(*) FROM sections) AS sections,
    (SELECT COUNT(*) FROM nodes) AS nodes,
    (SELECT COUNT(*) FROM node_refs) AS refs,
    (SELECT COUNT(*) FROM node_refs WHERE target_id IS NULL) AS unresolved_refs,
    (SELECT COUNT(*) FROM node_objects) AS object_rows,
    (SELECT COUNT(DISTINCT name) FROM node_objects) AS object_names,
    (SELECT COUNT(*) FROM node_objects WHERE TRIM(COALESCE(path, '')) = '') AS objects_without_path,
    (SELECT COUNT(DISTINCT name) FROM node_objects WHERE TRIM(COALESCE(path, '')) <> '') AS object_names_with_path,
    (SELECT COUNT(*) FROM node_notes) AS notes,
    (SELECT COUNT(*) FROM v_edge) AS edges,
    (SELECT COUNT(*) FROM v_edge WHERE kind LIKE 'chain%') AS chain_edges,
    (SELECT COUNT(*) FROM v_edge WHERE kind LIKE '%explicit%') AS explicit_edges,
    (SELECT COUNT(*) FROM nodes WHERE id NOT IN (SELECT to_id FROM v_edge)) AS root_nodes,
    (SELECT COUNT(*) FROM snapshots) AS snapshots;
"""


# --------------------------------------------------------------------------
# 连接与结构
# --------------------------------------------------------------------------


def connect(path, readonly: bool = False) -> sqlite3.Connection:
    """打开库连接。只读模式用 URI 打开，任何写入都会被数据库拒绝。

    刻意不使用 WAL 日志模式：只读连接在 WAL 库上需要可写的 -shm 文件，
    本工具会被「服务在跑」与「智能体只读查询」同时使用，默认日志模式更稳。
    """
    target = Path(path)
    if readonly:
        uri = target.resolve().as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn
    conn = sqlite3.connect(str(target), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def exists(path) -> bool:
    return Path(path).is_file() and Path(path).stat().st_size > 0


def ensure_schema(path) -> None:
    """建库或补建缺失的表与视图。已有数据不受影响。"""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(target)
    try:
        conn.executescript(SCHEMA)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(nodes)")}
        if "status" not in columns:
            conn.execute("ALTER TABLE nodes ADD COLUMN status TEXT NOT NULL DEFAULT '未实现' CHECK(status IN ('未实现', '实现中', '已实现'))")
            conn.execute("DROP VIEW IF EXISTS v_node")
            conn.executescript(SCHEMA)
        conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version',?)", (str(SCHEMA_VERSION),))
        conn.commit()
    finally:
        conn.close()


def meta_value(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row is not None else default


# --------------------------------------------------------------------------
# 模型 <-> 载荷
# --------------------------------------------------------------------------


def model_payload(model: M.Model) -> dict:
    """把模型转成可序列化载荷。

    结构与旧版 `数据/项目网络图.json` 同构，`model_from_dict` 可直接读回，
    因此快照既可用于恢复，也可用于人工比对。
    """
    return {
        "title": model.title,
        "source": model.source,
        "preamble": model.preamble,
        "aliases": dict(model.aliases or {}),
        "meta": model.meta if isinstance(model.meta, dict) else {},
        "sections": [
            {
                "id": s.id,
                "title": s.title,
                "level": s.level,
                "parent_id": s.parent_id,
                "start_number": s.start_number,
                "note": s.note,
            }
            for s in model.sections
        ],
        "nodes": [
            {
                "id": n.id,
                "section_id": n.section_id,
                "number": n.number,
                "summary": n.summary,
                "body": n.body,
                "notes": list(n.notes),
                "manual": dict(n.manual or {}),
                "status": M.node_status(n.status),
                "refs": [
                    {
                        "raw": r.raw,
                        "section": r.section,
                        "number": r.number,
                        "target_id": r.target_id,
                        "reason": r.reason,
                    }
                    for r in n.refs
                ],
                "objects": [
                    {"name": o.name, "note": o.note, "path": o.path} for o in n.objects
                ],
            }
            for n in model.nodes
        ],
    }


def load_model_dict(path) -> dict:
    """从库读出模型载荷（不解析引用，保持库内原样）。"""
    conn = connect(path, readonly=True)
    try:
        payload = {
            "title": meta_value(conn, "title"),
            "source": meta_value(conn, "source"),
            "preamble": meta_value(conn, "preamble"),
            "aliases": {
                row["alias"]: row["target"]
                for row in conn.execute("SELECT alias, target FROM aliases ORDER BY alias")
            },
            "meta": _load_model_meta(conn),
            "sections": [],
            "nodes": [],
        }

        refs: dict[str, list[dict]] = {}
        for row in conn.execute(
            "SELECT node_id, raw, section, number, target_id, reason"
            " FROM node_refs ORDER BY node_id, seq"
        ):
            refs.setdefault(row["node_id"], []).append(
                {
                    "raw": row["raw"],
                    "section": row["section"],
                    "number": row["number"],
                    "target_id": row["target_id"],
                    "reason": row["reason"],
                }
            )

        objects: dict[str, list[dict]] = {}
        for row in conn.execute(
            "SELECT node_id, name, note, path FROM node_objects ORDER BY node_id, seq"
        ):
            objects.setdefault(row["node_id"], []).append(
                {"name": row["name"], "note": row["note"], "path": row["path"]}
            )

        notes: dict[str, list[str]] = {}
        for row in conn.execute(
            "SELECT node_id, text FROM node_notes ORDER BY node_id, seq"
        ):
            notes.setdefault(row["node_id"], []).append(row["text"])

        for row in conn.execute(
            "SELECT id, title, level, parent_id, start_number, note"
            " FROM sections ORDER BY seq"
        ):
            payload["sections"].append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "level": row["level"],
                    "parent_id": row["parent_id"],
                    "start_number": row["start_number"],
                    "note": row["note"],
                }
            )

        columns = {row["name"] for row in conn.execute("PRAGMA table_info(nodes)")}
        status_column = "status" if "status" in columns else "'未实现' AS status"
        for row in conn.execute(
            "SELECT id, section_id, number, summary, body, manual, " + status_column +
            " FROM nodes ORDER BY seq"
        ):
            payload["nodes"].append(
                {
                    "id": row["id"],
                    "section_id": row["section_id"],
                    "number": row["number"],
                    "summary": row["summary"],
                    "body": row["body"],
                    "notes": notes.get(row["id"], []),
                    "manual": _json_or(row["manual"], {}),
                    "status": row["status"],
                    "refs": refs.get(row["id"], []),
                    "objects": objects.get(row["id"], []),
                }
            )
        return payload
    finally:
        conn.close()


def load_model(path) -> M.Model:
    """从库读出模型，并按现行规则重新解析引用。"""
    model = M.model_from_dict(load_model_dict(path))
    M.resolve_refs(model)
    return model


def _load_model_meta(conn: sqlite3.Connection) -> dict:
    meta: dict = {}
    for row in conn.execute("SELECT key, value FROM model_meta"):
        try:
            meta[row["key"]] = json.loads(row["value"])
        except (TypeError, ValueError):
            meta[row["key"]] = row["value"]
    return meta


def _json_or(text, default):
    try:
        value = json.loads(text)
    except (TypeError, ValueError):
        return default
    return value if isinstance(value, type(default)) else default


# --------------------------------------------------------------------------
# 写入
# --------------------------------------------------------------------------


def save_model(
    path,
    model: M.Model,
    reason: str = "",
    backup: bool = True,
    force_snapshot: bool = False,
) -> Path:
    """整模型覆盖写入。写入完成后按需追加一份快照。

    `reason` 记录本次写入来源（操作名或迁移标记），写入 `meta.last_reason`；
    `backup` 为假时不动快照表，用于首次建库。
    """
    # 所有程序写库入口（含导入、恢复历史和外部脚本）统一执行依赖约束。
    M.prune_inherited_dependencies(model)
    target = Path(path)
    ensure_schema(target)
    conn = connect(target)
    try:
        with conn:
            _replace_all(conn, model, reason)
            if backup:
                _maybe_snapshot(conn, model_payload(model), reason, force_snapshot)
    finally:
        conn.close()
    return target


def clean_inherited_dependencies(path, model: M.Model) -> list[dict]:
    """清理旧库时先保存完整旧模型快照，供恢复与核对。"""
    before = model_payload(model)
    removed = M.prune_inherited_dependencies(model)
    if removed:
        append_snapshot(path, before, reason="上游依赖约束清理前")
        save_model(path, model, reason=f"上游依赖约束清理 {len(removed)} 条", force_snapshot=True)
    return removed


def _replace_all(conn: sqlite3.Connection, model: M.Model, reason: str) -> None:
    cur = conn.cursor()
    cur.execute("DELETE FROM node_refs")
    cur.execute("DELETE FROM node_objects")
    cur.execute("DELETE FROM node_notes")
    cur.execute("DELETE FROM nodes")
    cur.execute("DELETE FROM sections")
    cur.execute("DELETE FROM aliases")
    cur.execute("DELETE FROM model_meta")

    section_ids = {s.id for s in model.sections}
    for index, section in enumerate(model.sections, 1):
        cur.execute(
            "INSERT INTO sections (id, seq, title, level, parent_id, start_number, note)"
            " VALUES (?,?,?,?,NULL,?,?)",
            (
                section.id,
                index,
                section.title,
                int(section.level),
                int(section.start_number),
                section.note or "",
            ),
        )
    # 父级单独回填：允许父级在文件中排在子级之后
    for section in model.sections:
        if section.parent_id and section.parent_id in section_ids:
            cur.execute(
                "UPDATE sections SET parent_id = ? WHERE id = ?",
                (section.parent_id, section.id),
            )

    node_ids = {n.id for n in model.nodes}
    for index, node in enumerate(model.nodes, 1):
        if node.section_id not in section_ids:
            raise ValueError(
                "条目 {} 指向不存在的开发路线 {}，请先修复模型再存档".format(
                    node.id, node.section_id
                )
            )
        cur.execute(
            "INSERT INTO nodes (id, seq, section_id, number, summary, body, manual,"
            " summary_is_auto, status) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                node.id,
                index,
                node.section_id,
                int(node.number),
                node.summary or "",
                node.body or "",
                json.dumps(dict(node.manual or {}), ensure_ascii=False),
                1 if node.summary_is_auto else 0,
                M.node_status(node.status),
            ),
        )

    for node in model.nodes:
        for index, ref in enumerate(node.refs, 1):
            target_id = ref.target_id if ref.target_id in node_ids else None
            cur.execute(
                "INSERT INTO node_refs (node_id, seq, raw, section, number, target_id, reason)"
                " VALUES (?,?,?,?,?,?,?)",
                (
                    node.id,
                    index,
                    ref.raw or "",
                    ref.section or "",
                    ref.number,
                    target_id,
                    ref.reason or "",
                ),
            )
        for index, obj in enumerate(node.objects, 1):
            cur.execute(
                "INSERT INTO node_objects (node_id, seq, name, note, path)"
                " VALUES (?,?,?,?,?)",
                (node.id, index, obj.name or "", obj.note or "", obj.path or ""),
            )
        for index, text in enumerate(node.notes, 1):
            cur.execute(
                "INSERT INTO node_notes (node_id, seq, text) VALUES (?,?,?)",
                (node.id, index, str(text)),
            )

    for alias, value in (model.aliases or {}).items():
        cur.execute(
            "INSERT OR REPLACE INTO aliases (alias, target) VALUES (?,?)",
            (str(alias), str(value)),
        )
    for key, value in (model.meta or {}).items():
        cur.execute(
            "INSERT OR REPLACE INTO model_meta (key, value) VALUES (?,?)",
            (str(key), json.dumps(value, ensure_ascii=False)),
        )

    rows = {
        "schema_version": str(SCHEMA_VERSION),
        "tool": TOOL_NAME,
        "title": model.title or "",
        "source": model.source or "",
        "preamble": model.preamble or "",
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "last_reason": reason or "",
    }
    for key, value in rows.items():
        cur.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?,?)", (key, str(value))
        )


def _maybe_snapshot(
    conn: sqlite3.Connection, payload: dict, reason: str, force: bool
) -> int | None:
    now = time.time()
    if not force:
        row = conn.execute(
            "SELECT created_unix FROM snapshots ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is not None and now - float(row["created_unix"]) < SNAPSHOT_INTERVAL_SECONDS:
            return None
    cur = conn.execute(
        "INSERT INTO snapshots (created_at, created_unix, reason, payload) VALUES (?,?,?,?)",
        (
            time.strftime("%Y-%m-%d %H:%M:%S"),
            now,
            reason or "",
            json.dumps(payload, ensure_ascii=False),
        ),
    )
    conn.execute(
        "DELETE FROM snapshots WHERE id NOT IN"
        " (SELECT id FROM snapshots ORDER BY id DESC LIMIT ?)",
        (SNAPSHOT_KEEP,),
    )
    return int(cur.lastrowid)


def list_snapshots(path) -> list[dict]:
    """列出快照清单（不含正文），按时间倒序。"""
    conn = connect(path, readonly=True)
    try:
        return [
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "reason": row["reason"],
                "bytes": len(row["payload"] or ""),
            }
            for row in conn.execute(
                "SELECT id, created_at, reason, payload FROM snapshots ORDER BY id DESC"
            )
        ]
    finally:
        conn.close()


def restore_snapshot(path, snapshot_id: int | None = None) -> M.Model:
    """用指定快照恢复库；不给编号时取最近一份。

    恢复前先把当前数据追加成一份快照，因此恢复动作本身也可以再回退。
    """
    conn = connect(path, readonly=True)
    try:
        if snapshot_id is None:
            row = conn.execute(
                "SELECT id, payload FROM snapshots ORDER BY id DESC LIMIT 1"
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT id, payload FROM snapshots WHERE id = ?", (int(snapshot_id),)
            ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise ValueError("没有可用的快照")
    model = M.model_from_dict(json.loads(row["payload"]))
    M.resolve_refs(model)
    before = model_payload(load_model(path))
    save_model(
        path,
        model,
        reason="恢复快照 #{}".format(row["id"]),
        backup=True,
        force_snapshot=True,
    )
    append_snapshot(path, before, "恢复快照 #{} 前的状态".format(row["id"]))
    return model


def append_snapshot(path, payload: dict, reason: str = "") -> None:
    """无条件追加一份整模型载荷快照（写入侧用途，例如恢复前的留底）。"""
    conn = connect(path)
    try:
        with conn:
            _maybe_snapshot(conn, payload, reason, True)
    finally:
        conn.close()


# --------------------------------------------------------------------------
# 自检
# --------------------------------------------------------------------------


def verify(path) -> dict:
    """校验结构与引用完整性，返回可打印的自检结果。读不出结构时返回 error 字段。"""
    result: dict = {"path": str(path), "sqlite_version": sqlite3.sqlite_version}
    if not exists(path):
        result["exists"] = False
        return result
    conn = connect(path, readonly=True)
    try:
        return _verify_conn(conn, result)
    except sqlite3.DatabaseError as exc:
        result["exists"] = True
        result["error"] = str(exc)
        return result
    finally:
        conn.close()


def _verify_conn(conn: sqlite3.Connection, result: dict) -> dict:
    tables = {
        r["name"]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    views = {
        r["name"]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'view'")
    }
    result["exists"] = True
    result["missing_tables"] = sorted(set(REQUIRED_TABLES) - tables)
    result["missing_views"] = sorted(set(REQUIRED_VIEWS) - views)
    result["integrity"] = conn.execute("PRAGMA integrity_check").fetchone()[0]
    result["foreign_key_errors"] = len(list(conn.execute("PRAGMA foreign_key_check")))
    result["schema_version"] = meta_value(conn, "schema_version")
    result["updated_at"] = meta_value(conn, "updated_at")
    if result["missing_tables"]:
        return result
    stats = conn.execute("SELECT * FROM v_stats").fetchone()
    result["stats"] = {key: stats[key] for key in stats.keys()}
    result["duplicate_numbers"] = conn.execute(
        "SELECT COUNT(*) FROM (SELECT section_id, number FROM nodes"
        " GROUP BY section_id, number HAVING COUNT(*) > 1)"
    ).fetchone()[0]
    result["nodes_without_section"] = conn.execute(
        "SELECT COUNT(*) FROM nodes n LEFT JOIN sections s ON s.id = n.section_id"
        " WHERE s.id IS NULL"
    ).fetchone()[0]
    result["refs_without_node"] = conn.execute(
        "SELECT COUNT(*) FROM node_refs r LEFT JOIN nodes n ON n.id = r.node_id"
        " WHERE n.id IS NULL"
    ).fetchone()[0]
    result["snapshot_span"] = conn.execute(
        "SELECT COALESCE(MIN(created_at), '') || ' ~ ' || COALESCE(MAX(created_at), '')"
        " FROM snapshots"
    ).fetchone()[0]
    return result


def schema_report(path) -> dict:
    """列出表与视图及其列定义，供读取方低成本了解库结构。"""
    conn = connect(path, readonly=True)
    try:
        report: dict = {"tables": {}, "views": {}}
        for kind, key in (("table", "tables"), ("view", "views")):
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = ? ORDER BY name", (kind,)
            ):
                name = row["name"]
                if name.startswith("sqlite_"):
                    continue
                report[key][name] = [
                    {
                        "name": col["name"],
                        "type": col["type"],
                        "notnull": bool(col["notnull"]),
                        "pk": bool(col["pk"]),
                    }
                    for col in conn.execute('PRAGMA table_info("{}")'.format(name))
                ]
        return report
    finally:
        conn.close()


# --------------------------------------------------------------------------
# CLI（存档侧：自检、快照、恢复）
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(description="项目网络图库：自检、快照与恢复")
    parser.add_argument("--check", metavar="DB", help="校验库结构与引用完整性")
    parser.add_argument("--schema", metavar="DB", help="列出表与视图的列定义")
    parser.add_argument("--snapshots", metavar="DB", help="列出快照清单")
    parser.add_argument("--restore", metavar="DB", help="用快照恢复库")
    parser.add_argument("--snapshot-id", type=int, default=None, help="恢复时指定的快照编号")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = parser.parse_args(argv)

    targets = [args.check, args.schema, args.snapshots, args.restore]
    if not any(targets):
        parser.print_help()
        return 2

    if args.check:
        _emit(verify(args.check), args.json)
    if args.schema:
        _emit(schema_report(args.schema), args.json)
    if args.snapshots:
        _emit({"snapshots": list_snapshots(args.snapshots)}, args.json)
    if args.restore:
        model = restore_snapshot(args.restore, args.snapshot_id)
        _emit(
            {
                "restored": True,
                "path": args.restore,
                "sections": len(model.sections),
                "nodes": len(model.nodes),
            },
            args.json,
        )
    return 0


def _emit(value, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, dict):
                print("{}:".format(key))
                for k, v in item.items():
                    print("    {} = {}".format(k, v))
            else:
                print("{}: {}".format(key, item))
        return
    print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
