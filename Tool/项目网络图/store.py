"""项目网络图的本地存档。

- 定位工作区根目录；
- 数据存放在 SQLite 库 `数据/项目网络图.sqlite`（结构见 db.py，读取方式见 读库说明.md）；
- 首次启动时按「旧 JSON 存档 → 默认任务书」的顺序初始化；
- 每次编辑自动写入库，并按时间限流追加整模型快照，滚动保留最近若干份；
- 旧版 `数据/项目网络图.json` 与 `数据/备份/*.json` 只作为迁移来源保留，不再更新。
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

import db
import model as M

TOOL_DIR = Path(__file__).resolve().parent
DATA_DIR = TOOL_DIR / "数据"
BACKUP_DIR = DATA_DIR / "备份"          # 旧版 JSON 备份目录，仅保留历史文件
EXPORT_DIR = DATA_DIR / "导出"
DB_FILE = Path(os.environ.get("PN_DB") or (DATA_DIR / "项目网络图.sqlite"))
LEGACY_JSON_FILE = DATA_DIR / "项目网络图.json"

DEFAULT_SOURCE = "Task/CO系列任务/CO05.md"
BACKUP_INTERVAL_SECONDS = db.SNAPSHOT_INTERVAL_SECONDS
BACKUP_KEEP = db.SNAPSHOT_KEEP


def find_workspace(start: Path | None = None) -> Path:
    """向上寻找同时含 Task/ 与 Rules/ 的目录，作为工作区根。"""
    cur = (start or TOOL_DIR).resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / "Task").is_dir() and (candidate / "Rules").is_dir():
            return candidate
    return Path.cwd()


WORKSPACE = find_workspace()


def resolve_in_workspace(relative: str, must_exist: bool = False) -> Path:
    """把用户输入的相对路径限制在工作区内。"""
    raw = (relative or "").strip().strip('"').strip("'")
    if not raw:
        raise ValueError("路径为空")
    path = Path(raw)
    if not path.is_absolute():
        path = WORKSPACE / path
    path = path.resolve()
    try:
        path.relative_to(WORKSPACE)
    except ValueError:
        raise ValueError(f"只允许访问工作区内的路径：{WORKSPACE}")
    if must_exist and not path.exists():
        raise ValueError(f"文件不存在：{path}")
    return path


def relative_to_workspace(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(WORKSPACE))
    except ValueError:
        return str(path)


def default_source_path() -> Path:
    candidate = WORKSPACE / DEFAULT_SOURCE
    return candidate


def ensure_dirs() -> None:
    for d in (DATA_DIR, BACKUP_DIR, EXPORT_DIR):
        d.mkdir(parents=True, exist_ok=True)


def import_from(relative_path: str | None = None, text: str | None = None) -> M.Model:
    """从任务书导入模型。给定文本时按文本解析，否则读文件。"""
    if text is not None:
        source = relative_path or "（粘贴的文本）"
        return M.parse_markdown(text, source=source)
    path = resolve_in_workspace(relative_path or DEFAULT_SOURCE, must_exist=True)
    content = path.read_text(encoding="utf-8")
    return M.parse_markdown(content, source=relative_to_workspace(path))


def load_or_seed() -> M.Model:
    """读取库；没有库时按「旧 JSON 存档 → 默认任务书」的顺序初始化。"""
    ensure_dirs()
    if db.exists(DB_FILE):
        try:
            m = db.load_model(DB_FILE)
            db.clean_inherited_dependencies(DB_FILE, m)
            if not m.nodes and not m.sections:
                return m
            if m.nodes or m.sections:
                # 说明归属规则升级后，把库里已存的设计说明归到它点名的对象下（幂等）
                moves = M.reclassify_notes(m)
                if moves:
                    save(m, reason="设计说明归属对象")
                    print(
                        "[项目网络图] 已把 {} 段设计说明归到对应对象下：{}".format(
                            len(moves), "、".join(sorted({x["object"] for x in moves}))
                        ),
                        flush=True,
                    )
                return m
        except sqlite3.DatabaseError as exc:
            # 库损坏时不覆盖原文件，改名留档后重新初始化
            broken = DB_FILE.with_name(
                f"{DB_FILE.stem}.broken-{int(time.time())}{DB_FILE.suffix}"
            )
            DB_FILE.replace(broken)
            print(f"[项目网络图] 库读取失败（{exc}），已改名留档：{broken.name}", flush=True)

    m = _load_legacy_json()
    if m is not None:
        save(m, reason="迁移自旧 JSON 存档", force_snapshot=True)
        return m

    source = default_source_path()
    if source.exists():
        m = import_from(relative_to_workspace(source))
    else:
        m = M.Model(title="项目网络图")
    save(m, backup=False, reason="初始化")
    return m


def _load_legacy_json() -> M.Model | None:
    """读取旧版 JSON 存档，用于一次性迁移。读不出内容时返回 None。"""
    if not LEGACY_JSON_FILE.exists():
        return None
    try:
        data = json.loads(LEGACY_JSON_FILE.read_text(encoding="utf-8"))
        m = M.model_from_dict(data)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"[项目网络图] 旧 JSON 存档无法迁移（{exc}），将按默认任务书重建", flush=True)
        return None
    if not (m.nodes or m.sections):
        return None
    M.resolve_refs(m)
    return m


def save(
    m: M.Model,
    backup: bool = True,
    reason: str = "",
    force_snapshot: bool = False,
) -> Path:
    """把模型整体写入库。backup 为假时不追加快照（用于首次建库）。"""
    ensure_dirs()
    return db.save_model(
        DB_FILE,
        m,
        reason=reason,
        backup=backup,
        force_snapshot=force_snapshot,
    )


def snapshot_current(m: M.Model, reason: str) -> None:
    """给当前模型追加快照（不改库内容），用于清空/覆盖前一类的危险操作留底。"""
    ensure_dirs()
    db.append_snapshot(DB_FILE, db.model_payload(m), reason=reason)


def export_markdown(m: M.Model, relative_path: str | None = None) -> tuple[Path, str]:
    """把当前网络图导出成任务书 Markdown。"""
    ensure_dirs()
    text = M.to_markdown(m)
    if relative_path:
        path = resolve_in_workspace(relative_path)
    else:
        stem = Path(m.source).stem or "项目网络图"
        path = EXPORT_DIR / f"{stem}_项目网络图导出.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path, text


def info() -> dict:
    check = db.verify(DB_FILE) if db.exists(DB_FILE) else {"exists": False}
    return {
        "workspace": str(WORKSPACE),
        "data_file": relative_to_workspace(DB_FILE),
        "db_file": relative_to_workspace(DB_FILE),
        "db_env_override": bool(os.environ.get("PN_DB")),
        "db_exists": bool(check.get("exists")),
        "schema_version": str(check.get("schema_version") or db.SCHEMA_VERSION),
        "snapshots": int((check.get("stats") or {}).get("snapshots") or 0),
        "snapshot_keep": BACKUP_KEEP,
        "snapshot_interval_seconds": BACKUP_INTERVAL_SECONDS,
        "legacy_json": relative_to_workspace(LEGACY_JSON_FILE),
        "legacy_json_exists": LEGACY_JSON_FILE.exists(),
        "export_dir": relative_to_workspace(EXPORT_DIR),
        "backup_dir": relative_to_workspace(BACKUP_DIR),
        "default_source": DEFAULT_SOURCE,
        "default_source_exists": default_source_path().exists(),
    }
