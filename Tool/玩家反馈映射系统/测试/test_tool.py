"""数据库与本地编辑接口的回归检查。运行：python -B -m unittest discover -s Tool/玩家反馈映射系统/测试 -v"""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import database as db  # noqa: E402
import init_db  # noqa: E402
import server as web  # noqa: E402


class FeedbackToolTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "test.sqlite"
        self.assertEqual(init_db.build(self.path), 43)

    def tearDown(self):
        self.temp.cleanup()

    def test_database_crud_and_cascade(self):
        con = db.connect(self.path)
        try:
            self.assertEqual(len(db.list_topics(con)), 43)
            self.assertEqual(con.execute("SELECT count(*) FROM mappings").fetchone()[0], 0)
            columns = {row[1] for row in con.execute("PRAGMA table_info(topics)")}
            self.assertIn("code_owner", columns)
            self.assertNotIn("old_v1_coordinate", columns)
            topic = db.create_topic(con, {
                "topic_id": "FB-44", "player_behavior": "测试行为",
                "feedback_topic": "测试反馈", "code_owner": "M08",
                "source_ref": "测试来源", "sort_order": 44,
            })
            self.assertEqual(topic["topic_id"], "FB-44")
            mapping = db.create_mapping(con, "FB-44", {
                "player_action": "测试操作", "program_feedback": "测试程序反馈",
                "context": "地图", "condition_text": "条件", "notes": "备注", "sort_order": 1,
            })
            self.assertEqual(len(db.get_topic(con, "FB-44")["mappings"]), 1)
            self.assertEqual(len(db.list_topics(con, "测试操作")), 1)
            changed = db.update_mapping(con, mapping["mapping_id"], {
                "player_action": "修改操作", "program_feedback": "修改反馈",
                "context": "事件", "condition_text": "", "notes": "", "sort_order": 2,
            })
            self.assertEqual(changed["program_feedback"], "修改反馈")
            self.assertEqual(db.update_topic(con, "FB-44", {
                "player_behavior": "更新行为", "feedback_topic": "更新主题",
                "code_owner": "M04, M08", "source_ref": "来源", "sort_order": 44,
            })["code_owner"], "M04, M08")
            self.assertTrue(db.delete_topic(con, "FB-44"))
            self.assertEqual(con.execute("SELECT count(*) FROM mappings WHERE mapping_id=?", (mapping["mapping_id"],)).fetchone()[0], 0)
            self.assertEqual(con.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        finally:
            con.close()

    def test_http_crud(self):
        httpd = web.LocalHTTPServer(("127.0.0.1", 0), web.Handler)
        httpd.db_path = self.path
        httpd.edit_token = "test-token"
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{httpd.server_address[1]}"

        def call(path, method="GET", payload=None, token=True):
            headers = {}
            if token:
                headers["X-Tool-Token"] = "test-token"
            data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
            if data is not None:
                headers["Content-Type"] = "application/json"
            req = Request(base + path, data=data, headers=headers, method=method)
            with urlopen(req, timeout=5) as response:
                return response.status, json.load(response)

        try:
            self.assertEqual(len(call("/api/topics")[1]["topics"]), 43)
            self.assertEqual(call("/api/config")[1]["edit_token"], "test-token")
            self.assertEqual(call("/api/export")[1]["schema_version"], 1)
            with self.assertRaises(HTTPError) as denied:
                call("/api/topics", "POST", {"topic_id": "FB-44"}, token=False)
            self.assertEqual(denied.exception.code, 403)
            status, topic = call("/api/topics", "POST", {
                "topic_id": "FB-44", "player_behavior": "网页测试行为",
                "feedback_topic": "网页测试反馈", "code_owner": "M08",
                "source_ref": "", "sort_order": 44,
            })
            self.assertEqual(status, 201)
            self.assertEqual(topic["topic_id"], "FB-44")
            status, mapping = call("/api/topics/FB-44/mappings", "POST", {
                "player_action": "点击测试", "program_feedback": "显示测试",
                "context": "", "condition_text": "", "notes": "", "sort_order": 1,
            })
            self.assertEqual(status, 201)
            self.assertEqual(len(call("/api/topics/FB-44")[1]["mappings"]), 1)
            self.assertEqual(len(call("/api/topics?q=" + quote("点击测试"))[1]["topics"]), 1)
            status, changed = call(f"/api/mappings/{mapping['mapping_id']}", "PUT", {
                "player_action": "改后操作", "program_feedback": "改后反馈",
                "context": "", "condition_text": "", "notes": "", "sort_order": 1,
            })
            self.assertEqual(changed["program_feedback"], "改后反馈")
            self.assertEqual(call(f"/api/mappings/{mapping['mapping_id']}", "DELETE")[1]["deleted"], True)
            self.assertEqual(call("/api/topics/FB-44", "DELETE")[1]["deleted"], True)
            self.assertEqual(len(call("/api/topics")[1]["topics"]), 43)
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
