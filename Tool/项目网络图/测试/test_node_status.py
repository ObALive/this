"""节点状态：三态校验、旧库只读兼容、迁移与快照恢复。"""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import db
import model as M


class NodeStatusTests(unittest.TestCase):
    def test_status_roundtrip_and_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "状态.sqlite"
            m = M.parse_markdown("## 路线\n1. 节点")
            node = m.nodes[0]
            self.assertEqual(node.status, "未实现")
            for status in M.NODE_STATUSES:
                M.apply_op(m, "update_node", {"node_id": node.id, "status": status, "reparse": False})
                db.save_model(path, m, force_snapshot=True)
                self.assertEqual(db.load_model(path).nodes[0].status, status)
                self.assertEqual(M.serialize(m)["nodes"][0]["status"], status)
            snapshots = db.list_snapshots(path)
            restored = db.restore_snapshot(path, snapshots[-1]["id"])
            self.assertEqual(restored.nodes[0].status, "未实现")

    def test_invalid_status_does_not_modify_node(self):
        m = M.parse_markdown("## 路线\n1. 原正文")
        old = db.model_payload(m)
        with self.assertRaises(ValueError):
            M.apply_op(m, "update_node", {"node_id": m.nodes[0].id, "status": "随便", "body": "不应修改"})
        self.assertEqual(db.model_payload(m), old)

    def test_old_payload_defaults_and_replace_preserves(self):
        m = M.parse_markdown("## 路线\n1. 节点")
        payload = db.model_payload(m)
        del payload["nodes"][0]["status"]
        self.assertEqual(M.model_from_dict(payload).nodes[0].status, "未实现")
        payload["nodes"][0]["status"] = "实现中"
        M.apply_op(m, "replace", {"model": payload})
        self.assertEqual(m.nodes[0].status, "实现中")

    def test_schema_one_readonly_compatible_and_migrates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "旧库.sqlite"
            schema = db.SCHEMA.replace(
                "summary_is_auto  INTEGER NOT NULL DEFAULT 1,\n    status           TEXT NOT NULL DEFAULT '未实现' CHECK(status IN ('未实现', '实现中', '已实现'))",
                "summary_is_auto  INTEGER NOT NULL DEFAULT 1",
            ).replace("       n.status,\n", "")
            conn = db.connect(path)
            try:
                conn.executescript(schema)
                conn.execute("INSERT INTO sections(id,seq,title,level) VALUES('s',1,'旧路线',2)")
                conn.execute("INSERT INTO nodes(id,seq,section_id,number,summary) VALUES('n',1,'s',1,'旧节点')")
                conn.execute("INSERT INTO meta VALUES('schema_version','1')")
                conn.commit()
            finally:
                conn.close()
            before = path.read_bytes()
            self.assertEqual(db.load_model(path).nodes[0].status, "未实现")
            self.assertEqual(path.read_bytes(), before)
            db.ensure_schema(path)
            m = db.load_model(path)
            m.nodes[0].status = "已实现"
            db.save_model(path, m)
            conn = db.connect(path, readonly=True)
            try:
                self.assertEqual(conn.execute("SELECT status FROM v_node").fetchone()[0], "已实现")
                self.assertEqual(db.meta_value(conn, "schema_version"), "2")
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
