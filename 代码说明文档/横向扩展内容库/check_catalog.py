"""在临时数据库上核验目录维护行为；不修改项目源码或正式库。"""
import contextlib
import io
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import catalog
import seed


class CatalogChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="extension-catalog-check-")
        self.folder = Path(self.temp.name)
        self.path = self.folder / "test.sqlite"
        shutil.copy2(catalog.DEFAULT_DB, self.path)
        self.db = catalog.connect(self.path)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def rebuild(self, records=None):
        with contextlib.redirect_stdout(io.StringIO()), patch.object(catalog, "HERE", self.folder):
            if records is None:
                catalog.build(catalog.DEFAULT_ROOT, self.path)
            else:
                with patch.object(seed, "records", return_value=records):
                    catalog.build(catalog.DEFAULT_ROOT, self.path)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(catalog.HERE / "catalog.py"), "--db", str(self.path), *args], capture_output=True, encoding="utf-8")

    def test_integrity_and_evidence(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(catalog.verify(self.db, catalog.DEFAULT_ROOT), 0)

    def test_foreign_keys_reject_dangling_executor(self):
        with self.assertRaises(sqlite3.IntegrityError), self.db:
            self.db.execute('UPDATE "报文操作" SET executor_id=? WHERE id=?', ("MissingExecutor", "Movement"))
        self.assertEqual(self.db.execute('SELECT executor_id FROM "报文操作" WHERE id="Movement"').fetchone()[0], "MovementEffectExecutor")

    def test_rebuild_preserves_management_and_manual_plan(self):
        created = self.db.execute('SELECT created_at FROM "固定属性" WHERE id="ActionPoints"').fetchone()[0]
        with self.db:
            self.db.execute('UPDATE "固定属性" SET notes=?,owner=?,priority=0 WHERE id="ActionPoints"', ("保留备注", "程序组"))
            self.db.execute('INSERT INTO "目标类型" (id,code_name,display_name,summary,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?)', ("Unit", "Unit", "计划单位目标", "未实现计划", "待实现", catalog.now(), catalog.now()))
        self.rebuild()
        row = self.db.execute('SELECT notes,owner,priority,created_at FROM "固定属性" WHERE id="ActionPoints"').fetchone()
        self.assertEqual(tuple(row), ("保留备注", "程序组", 0, created))
        self.assertEqual(self.db.execute('SELECT managed,status FROM "目标类型" WHERE id="Unit"').fetchone()[:], (0, "待实现"))

    def test_removed_seed_is_retained_as_deprecated(self):
        rows = seed.records(catalog.DEFAULT_ROOT, catalog.source_index(catalog.DEFAULT_ROOT))
        self.rebuild([(table, row) for table, row in rows if not (table == "固定属性" and row["id"] == "Strength")])
        self.assertEqual(self.db.execute('SELECT status FROM "固定属性" WHERE id="Strength"').fetchone()[0], "已废弃")

    def test_new_indirect_component_requires_review(self):
        index = catalog.source_index(catalog.DEFAULT_ROOT)
        index["test.cs"] = "public sealed class ExtraBuilder : ActionPacketBuilder {}"
        with self.assertRaisesRegex(ValueError, "ExtraBuilder"):
            seed.records(catalog.DEFAULT_ROOT, index)

    def test_new_enum_member_requires_review(self):
        index = catalog.source_index(catalog.DEFAULT_ROOT)
        path = seed.M + "AttributeComponent.cs"
        index[path] = index[path].replace("ActionSpeed\n}", "ActionSpeed,\n    ExtraAttribute\n}")
        self.assertIn("ExtraAttribute", index[path])
        with self.assertRaisesRegex(ValueError, "ExtraAttribute"):
            seed.records(catalog.DEFAULT_ROOT, index)

    def test_new_source_file_is_reported(self):
        index = catalog.source_index(catalog.DEFAULT_ROOT)
        index["Assets/Script/NewFile.cs"] = "public class NewFile {}"
        with patch.object(catalog, "source_index", return_value=index), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(catalog.verify(self.db, catalog.DEFAULT_ROOT), 1)
        self.assertIn("NewFile.cs", output.getvalue())

    def test_cli_add_update_and_invalid_status(self):
        file = self.folder / "input.json"
        file.write_text(json.dumps(dict(display_name="计划单位目标", summary="待办", enum_type="ActionTargetKind"), ensure_ascii=False), encoding="utf-8")
        result = self.cli("add", "目标类型", "Unit", "--data", str(file))
        self.assertEqual(result.returncode, 0, result.stderr)
        file.write_text(json.dumps(dict(notes="CLI备注", owner="程序组", priority=1), ensure_ascii=False), encoding="utf-8")
        result = self.cli("update", "固定属性", "ActionPoints", "--data", str(file))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.db.execute('SELECT notes FROM "固定属性" WHERE id="ActionPoints"').fetchone()[0], "CLI备注")
        file.write_text('{"status":"错误状态"}', encoding="utf-8")
        result = self.cli("update", "目标类型", "Unit", "--data", str(file))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.db.execute('SELECT status FROM "目标类型" WHERE id="Unit"').fetchone()[0], "待实现")
        result = self.cli("update", "固定属性", "ActionPoints", "--data", str(file))
        self.assertNotEqual(result.returncode, 0)

    def test_manual_collision_rolls_back_entire_build(self):
        with self.db:
            self.db.execute('UPDATE "固定属性" SET managed=0,summary="人工事实" WHERE id="Strength"')
        before = self.db.execute('SELECT verified_at FROM "元对象组件" WHERE id="AttributeComponent"').fetchone()[0]
        with self.assertRaisesRegex(ValueError, "ID 冲突"):
            self.rebuild()
        self.assertEqual(self.db.execute('SELECT verified_at FROM "元对象组件" WHERE id="AttributeComponent"').fetchone()[0], before)
        self.assertEqual(self.db.execute('SELECT summary FROM "固定属性" WHERE id="Strength"').fetchone()[0], "人工事实")

    def test_new_content_table_requires_user_permission(self):
        spec = dict(seed.TABLES["对象消息"])
        with patch.dict(seed.TABLES, {"待确认类别": spec}):
            with self.assertRaisesRegex(ValueError, "需先询问用户"):
                self.rebuild()
        self.assertIsNone(self.db.execute("SELECT name FROM sqlite_master WHERE name='待确认类别'").fetchone())

    def test_missing_database_is_not_initialized(self):
        missing = self.folder / "missing.sqlite"
        with self.assertRaisesRegex(ValueError, "默认不新建数据库或表"):
            catalog.build(catalog.DEFAULT_ROOT, missing)
        self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
