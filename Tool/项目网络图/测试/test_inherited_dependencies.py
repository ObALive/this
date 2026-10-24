"""同路线上游依赖覆盖规则，以及编辑、保存和旧库迁移的约束测试。"""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import db
import model as M
import datasets
import store


def sample():
    return M.parse_markdown("""## 甲
1. 上游（依赖乙2）
2. 中间
3. 下游（依赖乙1、乙2、乙3、丙1、不存在1）
## 乙
1. 第一项
2. 第二项
3. 第三项
## 丙
1. 独立项
""")


class InheritedDependencyTests(unittest.TestCase):
    def test_non_adjacent_upstream_covers_equal_and_earlier(self):
        m = sample()
        removed = M.prune_inherited_dependencies(m)
        self.assertEqual([r["raw"] for r in removed], ["乙1", "乙2"])
        self.assertEqual([r.raw for r in m.nodes[2].refs], ["乙3", "丙1", "不存在1"])
        self.assertEqual(M.prune_inherited_dependencies(m), [])

    def test_same_node_keeps_only_latest_target_per_route(self):
        m = sample()
        m.nodes[0].refs = []
        self.assertEqual(len(M.prune_inherited_dependencies(m)), 2)
        self.assertEqual([r.raw for r in m.nodes[2].refs], ["乙3", "丙1", "不存在1"])
        self.assertEqual(M.prune_inherited_dependencies(m), [])

    def test_single_ref_does_not_delete_itself_and_duplicates_keep_one(self):
        m = sample()
        m.nodes[0].refs = []
        m.nodes[2].refs = [M.Ref(raw="乙2"), M.Ref(raw="乙2")]
        self.assertEqual(len(M.prune_inherited_dependencies(m)), 1)
        self.assertEqual(len(m.nodes[2].refs), 1)
        self.assertEqual(M.prune_inherited_dependencies(m), [])

    def test_descendant_reference_does_not_prune_ancestor(self):
        m = sample()
        m.nodes[0].refs = [M.Ref(raw="乙1")]
        m.nodes[2].refs = [M.Ref(raw="乙3")]
        self.assertEqual(M.prune_inherited_dependencies(m), [])

    def test_other_source_route_does_not_cover(self):
        m = sample()
        m.nodes[0].refs = []
        m.nodes[2].refs = [M.Ref(raw="乙1")]
        m.nodes[-1].refs = [M.Ref(raw="乙3")]
        self.assertEqual(M.prune_inherited_dependencies(m), [])

    def test_order_comes_from_route_sequence_not_number(self):
        m = sample()
        m.nodes[3].number, m.nodes[4].number = 100, -10
        # 引用已经绑定，修改显示编号不改变条目的上下游顺序。
        self.assertEqual(len(M.prune_inherited_dependencies(m)), 2)

    def test_upstream_changes_recheck_all_descendants(self):
        m = sample()
        M.prune_inherited_dependencies(m)
        result = M.apply_op(m, "update_node", {
            "node_id": m.nodes[0].id,
            "refs": [{"raw": "乙3"}], "reparse": False,
        })
        self.assertEqual([r["raw"] for r in result["pruned_dependencies"]], ["乙3"])
        self.assertEqual([r.raw for r in m.nodes[2].refs], ["丙1", "不存在1"])

    def test_new_dependency_and_history_replace_are_normalized(self):
        m = sample()
        original = db.model_payload(m)
        result = M.apply_op(m, "replace", {"model": original})
        self.assertEqual(len(result["pruned_dependencies"]), 2)
        result = M.apply_op(m, "update_node", {
            "node_id": m.nodes[2].id,
            "refs": [{"raw": "乙1"}], "reparse": False,
        })
        self.assertEqual(len(result["pruned_dependencies"]), 1)
        self.assertEqual(m.nodes[2].refs, [])

    def test_save_enforces_rule_and_export_does_not_resurrect(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "图.sqlite"
            db.save_model(path, sample(), backup=False)
            loaded = db.load_model(path)
            self.assertEqual(M.prune_inherited_dependencies(loaded), [])
            self.assertEqual(len(loaded.nodes[2].refs), 3)
            exported = M.parse_markdown(M.to_markdown(loaded))
            self.assertEqual(len(exported.nodes[2].refs), 3)

    def test_open_old_database_saves_pre_cleanup_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            path = directory / "旧图.sqlite"
            # 模拟旧程序写入尚未执行约束的数据库。
            with patch.object(M, "prune_inherited_dependencies", return_value=[]):
                db.save_model(path, sample(), backup=False)
            self.assertEqual(len(db.load_model(path).nodes[2].refs), 5)
            with patch.object(store, "DB_FILE", path):
                opened = datasets.Catalog(directory).select(path.name)
            self.assertEqual(len(opened.nodes[2].refs), 3)
            snapshots = db.list_snapshots(path)
            self.assertTrue(any(s["reason"] == "上游依赖约束清理前" for s in snapshots))
            conn = db.connect(path, readonly=True)
            try:
                import json
                previous = json.loads(conn.execute("SELECT payload FROM snapshots WHERE reason = ?", ("上游依赖约束清理前",)).fetchone()[0])
                self.assertEqual(len(previous["nodes"][2]["refs"]), 5)
            finally:
                conn.close()
            self.assertEqual(M.prune_inherited_dependencies(db.load_model(path)), [])


if __name__ == "__main__":
    unittest.main()
