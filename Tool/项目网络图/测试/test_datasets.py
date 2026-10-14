"""数据隔离、持久化、可恢复删除与 HTTP 路由测试。"""
from pathlib import Path
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import db
import datasets
import model as M
import server
import store


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="pn-datasets-test-")
        self.root = Path(self.temporary.name)
        self.directory = self.root / "data"
        self.patches = [
            patch.object(store, "DATA_DIR", self.directory),
            patch.object(store, "BACKUP_DIR", self.directory / "备份"),
            patch.object(store, "EXPORT_DIR", self.directory / "导出"),
            patch.object(store, "DB_FILE", self.directory / "项目网络图.sqlite"),
            patch.object(store, "WORKSPACE", self.root),
            patch.object(store, "LEGACY_JSON_FILE", self.root / "missing.json"),
        ]
        for item in self.patches:
            item.start()
        self.catalog = datasets.Catalog(self.directory)

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temporary.cleanup()

    def test_create_switch_and_separate_edits(self):
        self.catalog.create("图甲")
        first = self.catalog.active_id
        model = M.parse_markdown("## 路线\n1. 条目", source="甲")
        store.save(model)
        self.catalog.create("图乙")
        second = self.catalog.active_id
        self.assertFalse(store.load_or_seed().nodes)
        self.assertEqual(len(self.catalog.select(first).nodes), 1)
        self.assertFalse(self.catalog.select(second).nodes)
        self.assertEqual(len(self.catalog.entries()), 2)

    def test_import_consistent_copy_and_preserve_original(self):
        original = self.root / "外部.sqlite"
        db.save_model(original, M.parse_markdown("## 路线\n1. A\n2. B"), backup=False)
        before = original.read_bytes()
        loaded = self.catalog.add_existing(original)
        self.assertEqual(len(loaded.nodes), 2)
        self.assertEqual(store.DB_FILE.parent, self.directory)
        store.save(M.Model(title="编辑后的副本"))
        self.assertEqual(original.read_bytes(), before)
        self.assertEqual(len(db.load_model(original).nodes), 2)

    def test_delete_active_selects_other_and_can_restore(self):
        self.catalog.create("甲")
        first = self.catalog.active_id
        self.catalog.create("乙")
        second = self.catalog.active_id
        replacement = self.catalog.delete(second)
        self.assertEqual(self.catalog.active_id, first)
        self.assertEqual(replacement.title, "甲")
        deleted = list((self.directory / "已删除").glob("*.sqlite"))
        self.assertEqual(len(deleted), 1)
        self.assertEqual(self.catalog.add_existing(deleted[0]).title, "乙")

    def test_delete_last_does_not_reseed_on_restart(self):
        self.catalog.create("最后一张图")
        self.catalog.delete(self.catalog.active_id)
        self.assertIsNone(self.catalog.active_id)
        restarted = datasets.Catalog(self.directory)
        self.assertIsNone(restarted.initialize(self.directory / "项目网络图.sqlite"))
        self.assertFalse(restarted.entries())

    def test_remember_selection_and_keep_empty_database(self):
        self.catalog.create("空图甲")
        first = self.catalog.active_id
        self.catalog.create("空图乙")
        self.catalog.select(first)
        restarted = datasets.Catalog(self.directory)
        model = restarted.initialize(self.directory / "项目网络图.sqlite")
        self.assertEqual(restarted.active_id, first)
        self.assertEqual(model.title, "空图甲")
        self.assertEqual(store.load_or_seed().title, "空图甲")

    def test_reject_escape_and_invalid_sqlite(self):
        for value in ["../escape.sqlite", "..\\escape.sqlite", "C:/other.sqlite", "bad.txt", None]:
            with self.assertRaises(ValueError):
                self.catalog.path(value)
        invalid = self.root / "其他.sqlite"
        conn = sqlite3.connect(invalid)
        conn.execute("CREATE TABLE other (id)")
        conn.close()
        with self.assertRaises(sqlite3.DatabaseError):
            self.catalog.add_existing(invalid)
        self.assertFalse(self.catalog.entries())

    def test_duplicate_names_create_distinct_files(self):
        self.catalog.create("同名")
        first = self.catalog.active_id
        self.catalog.create("同名")
        self.assertNotEqual(first, self.catalog.active_id)
        self.assertEqual(len(self.catalog.entries()), 2)

    def test_http_data_lifecycle_and_stale_writes(self):
        with patch.object(server, "CATALOG", self.catalog), patch.object(server, "STATE", {"model": None}):
            http = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
            thread = threading.Thread(target=http.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{http.server_port}"
            def request(path, body=None):
                data = json.dumps(body).encode() if body is not None else None
                req = Request(base + path, data=data, headers={"Content-Type": "application/json"})
                try:
                    with urlopen(req, timeout=5) as response:
                        return response.status, json.loads(response.read())
                except HTTPError as error:
                    return error.code, json.loads(error.read())
            try:
                code, current = request("/api/state")
                self.assertEqual(code, 200)
                self.assertIsNone(current["dataset_id"])
                self.assertEqual(request("/api/op", {"op": "insert_section", "args": {"title": "禁止"}})[0], 400)
                _, first = request("/api/datasets/create", {"title": "图一", "dataset_id": None})
                first_id = first["dataset_id"]
                _, second = request("/api/datasets/create", {"title": "图二", "dataset_id": first_id})
                second_id = second["dataset_id"]
                code, _ = request("/api/op", {"op": "insert_section", "args": {"title": "误写"}, "dataset_id": first_id})
                self.assertEqual(code, 409)
                self.assertFalse(db.load_model(self.catalog.path(first_id)).sections)
                self.assertFalse(db.load_model(self.catalog.path(second_id)).sections)
                code, updated = request("/api/op", {"op": "insert_section", "args": {"title": "正确路线"}, "dataset_id": second_id})
                self.assertEqual(code, 200)
                self.assertEqual(len(updated["model"]["sections"]), 1)
                code, selected = request("/api/datasets/select", {"id": first_id, "dataset_id": second_id})
                self.assertEqual(code, 200)
                self.assertFalse(selected["model"]["sections"])
                for item in (second_id, first_id):
                    code, last = request("/api/datasets/delete", {"id": item, "dataset_id": first_id})
                    self.assertEqual(code, 200)
                self.assertIsNone(last["dataset_id"])
                self.assertFalse(last["config"]["datasets"])
                with urlopen(base + "/") as response:
                    self.assertIn("img-src 'self' blob:", response.headers["Content-Security-Policy"])
            finally:
                http.shutdown()
                http.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
