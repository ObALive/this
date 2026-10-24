"""统一数据目录：一图一库，切换、新建、只读导入与可恢复删除。"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from pathlib import Path

import db
import model as M
import store


class Catalog:
    def __init__(self, directory: Path):
        self.directory = directory.resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.settings = self.directory / "数据管理.json"
        self.active_id: str | None = None

    def path(self, dataset_id: str) -> Path:
        if not isinstance(dataset_id, str) or Path(dataset_id).name != dataset_id or not dataset_id.endswith(".sqlite"):
            raise ValueError("无效的数据名称")
        target = (self.directory / dataset_id).resolve()
        if target.parent != self.directory:
            raise ValueError("数据必须位于统一数据目录内")
        return target

    def entries(self) -> list[dict]:
        entries = []
        for candidate in sorted(self.directory.glob("*.sqlite"), key=lambda p: p.name.casefold()):
            try:
                target = self.path(candidate.name)
                conn = db.connect(target, readonly=True)
                try:
                    # 只列出网络图库，避免把其他应用的 SQLite 文件当作图。
                    conn.execute("SELECT id FROM nodes LIMIT 1")
                    conn.execute("SELECT id FROM sections LIMIT 1")
                    title = db.meta_value(conn, "title") or target.stem
                    count = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
                finally:
                    conn.close()
                entries.append({"id": target.name, "title": title, "nodes": count})
            except (ValueError, sqlite3.DatabaseError, OSError):
                continue
        return entries

    def remember(self) -> None:
        temporary = self.settings.with_suffix(".tmp")
        temporary.write_text(json.dumps({"active_id": self.active_id}, ensure_ascii=False), encoding="utf-8")
        temporary.replace(self.settings)

    def select(self, dataset_id: str) -> M.Model:
        target = self.path(dataset_id)
        if not target.is_file():
            raise ValueError("数据不存在，请刷新数据列表")
        db.ensure_schema(target)
        model = db.load_model(target)
        db.clean_inherited_dependencies(target, model)
        self.active_id = dataset_id
        store.DB_FILE = target
        self.remember()
        return model

    def unique_path(self, name: str) -> Path:
        stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name.strip()).strip(" .")[:80]
        if not stem:
            raise ValueError("请输入数据名称")
        if stem.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(10)], *[f"LPT{i}" for i in range(10)]}:
            stem = "网络图_" + stem
        target = self.path(stem + ".sqlite")
        if target.exists():
            target = self.path(f"{stem}-{uuid.uuid4().hex[:8]}.sqlite")
        return target

    def create(self, title: str) -> M.Model:
        if not isinstance(title, str) or not title.strip():
            raise ValueError("请输入数据名称")
        target = self.unique_path(title)
        db.save_model(target, M.Model(title=title.strip()), reason="新建网络图", backup=False)
        return self.select(target.name)

    def add_existing(self, source: Path) -> M.Model:
        source = source.resolve()
        if not source.is_file() or source.suffix.lower() != ".sqlite":
            raise ValueError("请选择已有的网络图 .sqlite 文件")
        # 先验证，再用 SQLite backup 获取完整一致副本；原库保持只读。
        db.load_model(source)
        if source.parent == self.directory:
            return self.select(source.name)
        target = self.unique_path(source.stem)
        original = db.connect(source, readonly=True)
        copy = sqlite3.connect(target)
        try:
            original.backup(copy)
        finally:
            copy.close()
            original.close()
        return self.select(target.name)

    def delete(self, dataset_id: str) -> M.Model | None:
        target = self.path(dataset_id)
        if not target.is_file():
            raise ValueError("数据不存在，请刷新数据列表")
        # 关闭 db 连接后移动整库，不在删除过程中重建或覆盖任何已有数据。
        db.load_model(target)
        deleted = self.directory / "已删除"
        deleted.mkdir(exist_ok=True)
        destination = deleted / f"{target.stem}-{uuid.uuid4().hex[:8]}.sqlite"
        target.replace(destination)
        if self.active_id == dataset_id:
            self.active_id = None
            entries = self.entries()
            if entries:
                return self.select(entries[0]["id"])
            self.remember()
        return None

    def info(self) -> dict:
        return {"data_dir": str(self.directory), "datasets": self.entries(), "active_dataset": self.active_id}

    def initialize(self, initial: Path) -> M.Model | None:
        # 兼容旧启动入口；外部库只复制一次，随后通过界面选择。
        initial = initial.resolve()
        if initial.is_file() and initial.parent != self.directory:
            existing = self.directory / initial.name
            if existing.is_file():
                return self.select(existing.name)
            return self.add_existing(initial)
        if self.settings.exists():
            try:
                selected = json.loads(self.settings.read_text(encoding="utf-8")).get("active_id")
                if selected and self.path(selected).is_file():
                    return self.select(selected)
            except (ValueError, OSError, sqlite3.DatabaseError):
                pass
            entries = self.entries()
            return self.select(entries[0]["id"]) if entries else None
        entries = self.entries()
        if entries:
            selected = initial.name if any(e["id"] == initial.name for e in entries) else entries[0]["id"]
            return self.select(selected)
        store.DB_FILE = self.directory / "项目网络图.sqlite"
        model = store.load_or_seed()
        self.active_id = store.DB_FILE.name
        self.remember()
        return model


def initialize() -> tuple[Catalog, M.Model | None]:
    initial = store.DB_FILE
    directory = Path(os.environ.get("PN_DATA_DIR") or (store.TOOL_DIR / "数据"))
    store.DATA_DIR = directory
    store.BACKUP_DIR = directory / "备份"
    store.EXPORT_DIR = directory / "导出"
    catalog = Catalog(directory)
    return catalog, catalog.initialize(initial)
