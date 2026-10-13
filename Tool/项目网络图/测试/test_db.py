"""项目网络图 SQLite 存档层测试。

覆盖：整模型往返、视图与模型的一致性、只读约束、快照追加与恢复、结构自检。

运行： python3 Tool/项目网络图/测试/test_db.py
或在工具目录： python3 -m unittest discover -s 测试 -v
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
sys.path.insert(0, str(TOOL))

import db  # noqa: E402
import model as M  # noqa: E402
import query  # noqa: E402

WORKSPACE = TOOL.parent.parent

SAMPLE_MARKDOWN = """# 角色行为

任务背景说明，不计入网络图。

## 角色移动

0. 四向移动，按格移动
1. 碰撞判定（依赖角色移动0；元对象-地格占用组件，用于占位）

### 移动子路线

1. 子路线上的第一步
2. 子路线上的第二步（依赖角色移动1）

## 地图

1. 地图绘制
2. 障碍（依赖不存在路线1）（这是一段超过二十四个字符的设计方式说明文字用来触发长括号摘出逻辑）
"""


def load_sample() -> M.Model:
    return M.parse_markdown(SAMPLE_MARKDOWN, source="测试用例")


def norm(payload: dict) -> tuple:
    """把载荷压成可比较的结构，忽略派生字段。"""
    sections = [
        (
            s["id"],
            s["title"],
            int(s["level"]),
            s["parent_id"],
            int(s["start_number"]),
            s["note"],
        )
        for s in payload["sections"]
    ]
    nodes = []
    for n in payload["nodes"]:
        nodes.append(
            (
                n["id"],
                n["section_id"],
                int(n["number"]),
                n["summary"],
                n["body"],
                tuple(n["notes"]),
                tuple(sorted((n["manual"] or {}).items())),
                tuple(
                    (r["raw"], r["section"], r["number"], r["target_id"])
                    for r in n["refs"]
                ),
                tuple((o["name"], o["note"], o["path"]) for o in n["objects"]),
            )
        )
    return sections, nodes


class DBTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "项目网络图.sqlite"

    def save(self, model: M.Model, **kwargs):
        return db.save_model(self.path, model, **kwargs)

    def conn(self) -> sqlite3.Connection:
        return db.connect(self.path, readonly=True)


class TestRoundTrip(DBTestCase):
    def test_sample_roundtrip(self):
        model = load_sample()
        model.nodes[0].manual = {"dx": 12, "dy": -4}
        self.save(model)

        payload = db.load_model_dict(self.path)
        self.assertEqual(norm(payload), norm(db.model_payload(model)))

    def test_sample_roundtrip_and_stats(self):
        model = load_sample()
        self.save(model)

        loaded = db.load_model(self.path)
        self.assertEqual(M.validate(loaded)["stats"], M.validate(model)["stats"])
        self.assertEqual(
            [s.title for s in loaded.sections], [s.title for s in model.sections]
        )
        self.assertEqual(len(loaded.nodes), len(model.nodes))

    def test_meta_and_aliases_roundtrip(self):
        model = load_sample()
        model.aliases["地图"] = "瓦片地图"
        model.meta["自定义键"] = {"a": 1}
        self.save(model)

        payload = db.load_model_dict(self.path)
        self.assertEqual(payload["aliases"], {"地图": "瓦片地图"})
        self.assertEqual(payload["meta"]["自定义键"], {"a": 1})
        self.assertEqual(payload["title"], model.title)
        self.assertEqual(payload["preamble"], model.preamble)

    def test_last_reason_written(self):
        self.save(load_sample(), reason="操作 update_node")
        conn = self.conn()
        try:
            self.assertEqual(db.meta_value(conn, "last_reason"), "操作 update_node")
            self.assertEqual(db.meta_value(conn, "schema_version"), str(db.SCHEMA_VERSION))
            self.assertTrue(db.meta_value(conn, "updated_at"))
        finally:
            conn.close()

    def test_overwrite_replaces_rows(self):
        model = load_sample()
        self.save(model)
        before = len(model.nodes)

        model2 = load_sample()
        removed = next(n for n in model2.nodes if n.objects)
        model2.nodes.remove(removed)
        self.save(model2)
        conn = self.conn()
        try:
            count = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            orphans = conn.execute(
                "SELECT COUNT(*) FROM node_objects WHERE node_id = ?", (removed.id,)
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(count, before - 1)
        self.assertEqual(orphans, 0)


class TestViewsMatchModel(DBTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.model = load_sample()
        self.save(self.model)

    def test_index_label(self):
        conn = self.conn()
        try:
            rows = query._rows(conn, "SELECT id, index_label FROM v_node")
        finally:
            conn.close()
        labels = {row["id"]: row["index_label"] for row in rows}
        self.assertEqual(len(labels), len(self.model.nodes))
        for node in self.model.nodes:
            self.assertEqual(labels[node.id], self.model.index_label(node))

    def test_section_path(self):
        conn = self.conn()
        try:
            rows = query._rows(conn, "SELECT id, path, node_count FROM v_section")
        finally:
            conn.close()
        paths = {row["id"]: row["path"] for row in rows}
        for section in self.model.sections:
            expect = "/".join(s.title for s in self.model.section_path(section))
            self.assertEqual(paths[section.id], expect)
            count = len(self.model.section_nodes(section.id))
            self.assertEqual(
                next(r["node_count"] for r in rows if r["id"] == section.id), count
            )

    def test_edges_match_build_edges(self):
        model_edges, _ = M.build_edges(self.model)
        expected = {(e["from"], e["to"], e["kind"]) for e in model_edges}
        expected_raw = {
            (e["from"], e["to"]): e["raw"]
            for e in model_edges
            if "explicit" in e["kind"]
        }

        conn = self.conn()
        try:
            rows = query._rows(conn, "SELECT * FROM v_edge")
        finally:
            conn.close()
        actual = {(r["from_id"], r["to_id"], r["kind"]) for r in rows}
        actual_raw = {
            (r["from_id"], r["to_id"]): (r["raw"] or "")
            for r in rows
            if "explicit" in r["kind"]
        }
        self.assertEqual(expected, actual)
        self.assertEqual(expected_raw, actual_raw)

    def test_refs_view_matches_model(self):
        conn = self.conn()
        try:
            rows = query._rows(conn, "SELECT * FROM v_ref")
        finally:
            conn.close()
        expected = {}
        for node in self.model.nodes:
            for ref in node.refs:
                expected[(node.id, ref.raw)] = ref.target_id
        actual = {(r["node_id"], r["raw"]): r["target_id"] for r in rows}
        self.assertEqual(expected, actual)
        unresolved = sum(1 for r in rows if not r["resolved"])
        stats = M.validate(self.model)["stats"]
        self.assertEqual(unresolved, stats["unresolved_refs"])

    def test_stats_view_matches_model(self):
        conn = self.conn()
        try:
            row = query._rows(conn, "SELECT * FROM v_stats")[0]
        finally:
            conn.close()
        stats = M.validate(self.model)["stats"]
        self.assertEqual(row["sections"], stats["sections"])
        self.assertEqual(row["nodes"], stats["nodes"])
        self.assertEqual(row["edges"], stats["edges"])
        self.assertEqual(row["chain_edges"], stats["chain_edges"])
        self.assertEqual(row["explicit_edges"], stats["explicit_edges"])
        self.assertEqual(row["root_nodes"], stats["root_nodes"])
        self.assertEqual(row["unresolved_refs"], stats["unresolved_refs"])
        self.assertEqual(row["object_names"], stats["objects"])
        self.assertEqual(row["object_names_with_path"], stats["objects_with_path"])


class TestReadOnly(DBTestCase):
    def test_write_is_rejected(self):
        self.save(load_sample())
        conn = db.connect(self.path, readonly=True)
        try:
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("INSERT INTO aliases (alias, target) VALUES ('x', 'y')")
        finally:
            conn.close()

    def test_open_missing_db_fails(self):
        missing = Path(self._tmp.name) / "没有这个库.sqlite"
        with self.assertRaises(sqlite3.OperationalError):
            db.connect(missing, readonly=True)


class TestSnapshots(DBTestCase):
    def test_snapshot_interval_limits_writes(self):
        self.save(load_sample())
        self.save(load_sample())
        conn = self.conn()
        try:
            count = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(count, 1)

    def test_force_snapshot_and_restore(self):
        model = load_sample()
        self.save(model)
        first_id = db.list_snapshots(self.path)[-1]["id"]

        model.nodes.pop()
        self.save(model, force_snapshot=True)
        self.assertEqual(len(db.load_model(self.path).nodes), len(model.nodes))

        restored = db.restore_snapshot(self.path, first_id)
        self.assertGreater(len(restored.nodes), len(model.nodes))
        self.assertEqual(len(db.load_model(self.path).nodes), len(restored.nodes))

    def test_snapshot_prune(self):
        model = load_sample()
        for index in range(db.SNAPSHOT_KEEP + 3):
            self.save(model, reason="轮次 %d" % index, force_snapshot=True)
        snapshots = db.list_snapshots(self.path)
        self.assertEqual(len(snapshots), db.SNAPSHOT_KEEP)
        self.assertEqual(snapshots[0]["reason"], "轮次 %d" % (db.SNAPSHOT_KEEP + 2))

    def test_snapshot_payload_is_restorable_model(self):
        model = load_sample()
        self.save(model)
        conn = db.connect(self.path, readonly=True)
        try:
            payload = conn.execute(
                "SELECT payload FROM snapshots ORDER BY id DESC LIMIT 1"
            ).fetchone()[0]
        finally:
            conn.close()
        rebuilt = M.model_from_dict(json.loads(payload))
        M.resolve_refs(rebuilt)
        self.assertEqual(norm(db.model_payload(rebuilt)), norm(db.model_payload(model)))


class TestVerifyAndQuery(DBTestCase):
    def test_verify_clean(self):
        self.save(load_sample())
        result = db.verify(self.path)
        self.assertEqual(result["integrity"], "ok")
        self.assertEqual(result["missing_tables"], [])
        self.assertEqual(result["missing_views"], [])
        self.assertEqual(result["foreign_key_errors"], 0)
        self.assertEqual(result["duplicate_numbers"], 0)
        self.assertEqual(result["nodes_without_section"], 0)
        self.assertEqual(result["refs_without_node"], 0)

    def test_schema_report_lists_objects(self):
        self.save(load_sample())
        report = db.schema_report(self.path)
        for name in db.REQUIRED_TABLES:
            self.assertIn(name, report["tables"])
        for name in db.REQUIRED_VIEWS:
            self.assertIn(name, report["views"])
        columns = [c["name"] for c in report["tables"]["nodes"]]
        self.assertIn("summary_is_auto", columns)

    def test_query_outline_and_node(self):
        model = load_sample()
        self.save(model)
        conn = self.conn()
        try:
            data = query.outline(conn)
            self.assertEqual(data["stats"]["nodes"], len(model.nodes))
            self.assertEqual(
                [s["title"] for s in data["sections"]],
                [s.title for s in model.sections],
            )
            first = next(
                node for section in data["sections"] for node in section["nodes"]
            )
            detail = query.node_detail(conn, first["id"])
            self.assertEqual(detail["id"], first["id"])
            self.assertIn("refs", detail)
            self.assertIn("objects", detail)
            self.assertIn("notes", detail)

            unresolved = query.refs(conn, unresolved_only=True)
            self.assertTrue(all(not r["resolved"] for r in unresolved))
            self.assertGreaterEqual(len(unresolved), 1)

            missing = query.objects(conn, missing_path_only=True)
            self.assertTrue(all(not o["has_path"] for o in missing))

            self.assertEqual(query.node_id_for(conn, first["id"]), first["id"])
            self.assertEqual(query.node_id_for(conn, detail["index_label"]), detail["id"])
        finally:
            conn.close()

    def test_query_run_sql_guard(self):
        self.save(load_sample())
        conn = self.conn()
        try:
            result = query.run_sql(conn, "SELECT id FROM v_node LIMIT 1")
            self.assertEqual(result["columns"], ["id"])
            self.assertEqual(len(result["rows"]), 1)
            with self.assertRaises(SystemExit):
                query.run_sql(conn, "DELETE FROM nodes")
        finally:
            conn.close()

    def test_query_issues_and_view(self):
        self.save(load_sample())
        data = query.issues(self.path)
        self.assertIn("issues", data)
        self.assertTrue(any(i["kind"] == "unresolved_ref" for i in data["issues"]))
        view = query.view(self.path)
        self.assertEqual(len(view["nodes"]), data["stats"]["nodes"])
        self.assertIn("edges", view)


class TestModelHelpers(DBTestCase):
    def test_readonly_reports_missing_db(self):
        self.assertFalse(db.exists(self.path))
        result = db.verify(self.path)
        self.assertFalse(result["exists"])

    def test_save_rejects_node_without_section(self):
        model = load_sample()
        model.nodes[0].section_id = "s999"
        with self.assertRaises(ValueError):
            self.save(model)

    def test_dangling_ref_target_is_cleared(self):
        model = load_sample()
        model.nodes[-1].refs[0].target_id = "n999"
        self.save(model)
        payload = db.load_model_dict(self.path)
        targets = [
            r["target_id"] for n in payload["nodes"] for r in n["refs"]
        ]
        self.assertNotIn("n999", targets)


if __name__ == "__main__":
    unittest.main(verbosity=2)
