"""项目网络图模型单元测试。

运行： python3 Tool/项目网络图/测试/test_model.py
或在工具目录： python3 -m unittest discover -s 测试 -v
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
sys.path.insert(0, str(TOOL))

import model as M  # noqa: E402

WORKSPACE = TOOL.parent.parent
CO05 = WORKSPACE / "Task" / "CO系列任务" / "CO05.md"


def load_co05() -> M.Model:
    text = CO05.read_text(encoding="utf-8")
    return M.parse_markdown(text, source=str(CO05))


def label(m: M.Model, node: M.Node) -> str:
    return m.index_label(node)


class TestParse(unittest.TestCase):
    def setUp(self) -> None:
        self.m = load_co05()

    def test_routes_and_nodes(self):
        titles = [s.title for s in self.m.sections]
        self.assertEqual(titles, ["瓦片地图", "角色行为", "角色技能", "角色移动", "时间轴"])
        self.assertEqual(len(self.m.nodes), 16)

    def test_numbering_keeps_zero_start(self):
        move = next(s for s in self.m.sections if s.title == "角色移动")
        numbers = [n.number for n in self.m.section_nodes(move.id)]
        self.assertEqual(numbers, [0, 1, 2, 3])

    def test_parent_path(self):
        skill = next(n for n in self.m.nodes if n.summary == "制作元技能")
        self.assertEqual(label(self.m, skill), "角色行为/角色技能 1")

    def test_summary_and_detail(self):
        tile1 = self.m.section_nodes(next(s.id for s in self.m.sections if s.title == "瓦片地图"))[0]
        self.assertEqual(tile1.summary, "平铺的地图绘制")
        self.assertEqual(tile1.body, "平铺的地图绘制，每个瓦片无区别")

    def test_inline_parenthesis_kept_in_body(self):
        skill2 = next(n for n in self.m.nodes if "挂机动作" in n.summary)
        self.assertIn("（放技能还是移动还是挂机）", skill2.body)

    def test_long_design_note_extracted(self):
        tile2 = self.m.section_nodes(next(s.id for s in self.m.sections if s.title == "瓦片地图"))[1]
        self.assertTrue(any("TilemapManager" in n for n in tile2.notes))
        self.assertNotIn("TilemapManager", tile2.body)

    def test_object_group_lists_two_objects(self):
        move0 = next(n for n in self.m.nodes if n.summary == "制作元对象和相关组件约定")
        names = [o.name for o in move0.objects]
        self.assertEqual(names, ["元对象-场景纹理组件", "元对象-场景坐标组件"])

    def test_object_note(self):
        tile3 = next(n for n in self.m.nodes if n.summary == "场景道具摆放")
        obj = {o.name: o for o in tile3.objects}["元对象-角色标记组件"]
        self.assertIn("只作为将对象识别为角色的标记", obj.note)

    def test_explicit_refs_resolved(self):
        tile4 = next(n for n in self.m.nodes if n.number == 4 and n.section_id == self.m.sections[0].id)
        self.assertEqual(len(tile4.refs), 1)
        target = self.m.node(tile4.refs[0].target_id)
        self.assertIsNotNone(target)
        self.assertEqual(target.number, 3)

    def test_alias_ref_resolves_by_suffix(self):
        move1 = next(n for n in self.m.nodes if n.summary == "点击地格")
        self.assertEqual(move1.refs[0].raw, "地图1")
        target = self.m.node(move1.refs[0].target_id)
        self.assertEqual(target.summary, "平铺的地图绘制")

    def test_unresolved_ref_flagged(self):
        tile5 = next(n for n in self.m.nodes if n.number == 5 and n.section_id == self.m.sections[0].id)
        self.assertIsNone(tile5.refs[0].target_id)
        issues = M.validate(self.m)["issues"]
        self.assertTrue(any(i["kind"] == "unresolved_ref" and "元效果" in i["text"] for i in issues))

    def test_chain_edges_per_route(self):
        edges, _ = M.build_edges(self.m)
        chain = [e for e in edges if e["kind"] == "chain"]
        # 瓦片 4 条 + 技能 2 条 + 移动 3 条 + 时间轴 3 条
        self.assertEqual(len(chain), 12)


class TestInsertAndRenumber(unittest.TestCase):
    def setUp(self) -> None:
        self.m = load_co05()
        self.move = next(s for s in self.m.sections if s.title == "角色移动")
        self.move0 = self.m.section_nodes(self.move.id)[0]

    def test_insert_before_head_shifts_numbers(self):
        log: list[str] = []
        M.insert_node(
            self.m,
            section_id=self.move.id,
            before_node_id=self.move0.id,
            summary="新的前置步骤",
            body="新的前置步骤",
            log=log,
        )
        numbers = [n.number for n in self.m.section_nodes(self.move.id)]
        self.assertEqual(numbers, [0, 1, 2, 3, 4])

    def test_insert_rewrites_cross_route_refs(self):
        M.insert_node(
            self.m,
            section_id=self.move.id,
            before_node_id=self.move0.id,
            summary="新的前置步骤",
            body="新的前置步骤",
        )
        # 技能2 原本依赖 角色移动1，插入后应指向顺位后的 角色移动2
        skill2 = next(n for n in self.m.nodes if "挂机动作" in n.summary)
        self.assertEqual(skill2.refs[0].raw, "角色移动2")
        target = self.m.node(skill2.refs[0].target_id)
        self.assertEqual(target.summary, "点击地格")
        # 时间轴1 同理
        tl1 = next(n for n in self.m.nodes if n.summary == "为角色添加速度属性")
        self.assertEqual(tl1.refs[0].raw, "角色移动2")
        # 瓦片4 原本依赖 角色移动3 → 角色移动4
        tile4 = next(n for n in self.m.nodes if n.section_id == self.m.sections[0].id and n.number == 4)
        self.assertEqual(tile4.refs[0].raw, "角色移动4")

    def test_insert_does_not_touch_unrelated_alias_ref(self):
        M.insert_node(
            self.m,
            section_id=self.move.id,
            before_node_id=self.move0.id,
            summary="新的前置步骤",
            body="新的前置步骤",
        )
        move1 = next(n for n in self.m.nodes if n.summary == "点击地格")
        self.assertEqual(move1.refs[0].raw, "地图1")

    def test_insert_tail_keeps_existing_numbers(self):
        M.insert_node(self.m, section_id=self.move.id, summary="补充", body="补充")
        numbers = [n.number for n in self.m.section_nodes(self.move.id)]
        self.assertEqual(numbers, [0, 1, 2, 3, 4])

    def test_insert_after_middle(self):
        move1 = next(n for n in self.m.nodes if n.summary == "点击地格")
        M.insert_node(self.m, section_id=self.move.id, after_node_id=move1.id, summary="插入项", body="插入项")
        numbers = [n.number for n in self.m.section_nodes(self.move.id)]
        self.assertEqual(numbers, [0, 1, 2, 3, 4])
        self.assertEqual([n.summary for n in self.m.section_nodes(self.move.id)][2], "插入项")

    def test_delete_shifts_back_and_invalidates_refs(self):
        tile2 = next(n for n in self.m.nodes if n.section_id == self.m.sections[0].id and n.number == 2)
        result = M.delete_node(self.m, tile2.id)
        # 瓦片2 被删后，瓦片3..5 → 2..4
        numbers = [n.number for n in self.m.section_nodes(self.m.sections[0].id)]
        self.assertEqual(numbers, [1, 2, 3, 4])
        # 依赖 角色移动1 的引用不受影响；依赖 元效果 的仍为未解析
        tile5 = next(n for n in self.m.nodes if n.section_id == self.m.sections[0].id and n.number == 4)
        self.assertFalse(tile5.refs[0].resolved)

    def test_delete_marks_dependents(self):
        move1 = next(n for n in self.m.nodes if n.summary == "点击地格")
        result = M.delete_node(self.m, move1.id)
        self.assertIn("角色行为/角色技能 2", result["affected"])
        skill2 = next(n for n in self.m.nodes if "挂机动作" in n.summary)
        self.assertIsNone(skill2.refs[0].target_id)
        self.assertIn("已被删除", skill2.refs[0].reason)

    def test_move_node_renumbers(self):
        move3 = next(n for n in self.m.nodes if n.summary == "寻路逻辑")
        M.move_node(self.m, move3.id, "up")
        summaries = [n.summary for n in self.m.section_nodes(self.move.id)]
        self.assertEqual(summaries, ["制作元对象和相关组件约定", "点击地格", "寻路逻辑", "高亮渲染可移动的地格"])

    def test_log_reports_shifts(self):
        log: list[str] = []
        M.insert_node(
            self.m,
            section_id=self.move.id,
            before_node_id=self.move0.id,
            summary="x",
            body="x",
            log=log,
        )
        self.assertTrue(any("顺位偏移" in line for line in log))


class TestValidation(unittest.TestCase):
    def test_cycle_detected(self):
        m = load_co05()
        tile4 = next(n for n in m.nodes if n.section_id == m.sections[0].id and n.number == 4)
        move3 = next(n for n in m.nodes if n.summary == "寻路逻辑")
        # 瓦片4 已依赖 角色移动3；再让 角色移动3 依赖 瓦片4，构成环
        M.update_node(m, move3.id, {"refs": [{"raw": "地图4", "target_id": tile4.id}]})
        issues = M.validate(m)["issues"]
        self.assertTrue(any(i["kind"] == "cycle" for i in issues))
        cycles = [i["text"] for i in issues if i["kind"] == "cycle"]
        self.assertTrue(cycles)
        self.assertIn("成环", cycles[0])

    def test_empty_node_flagged(self):
        m = load_co05()
        empty = next(n for n in m.nodes if n.summary == "制作")
        M.update_node(m, empty.id, {"body": "", "summary": ""})
        issues = M.validate(m)["issues"]
        self.assertTrue(any(i["kind"] == "empty_node" for i in issues))


class TestRoundTrip(unittest.TestCase):
    def test_markdown_roundtrip_keeps_structure(self):
        m = load_co05()
        text = M.to_markdown(m)
        m2 = M.parse_markdown(text, source="roundtrip.md")
        self.assertEqual(len(m2.nodes), len(m.nodes))
        for a, b in zip(m.nodes, m2.nodes):
            self.assertEqual(a.summary, b.summary)
            self.assertEqual([r.raw for r in a.refs], [r.raw for r in b.refs])
            self.assertEqual([o.name for o in a.objects], [o.name for o in b.objects])

    def test_json_roundtrip(self):
        m = load_co05()
        data = json.loads(json.dumps(M.serialize(m), ensure_ascii=False))
        m2 = M.model_from_dict(
            {
                "title": data["title"],
                "source": data["source"],
                "preamble": data["preamble"],
                "aliases": data["aliases"],
                "meta": data["meta"],
                "sections": data["sections"],
                "nodes": data["nodes"],
            }
        )
        M.resolve_refs(m2)
        self.assertEqual([n.summary for n in m2.nodes], [n.summary for n in m.nodes])
        self.assertEqual(len(M.build_edges(m2)[0]), len(M.build_edges(m)[0]))

    def test_section_rename_rewrites_refs(self):
        m = load_co05()
        move = next(s for s in m.sections if s.title == "角色移动")
        M.update_section(m, move.id, {"title": "移动路线"})
        skill2 = next(n for n in m.nodes if "挂机动作" in n.summary)
        self.assertEqual(skill2.refs[0].raw, "移动路线1")

    def test_add_and_delete_section(self):
        m = load_co05()
        sec = M.insert_section(m, title="新路线")
        node = M.insert_node(m, section_id=sec.id, summary="第一步", body="第一步")
        self.assertEqual(m.index_label(node), "新路线 1")
        M.delete_section(m, sec.id)
        self.assertIsNone(m.node(node.id))
        self.assertEqual(len(m.nodes), 16)


if __name__ == "__main__":
    unittest.main(verbosity=2)
