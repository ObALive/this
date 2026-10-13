"""项目网络图模型单元测试。

用内置的任务书片段做夹具（不再依赖工作区里会变动的 `Task/` 文件）；
网络图的现行事实来源是工具库 `数据/项目网络图.sqlite`，其存取由 `test_db.py` 覆盖。

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

FIXTURE = """任务背景：
这是一段不计入网络图的背景说明。

本阶段你需要做的是：
1. 这一段标题之前的编号列表只作背景，不进网络图
2. 同上

## 瓦片地图
1. 平铺的地图绘制，每个瓦片无区别
2. 禁行地块，部分瓦片地图纹理笔刷设置禁止通过（依赖角色移动1）（增用 Tilemap作为地图编辑层，TilemapManager作为地图逻辑转换层 的设计方式。开发阶段通过Unity Tilemap笔刷绘制地图地形，运行时由独立的TilemapManager读取绘制信息。）
3. 场景道具摆放。当部分场景道具摆放到地图上的时候，摆放位置自动设置不可移动（元对象-角色标记组件，这个组件无功能，只作为将对象识别为角色的标记）（元对象-地格占用组件，用于记录对象以何种方式位于这个格子上）
4. 特殊障碍，部分场景道具不阻拦也不直接通行，而是设置在寻路时视为消耗格数增加（允许小数）（依赖角色移动3）
5. 特殊障碍，部分纹理笔刷以及场景道具摆放的时候，为地格添加效果（依赖元效果）
# 角色行为
## 角色技能
1. 制作元技能，以及相关组件约定
2. 设计一个挂机动作。并创建动作并列：轮到角色轮次时先选择要进行什么行动（放技能还是移动还是挂机），而不是默认进入角色移动的逻辑。并列为动作选择之一（依赖角色移动1）（元对象-技能容器组件）
3. 制作
## 角色移动
0. 制作元对象和相关组件约定，以及实现将元对象显示在地图的组件（元对象-场景纹理组件、元对象-场景坐标组件）
1. 点击地格，移动到对应位置（依赖地图1）
2. 高亮渲染可移动的地格，并添加移动格数限制属性（元对象-属性值组件）
3. 寻路逻辑，尝试寻找移动到对应位置的最短寻路，如果寻路失败则不可移动
# 时间轴
1. 为角色添加速度属性，并设置多角色，制作隐性时间轴，按照角色速度来决定角色行动轮次（依赖角色移动1）
2. 制作时间轴UI，显示各个角色在时间轴的位置
3. 制作时间轴预览，当鼠标悬浮在对应的行动上的时候，在时间轴上面虚化显示执行行动之后角色在时间轴的位置（依赖角色技能1）
4. 平滑化时间轴动画
"""


def load_fixture() -> M.Model:
    return M.parse_markdown(FIXTURE, source="fixture.md")


def label(m: M.Model, node: M.Node) -> str:
    return m.index_label(node)


class TestParse(unittest.TestCase):
    def setUp(self) -> None:
        self.m = load_fixture()

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

    def test_design_prose_goes_to_named_object(self):
        """括号里的设计说明点到了 TilemapManager，就该挂到那个对象下，而不是单立一条说明。"""
        tile2 = self.m.section_nodes(next(s.id for s in self.m.sections if s.title == "瓦片地图"))[1]
        self.assertEqual([o.name for o in tile2.objects], ["TilemapManager"])
        self.assertIn("TilemapManager作为地图逻辑转换层", tile2.objects[0].note)
        self.assertNotIn("TilemapManager", tile2.body)
        self.assertEqual(tile2.notes, [])

    def test_prose_without_object_name_stays_note(self):
        m = M.parse_markdown("## 路线\n1. 目标（这是一段超过二十四个字符但完全没有点名任何程序对象的设计说明文字，只讲做法。）\n", source="t.md")
        node = m.nodes[0]
        self.assertEqual(node.objects, [])
        self.assertEqual(len(node.notes), 1)

    def test_object_name_detection_rules(self):
        self.assertEqual(M._find_object_name_in("增用 Tilemap作为地图编辑层，TilemapManager作为逻辑转换层。"), "TilemapManager")
        self.assertIsNone(M._find_object_name_in("只用到 Unity 的 Tilemap 组件，其余按需再说。"))
        self.assertIsNone(M._find_object_name_in("先做一版最简实现，之后按需扩展，不点名任何对象。"))
        self.assertEqual(M._find_object_name_in("由地图占用数据管理器统一收集占用信息，编辑阶段生成数据。"), "地图占用数据管理器")

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
        self.m = load_fixture()
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
        m = load_fixture()
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
        m = load_fixture()
        empty = next(n for n in m.nodes if n.summary == "制作")
        M.update_node(m, empty.id, {"body": "", "summary": ""})
        issues = M.validate(m)["issues"]
        self.assertTrue(any(i["kind"] == "empty_node" for i in issues))


class TestRoundTrip(unittest.TestCase):
    def test_markdown_roundtrip_keeps_structure(self):
        m = load_fixture()
        text = M.to_markdown(m)
        m2 = M.parse_markdown(text, source="roundtrip.md")
        self.assertEqual(len(m2.nodes), len(m.nodes))
        for a, b in zip(m.nodes, m2.nodes):
            self.assertEqual(a.summary, b.summary)
            self.assertEqual([r.raw for r in a.refs], [r.raw for r in b.refs])
            self.assertEqual([o.name for o in a.objects], [o.name for o in b.objects])

    def test_json_roundtrip(self):
        m = load_fixture()
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
        m = load_fixture()
        move = next(s for s in m.sections if s.title == "角色移动")
        M.update_section(m, move.id, {"title": "移动路线"})
        skill2 = next(n for n in m.nodes if "挂机动作" in n.summary)
        self.assertEqual(skill2.refs[0].raw, "移动路线1")

    def test_add_and_delete_section(self):
        m = load_fixture()
        sec = M.insert_section(m, title="新路线")
        node = M.insert_node(m, section_id=sec.id, summary="第一步", body="第一步")
        self.assertEqual(m.index_label(node), "新路线 1")
        M.delete_section(m, sec.id)
        self.assertIsNone(m.node(node.id))
        self.assertEqual(len(m.nodes), 16)


class TestNestedRoutes(unittest.TestCase):
    """在二级路线（角色技能）下再建子路线。"""

    def setUp(self) -> None:
        self.m = load_fixture()
        self.skill = next(s for s in self.m.sections if s.title == "角色技能")

    def test_child_level_is_parent_level_plus_one(self):
        child = M.insert_section(self.m, title="技能子路线", parent_id=self.skill.id)
        self.assertEqual(child.parent_id, self.skill.id)
        self.assertEqual(child.level, self.skill.level + 1)
        self.assertEqual([s.title for s in self.m.section_path(child)], ["角色行为", "角色技能", "技能子路线"])

    def test_explicit_level_never_shallower_than_parent(self):
        child = M.insert_section(self.m, title="技能子路线", parent_id=self.skill.id, level=1)
        self.assertEqual(child.level, self.skill.level + 1)

    def test_unknown_parent_rejected(self):
        with self.assertRaises(ValueError):
            M.insert_section(self.m, title="坏路线", parent_id="不存在")

    def test_child_route_index_label_uses_full_path(self):
        child = M.insert_section(self.m, title="技能子路线", parent_id=self.skill.id)
        node = M.insert_node(self.m, section_id=child.id, summary="子步骤", body="子步骤")
        self.assertEqual(self.m.index_label(node), "角色行为/角色技能/技能子路线 1")

    def test_second_child_goes_after_existing_subtree(self):
        first = M.insert_section(self.m, title="子路线 A", parent_id=self.skill.id, after_subtree_of=self.skill.id)
        grand = M.insert_section(self.m, title="孙路线 A1", parent_id=first.id, after_subtree_of=first.id)
        second = M.insert_section(self.m, title="子路线 B", parent_id=self.skill.id, after_subtree_of=self.skill.id)
        order = [s.title for s in self.m.sections]
        self.assertEqual(order, ["瓦片地图", "角色行为", "角色技能", "子路线 A", "孙路线 A1", "子路线 B", "角色移动", "时间轴"])
        self.assertEqual([s.title for s in self.m.descendants(self.skill.id)], ["子路线 A", "孙路线 A1", "子路线 B"])

    def test_child_route_gets_own_column_and_head_inputs(self):
        child = M.insert_section(self.m, title="技能子路线", parent_id=self.skill.id, after_subtree_of=self.skill.id)
        view = M.serialize(self.m)
        section = next(s for s in view["sections"] if s["id"] == child.id)
        self.assertEqual(section["path"], "角色行为/角色技能/技能子路线")
        self.assertEqual(section["node_ids"], [])
        # 空的子路线会作为一条「还没有条目」的提示项出现在校验里，方便确认它已建好
        self.assertTrue(any(i["kind"] == "empty_section" and i.get("section_id") == child.id for i in view["issues"]))

    def test_markdown_roundtrip_keeps_nesting(self):
        child = M.insert_section(self.m, title="技能子路线", parent_id=self.skill.id, after_subtree_of=self.skill.id)
        M.insert_node(self.m, section_id=child.id, summary="子步骤", body="子步骤")
        text = M.to_markdown(self.m)
        self.assertIn("### 技能子路线", text)
        reparsed = M.parse_markdown(text, source="roundtrip.md")
        rebuilt = next(s for s in reparsed.sections if s.title == "技能子路线")
        parent = reparsed.section(rebuilt.parent_id)
        self.assertEqual(parent.title, "角色技能")
        node = reparsed.section_nodes(rebuilt.id)[0]
        self.assertEqual(reparsed.index_label(node), "角色行为/角色技能/技能子路线 1")

    def test_delete_parent_promotes_children(self):
        child = M.insert_section(self.m, title="技能子路线", parent_id=self.skill.id, after_subtree_of=self.skill.id)
        M.delete_section(self.m, self.skill.id)
        promoted = self.m.section(child.id)
        self.assertIsNotNone(promoted)
        self.assertEqual(self.m.section(promoted.parent_id).title, "角色行为")

    def test_child_route_placement_matches_ui_payload(self):
        # 界面发的是 after_section_id = 父级子树文档顺序的最后一条（不依赖服务端推导）
        first = M.insert_section(self.m, title="子路线 A", parent_id=self.skill.id, after_section_id=self.skill.id)
        M.insert_section(self.m, title="孙路线 A1", parent_id=first.id, after_section_id=first.id)
        anchor = self.m.descendants(self.skill.id)[-1].id
        M.insert_section(self.m, title="子路线 B", parent_id=self.skill.id, after_section_id=anchor)
        self.assertEqual(
            [s.title for s in self.m.sections],
            ["瓦片地图", "角色行为", "角色技能", "子路线 A", "孙路线 A1", "子路线 B", "角色移动", "时间轴"],
        )

    def test_move_child_route_only_swaps_siblings(self):
        a = M.insert_section(self.m, title="子路线 A", parent_id=self.skill.id, after_subtree_of=self.skill.id)
        b = M.insert_section(self.m, title="子路线 B", parent_id=self.skill.id, after_subtree_of=self.skill.id)
        M.move_section(self.m, b.id, "up")
        siblings = [s.title for s in self.m.child_sections(self.skill.id)]
        self.assertEqual(siblings, ["子路线 B", "子路线 A"])
        self.assertEqual(self.m.section(a.id).parent_id, self.skill.id)


class TestNoteReclassification(unittest.TestCase):
    """规则升级后，把库里已存的、属于某个对象的说明归位。"""

    def _model_with_note(self) -> M.Model:
        m = load_fixture()
        tile2 = m.section_nodes(next(s.id for s in m.sections if s.title == "瓦片地图"))[1]
        prose = "增用 Tilemap作为地图编辑层，TilemapManager作为地图逻辑转换层 的设计方式。开发阶段通过Unity Tilemap笔刷绘制地图地形。"
        tile2.notes = [prose]
        tile2.objects = []
        return m

    def test_reclassify_moves_prose_to_object(self):
        m = self._model_with_note()
        moves = M.reclassify_notes(m)
        tile2 = m.section_nodes(next(s.id for s in m.sections if s.title == "瓦片地图"))[1]
        self.assertEqual([o.name for o in tile2.objects], ["TilemapManager"])
        self.assertIn("TilemapManager作为地图逻辑转换层", tile2.objects[0].note)
        self.assertEqual(tile2.notes, [])
        self.assertEqual(moves[0]["object"], "TilemapManager")
        self.assertFalse(moves[0]["merged"])

    def test_reclassify_is_idempotent(self):
        m = self._model_with_note()
        M.reclassify_notes(m)
        self.assertEqual(M.reclassify_notes(m), [])

    def test_reclassify_merges_into_existing_object(self):
        m = self._model_with_note()
        tile2 = m.section_nodes(next(s.id for s in m.sections if s.title == "瓦片地图"))[1]
        tile2.objects = [M.ObjectItem(name="TilemapManager", note="先建的说明")]
        moves = M.reclassify_notes(m)
        self.assertTrue(moves[0]["merged"])
        self.assertIn("先建的说明", tile2.objects[0].note)
        self.assertIn("作为地图逻辑转换层", tile2.objects[0].note)

    def test_reclassify_keeps_unowned_note(self):
        m = load_fixture()
        tile1 = m.section_nodes(next(s.id for s in m.sections if s.title == "瓦片地图"))[0]
        tile1.notes = ["这段说明超过二十四个字符，但完全没有点名任何程序对象，应该原样留着。"]
        self.assertEqual(M.reclassify_notes(m), [])
        self.assertEqual(len(tile1.notes), 1)

    def test_reclassify_op_reports_log(self):
        m = self._model_with_note()
        result = M.apply_op(m, "reclassify_notes", {})
        self.assertTrue(result["moved"])
        self.assertTrue(any("已归属对象" in line for line in result["log"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
