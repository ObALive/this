"""项目网络图的本地存档。

- 定位工作区根目录；
- 首次启动时从默认任务书（Task/CO系列任务/CO05.md）导入初始网络图；
- 每次编辑自动保存，并滚动保留最近的备份。
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import model as M

TOOL_DIR = Path(__file__).resolve().parent
DATA_DIR = TOOL_DIR / "数据"
BACKUP_DIR = DATA_DIR / "备份"
EXPORT_DIR = DATA_DIR / "导出"
DATA_FILE = DATA_DIR / "项目网络图.json"

DEFAULT_SOURCE = "Task/CO系列任务/CO05.md"
BACKUP_INTERVAL_SECONDS = 120
BACKUP_KEEP = 30


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
    """读取本地存档；没有存档时用默认任务书初始化。"""
    ensure_dirs()
    if DATA_FILE.exists():
        try:
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            m = M.model_from_dict(data)
            if m.nodes or m.sections:
                M.resolve_refs(m)
                return m
        except (json.JSONDecodeError, KeyError, TypeError):
            # 存档损坏时不覆盖，改名留档后重新初始化
            broken = DATA_FILE.with_suffix(f".broken-{int(time.time())}.json")
            DATA_FILE.replace(broken)
    source = default_source_path()
    if source.exists():
        m = import_from(relative_to_workspace(source))
    else:
        m = M.Model(title="项目网络图")
    save(m, backup=False)
    return m


def save(m: M.Model, backup: bool = True) -> Path:
    ensure_dirs()
    payload = {
        "title": m.title,
        "source": m.source,
        "preamble": m.preamble,
        "aliases": m.aliases,
        "meta": m.meta,
        "sections": [s.to_dict() for s in m.sections],
        "nodes": [
            {
                "id": n.id,
                "section_id": n.section_id,
                "number": n.number,
                "summary": n.summary,
                "body": n.body,
                "notes": n.notes,
                "manual": n.manual,
                "refs": [
                    {"raw": r.raw, "section": r.section, "number": r.number, "target_id": r.target_id}
                    for r in n.refs
                ],
                "objects": [{"name": o.name, "note": o.note, "path": o.path} for o in n.objects],
            }
            for n in m.nodes
        ],
    }
    tmp = DATA_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(DATA_FILE)
    if backup:
        _backup(payload)
    return DATA_FILE


def _backup(payload: dict) -> None:
    ensure_dirs()
    existing = sorted(BACKUP_DIR.glob("项目网络图_*.json"))
    if existing:
        newest = existing[-1]
        if time.time() - newest.stat().st_mtime < BACKUP_INTERVAL_SECONDS:
            return
    stamp = time.strftime("%Y%m%d_%H%M%S")
    (BACKUP_DIR / f"项目网络图_{stamp}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for old in sorted(BACKUP_DIR.glob("项目网络图_*.json"))[:-BACKUP_KEEP]:
        old.unlink(missing_ok=True)


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
    return {
        "workspace": str(WORKSPACE),
        "data_file": relative_to_workspace(DATA_FILE),
        "export_dir": relative_to_workspace(EXPORT_DIR),
        "backup_dir": relative_to_workspace(BACKUP_DIR),
        "default_source": DEFAULT_SOURCE,
        "default_source_exists": default_source_path().exists(),
    }
