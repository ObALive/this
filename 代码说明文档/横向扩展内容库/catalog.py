"""代码扩展目录管理工具。Python 3.11 标准库即可；不读写 Unity 运行数据。"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import seed

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parents[2] / "mygame"
DEFAULT_DB = HERE / "横向扩展内容.sqlite"
STATUSES = ("已实现", "部分实现", "仅声明", "待实现", "已废弃")
COMMON = {
    "id": "TEXT PRIMARY KEY",
    "code_name": "TEXT NOT NULL UNIQUE",
    "display_name": "TEXT NOT NULL",
    "summary": "TEXT NOT NULL",
    "status": "TEXT NOT NULL CHECK(status IN ('已实现','部分实现','仅声明','待实现','已废弃'))",
    "extension_steps": "TEXT NOT NULL DEFAULT ''",
    "limitations": "TEXT NOT NULL DEFAULT ''",
    "evidence_json": "TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(evidence_json))",
    "reference_doc": "TEXT NOT NULL DEFAULT ''",
    "baseline_commit": "TEXT NOT NULL DEFAULT ''",
    "verified_at": "TEXT NOT NULL DEFAULT ''",
    "managed": "INTEGER NOT NULL DEFAULT 0 CHECK(managed IN (0,1))",
    "notes": "TEXT NOT NULL DEFAULT ''",
    "owner": "TEXT NOT NULL DEFAULT ''",
    "priority": "INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 0 AND 3)",
    "created_at": "TEXT NOT NULL",
    "updated_at": "TEXT NOT NULL",
}
PROTECTED = {"notes", "owner", "priority", "created_at"}


def now():
    # Windows 可能没有 IANA tzdata；上海无夏令时，显式使用 UTC+8。
    from datetime import timedelta, timezone
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def q(name):
    return '"' + name.replace('"', '""') + '"'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def code_only(text):
    """去掉注释但保留行号和字符串，避免把注释示例识别成代码。不是完整 C# 解析器。"""
    pattern = r'@"(?:""|[^"])*"|"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/'
    return re.sub(pattern, lambda m: re.sub(r'[^\n]', ' ', m[0]) if m[0].startswith(('//', '/*')) else m[0], text)


def source_index(root):
    return {p.relative_to(root).as_posix(): code_only(p.read_text(encoding="utf-8-sig"))
            for p in sorted((root / "Assets/Script").rglob("*.cs"))}


def evidence(root, spec):
    path = root / spec[0]
    text = path.read_text(encoding="utf-8-sig")
    searchable = code_only(text) if path.suffix == ".cs" else text
    match = re.search(spec[1], searchable, re.M)
    if not match:
        raise ValueError(f"证据未命中：{spec[0]} / {spec[1]}")
    line = searchable[:match.start()].count("\n") + 1
    return {"path": spec[0], "line": line, "pattern": spec[1],
            "excerpt": text.splitlines()[line - 1].strip(), "sha256": digest(path)}


def schema():
    parts = ["PRAGMA foreign_keys = ON;", "PRAGMA user_version = 2;",
             'CREATE TABLE IF NOT EXISTS "_分类" (table_name TEXT PRIMARY KEY, title TEXT NOT NULL, tier TEXT NOT NULL, extension_mode TEXT NOT NULL, entry_rule TEXT NOT NULL, extension_steps TEXT NOT NULL, limitations TEXT NOT NULL);',
             'CREATE TABLE IF NOT EXISTS "_构建信息" (key TEXT PRIMARY KEY, value TEXT NOT NULL);',
             'CREATE TABLE IF NOT EXISTS "_源码快照" (path TEXT PRIMARY KEY, sha256 TEXT NOT NULL);',
             'DROP VIEW IF EXISTS "v_待办";',
             'DROP VIEW IF EXISTS "v_全部条目";',
             'DROP VIEW IF EXISTS "v_操作链";',
             '-- v2：按用户要求移除固定的显示朝向分类，保留其他分类数据。',
             'DROP TABLE IF EXISTS "显示朝向";',
             'DELETE FROM "_分类" WHERE table_name=\'显示朝向\';']
    for name, spec in seed.TABLES.items():
        columns = {**COMMON, **spec.get("columns", {})}
        defs = [q(k) + " " + v for k, v in columns.items()] + spec.get("constraints", [])
        parts.append(f"CREATE TABLE IF NOT EXISTS {q(name)} (\n  " + ",\n  ".join(defs) + "\n);")
        parts.append(f"CREATE INDEX IF NOT EXISTS {q('ix_' + name + '_status')} ON {q(name)}(status);")
    unions = [f"SELECT '{name}' AS category, id, code_name, display_name, summary, status, owner, priority, notes FROM {q(name)}" for name in seed.TABLES]
    parts.append('CREATE VIEW IF NOT EXISTS "v_全部条目" AS ' + "\nUNION ALL\n".join(unions) + ";")
    parts.append('CREATE VIEW IF NOT EXISTS "v_待办" AS SELECT * FROM "v_全部条目" WHERE status IN (\'部分实现\',\'仅声明\',\'待实现\') ORDER BY priority,category,code_name;')
    parts.append('CREATE VIEW IF NOT EXISTS "v_操作链" AS SELECT o.code_name AS operation,o.status,b.code_name AS builder,e.code_name AS executor,o.target_kind_id,o.limitations FROM "报文操作" o JOIN "动作构造器" b ON b.id=o.builder_id JOIN "效果执行器" e ON e.id=o.executor_id;')
    return "\n\n".join(parts) + "\n"


def connect(path, create=False):
    if not create and not path.is_file():
        raise ValueError(f"数据库不存在；默认不新建数据库或表，请先恢复现有库并核对路径：{path}")
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


def upsert(db, table, row, key="id"):
    names = list(row)
    updates = [f"{q(k)}=excluded.{q(k)}" for k in names if k not in PROTECTED | {key}]
    db.execute(f"INSERT INTO {q(table)} ({','.join(map(q,names))}) VALUES ({','.join('?' for _ in names)}) ON CONFLICT({q(key)}) DO UPDATE SET {','.join(updates)}", [row[k] for k in names])


def build(root, path, allow_new_tables=()):
    # 常规文档更新只能维护既有类别；新增类别需有用户逐表批准。
    # 在核对、DDL、导出之前拒绝，避免种子新增分类时自动建表。
    existing_db = connect(path)
    try:
        existing_tables = {row[0] for row in existing_db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        existing_db.close()
    pending = set(seed.TABLES) - existing_tables
    allowed = set(allow_new_tables)
    if allowed - set(seed.TABLES):
        raise ValueError("许可中包含未定义分类：" + ", ".join(sorted(allowed - set(seed.TABLES))))
    if pending - allowed:
        raise ValueError("默认不新建内容表。以下分类需先询问用户并获得明确同意：" + ", ".join(sorted(pending - allowed)))
    records = seed.records(root, source_index(root))
    timestamp = now()
    commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    prepared = []
    for table, data in records:
        item = dict(data)
        item["evidence_json"] = json.dumps([evidence(root, s) for s in item.pop("evidence")], ensure_ascii=False)
        item.update(baseline_commit=commit, verified_at=timestamp, managed=1, created_at=timestamp, updated_at=timestamp)
        prepared.append((table, item))
    # 先解析并核对全部证据，再开始事务；失败不留下半份目录。
    db = connect(path, create=True)
    try:
        db.executescript(schema())
        with db:
            for name, spec in seed.TABLES.items():
                upsert(db, "_分类", dict(table_name=name, title=spec["title"], tier=spec["tier"], extension_mode=spec["mode"], entry_rule=spec["rule"], extension_steps=spec["steps"], limitations=spec["limitations"]), "table_name")
            expected = {}
            for table, item in prepared:
                expected.setdefault(table, set()).add(item["id"])
                existing = db.execute(f"SELECT managed FROM {q(table)} WHERE id=?", (item["id"],)).fetchone()
                if existing and not existing["managed"]:
                    raise ValueError(f"源码条目与人工条目 ID 冲突，请先整理：{table}/{item['id']}")
                upsert(db, table, item)
            # 不删除已移出的种子条目；保留备注并标为已废弃，供人工决定去留。
            for table in seed.TABLES:
                for row in db.execute(f"SELECT id FROM {q(table)} WHERE managed=1").fetchall():
                    if row["id"] not in expected.get(table, set()):
                        db.execute(f"UPDATE {q(table)} SET status='已废弃',updated_at=? WHERE id=?", (timestamp, row["id"]))
            db.execute('DELETE FROM "_源码快照"')
            for relative in source_index(root):
                db.execute('INSERT INTO "_源码快照" VALUES (?,?)', (relative, digest(root / relative)))
            info = {"schema_version": "2", "project_root": str(root), "git_commit": commit, "built_at": timestamp,
                    "scope": "Assets/Script/**/*.cs；证据引用 Assets/GameData 与 Assets/Scenes；不含第三方、示例、Editor 验证工具",
                    "source_of_truth": "源码事实来自 seed.py + 源文件核对；notes/owner/priority 与人工条目保存在数据库；非游戏运行数据库"}
            for key, value in info.items():
                db.execute('INSERT OR REPLACE INTO "_构建信息" VALUES (?,?)', (key, value))
        (HERE / "schema.sql").write_text(schema(), encoding="utf-8")
        export(db)
        print(f"已构建 {path}：{len(seed.TABLES)} 类，{len(prepared)} 个源码条目。")
    finally:
        db.close()


def export(db):
    info = dict(db.execute('SELECT key,value FROM "_构建信息"').fetchall())
    lines = ["# 当前项目代码横向扩展内容归纳", "", f"源码基线：`{info.get('git_commit', '')}`；构建时间：{info.get('built_at', '')}。", "",
             "条目是实现类型、协议成员或技术标识，不是技能资产、角色、装备实例。核心扩展点、旧体系与辅助契约分别标注；辅助有限状态不计作自然增长的内容维度。", "",
             "本文件是数据库导出的阅读快照；修改数据库后运行 `export` 更新。源码证据与文件哈希保存在每行 evidence_json。", "",
             "| 内容表 | 性质 | 当前条目数 | 扩展方式 |", "| --- | --- | ---: | --- |"]
    for name, spec in seed.TABLES.items():
        count = db.execute(f"SELECT count(*) FROM {q(name)}").fetchone()[0]
        lines.append(f"| {name} | {spec['tier']} | {count} | {spec['mode']} |")
    for name, spec in seed.TABLES.items():
        lines += ["", f"## {name}", "", spec["rule"], "", "新增时：" + spec["steps"], "", "当前边界：" + spec["limitations"], ""]
        for row in db.execute(f"SELECT * FROM {q(name)} ORDER BY id"):
            row = dict(row)
            lines += [f"### `{row['code_name']}` · {row['display_name']} · {row['status']}", "", row["summary"], ""]
            extras = {k: v for k, v in row.items() if k not in COMMON and v is not None}
            if extras:
                lines += ["专用字段：" + "；".join(f"`{k}`={v}" for k, v in extras.items()), ""]
            if row["limitations"]:
                lines += ["限制：" + row["limitations"], ""]
            for ev in json.loads(row["evidence_json"]):
                target = Path(info["project_root"]) / ev["path"]
                lines.append(f"- [{ev['path']}:{ev['line']}](<{target.as_posix()}:{ev['line']}>)")
            if row["reference_doc"]:
                lines += ["", "说明参考：" + row["reference_doc"]]
            if row["notes"] or row["owner"]:
                lines += ["", f"维护：owner={row['owner']}；priority={row['priority']}；{row['notes']}"]
            lines.append("")
    (HERE / "内容归纳.md").write_text("\n".join(lines), encoding="utf-8")
    data = {name: [dict(r) for r in db.execute(f"SELECT * FROM {q(name)} ORDER BY id")] for name in seed.TABLES}
    (HERE / "catalog.export.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def verify(db, root):
    errors = []
    integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok": errors.append(integrity)
    errors += [str(tuple(r)) for r in db.execute("PRAGMA foreign_key_check")]
    snapshot = dict(db.execute('SELECT path,sha256 FROM "_源码快照"').fetchall())
    current = source_index(root)
    for path in sorted(set(snapshot) | set(current)):
        if path not in snapshot: errors.append("新增源码（需复核目录）: " + path)
        elif path not in current: errors.append("源码已删除: " + path)
        elif digest(root / path) != snapshot[path]: errors.append("源码已变化: " + path)
    for table in seed.TABLES:
        for row in db.execute(f"SELECT * FROM {q(table)} WHERE managed=1 AND status!='已废弃'"):
            if not json.loads(row["evidence_json"]): errors.append(f"无证据: {table}/{row['id']}")
            for ev in json.loads(row["evidence_json"]):
                path = root / ev["path"]
                if not path.is_file() or digest(path) != ev["sha256"]:
                    errors.append(f"证据文件已变化或缺失: {table}/{row['id']} {ev['path']}")
                else:
                    fresh = evidence(root, (ev["path"], ev["pattern"]))
                    if fresh["line"] != ev["line"]: errors.append(f"证据行变化: {table}/{row['id']}")
    # 重新跑发现与人工说明的集合对照，禁止新类型悄悄漏入库。
    try:
        fresh_records = seed.records(root, current)
        for table, item in fresh_records:
            if not db.execute(f"SELECT 1 FROM {q(table)} WHERE id=? AND managed=1 AND status!='已废弃'", (item["id"],)).fetchone():
                errors.append(f"缺少源码条目: {table}/{item['id']}")
    except ValueError as exc:
        errors.append(str(exc))
    if errors:
        print(json.dumps({"ok": False, "errors": sorted(set(errors))}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"ok": True, "integrity": integrity, "foreign_keys": "ok", "source_files": len(current),
                      "content_tables": len(seed.TABLES), "rows": db.execute('SELECT count(*) FROM "v_全部条目"').fetchone()[0]}, ensure_ascii=False))
    return 0


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--project-root", type=Path, default=DEFAULT_ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    builder = sub.add_parser("build", help="核对源码、更新既有表，保留备注/负责人/优先级/人工条目")
    builder.add_argument("--allow-new-table", action="append", default=[], metavar="表名", help="仅在用户明确批准该分类后使用；可逐表重复指定")
    sub.add_parser("verify", help="检查完整性、外键、源码漂移与目录覆盖")
    sub.add_parser("export", help="导出数据库为 Markdown 和 JSON")
    sub.add_parser("tables", help="列出分类和数量")
    ls = sub.add_parser("list"); ls.add_argument("table", choices=list(seed.TABLES)); ls.add_argument("--status", choices=STATUSES)
    show = sub.add_parser("show"); show.add_argument("table", choices=list(seed.TABLES)); show.add_argument("id")
    for command in ("add", "update"):
        cmd = sub.add_parser(command)
        cmd.add_argument("table", choices=list(seed.TABLES)); cmd.add_argument("id")
        cmd.add_argument("--data", type=Path, required=True, help="UTF-8 JSON 对象文件")
    args = parser.parse_args()
    if args.command == "build":
        build(args.project_root.resolve(), args.db.resolve(), args.allow_new_table); return 0
    db = connect(args.db.resolve())
    try:
        if args.command == "verify": return verify(db, args.project_root.resolve())
        if args.command == "export": export(db); print("已导出内容归纳.md 和 catalog.export.json"); return 0
        if args.command == "tables":
            rows = [dict(table=name, tier=spec["tier"], count=db.execute(f"SELECT count(*) FROM {q(name)}").fetchone()[0]) for name, spec in seed.TABLES.items()]
        elif args.command == "list":
            sql = f"SELECT id,code_name,display_name,status,priority,owner FROM {q(args.table)}"
            rows = [dict(r) for r in db.execute(sql + (" WHERE status=?" if args.status else "") + " ORDER BY id", (args.status,) if args.status else ())]
        elif args.command == "show":
            row = db.execute(f"SELECT * FROM {q(args.table)} WHERE id=?", (args.id,)).fetchone()
            if not row: raise ValueError("条目不存在")
            rows = dict(row)
            rows["evidence_json"] = json.loads(rows["evidence_json"])
        else:
            data = json.loads(args.data.read_text(encoding="utf-8-sig"))
            if not isinstance(data, dict) or not data: raise ValueError("--data 必须是非空 JSON 对象")
            columns = {r["name"] for r in db.execute(f"PRAGMA table_info({q(args.table)})")}
            if set(data) - columns: raise ValueError("未知字段: " + str(sorted(set(data) - columns)))
            if set(data) & {"id", "managed", "created_at", "updated_at", "baseline_commit", "verified_at", "evidence_json"}:
                raise ValueError("不能人工修改身份、源码证据与审核字段")
            existing = db.execute(f"SELECT managed FROM {q(args.table)} WHERE id=?", (args.id,)).fetchone()
            with db:
                if args.command == "add":
                    if existing: raise ValueError("条目已存在")
                    item = dict(data, id=args.id, created_at=now(), updated_at=now(), managed=0)
                    item.setdefault("code_name", args.id)
                    item.setdefault("status", "待实现")
                    fields = list(item)
                    db.execute(f"INSERT INTO {q(args.table)} ({','.join(map(q,fields))}) VALUES ({','.join('?' for _ in fields)})", [item[k] for k in fields])
                else:
                    if not existing: raise ValueError("条目不存在")
                    if existing["managed"] and set(data) - {"notes", "owner", "priority"}:
                        raise ValueError("源码条目只能改 notes/owner/priority；事实变更请修改 seed.py 并 build")
                    data["updated_at"] = now()
                    db.execute(f"UPDATE {q(args.table)} SET " + ','.join(f'{q(k)}=?' for k in data) + ' WHERE id=?', [*data.values(), args.id])
            print("已保存。运行 export 更新阅读快照。"); return 0
        print(json.dumps(rows, ensure_ascii=False, indent=2)); return 0
    finally:
        db.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, sqlite3.Error) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
