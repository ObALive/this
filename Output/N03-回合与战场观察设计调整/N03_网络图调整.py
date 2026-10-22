"""Prepare and apply the approved graph change through the existing HTTP API."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'Tool/项目网络图'))
import model as M

DATASET = 'N01_完整依赖清理新图_v2.sqlite'
URL = 'http://127.0.0.1:8791'
TASK = 'N03-回合与战场观察设计调整'
DEFER = '具体实现路径在实施本节点时讨论，沿用架构已定约束；未给定的规则和配置输入届时明确，不以临时输入替代正式规则。'


def get_state():
    with urllib.request.urlopen(URL + '/api/state', timeout=10) as response:
        data = json.load(response)
    assert data['dataset_id'] == DATASET, '当前工具打开的数据库已改变，停止写入'
    assert Path(data['config']['db_file']).name == DATASET
    return data


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def post(path, payload):
    payload['dataset_id'] = DATASET
    request = urllib.request.Request(URL + path, json.dumps(payload, ensure_ascii=False).encode(), {'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    assert data.get('ok'), data
    return data


def write_json(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def prepare():
    state = get_state()
    original = state['model']
    model = M.model_from_dict(original)
    before = copy.deepcopy(model)
    assert len(model.nodes) == 146, '节点数量改变，请重新审阅当前库'
    assert model.node('n13').summary == '多角色共用时间轴'
    assert model.node('n36').summary == '行动后摇与速度回排'
    assert 'ElectedObject' in model.node('n13').objects[0].path

    def edit(ident, body, summary=None):
        node = model.node(ident)
        assert node is not None, ident
        node.body = body
        if summary:
            node.summary = summary
        return node

    def add_ref(ident, target):
        node = model.node(ident)
        if not any(r.target_id == target for r in node.refs):
            node.refs.append(M.Ref(raw='', target_id=target))

    def section(title, parent=None):
        value = M.Section(model.next_id('s'), title, 2 if parent else 1, parent_id=parent)
        model.sections.append(value)
        return value.id

    # Change routes and order before re-numbering. Bound references are preserved by ID.
    logic = section('逻辑', 's5')
    ui = section('UI', 's5')
    observe = section('战场观察')
    detail = section('单位详情', observe)
    camera = section('镜头', observe)
    for ident in ['n36', 'n38']:
        model.node(ident).section_id = logic
    for ident in ['n14', 'n15', 'n16', 'n21', 'n37']:
        model.node(ident).section_id = ui
    model.node('n50').section_id = detail

    def add_node(route, summary, body, refs=()):
        node = M.Node(model.next_id('n'), route, 1, summary, body)
        model.nodes.append(node)
        for target in refs:
            add_ref(node.id, target)
        return node.id

    clock = add_node(logic, '战斗净时长累计', '战斗局部按秒持有和累计本次战斗净时长，收尾窗口停止累计；供显示及外部时间结算读取。累计逻辑独立于显示和动画，沿用架构的逻辑时间约束。' + DEFER)
    save = add_node(logic, '轮次保存与恢复接入边界', '在单位获得行动机会的轮次起点提供战斗状态采集与恢复接入边界；恢复落在最近一次行动机会开始时，未确认选择按表现编辑态处理。本阶段登记接入边界，实际存档服务和外部世界时间流转延期建设。' + DEFER)
    pan = add_node(camera, '战场镜头平移和缩放', '玩家在战斗中可平移、缩放镜头观察战场；相机与表现状态变化不提交角色行动，不改变战斗规则对象的位置、属性、Buff或行动机会归属，不误触移动、目标确认等战斗命令。输入方式、范围及冲突处理在实施本节点时讨论。', ['n30'])
    center = add_node(camera, '镜头定位当前行动者', '玩家可将镜头定位到时间轴给出的当前行动者；定位不改变查看对象、行为目标或行动机会。是否同时恢复缩放与朝向、输入和反馈方式在实施本节点时讨论。', ['n36'])

    old_object = model.node('n13').objects[0]
    new_core = edit('n36', '场景中存在多个参战角色，敌我全部单位共用一条时间轴。根据战斗配置初始化行动标记并选出首个行动者；单位完成行动后，以行为后摇、技能后摇及行动速度补正计算其下一次行动时机并回排，再按时间轴排序选取下一行动者并授予行动机会。当前行动者可以通过基础调试信息验收，调度独立于UI、预览和动画。实际回排与预览使用一致的计算规则和配置输入。' + DEFER, '共享时间轴调度与行动回排')
    new_core.objects.append(M.ObjectItem(old_object.name, '战斗行动顺序与当前行动机会的唯一管理入口；管理多角色行动标记、初始化排序、行动后回排和下一行动者选取。保存ElectedObject作为当前行动者的权威状态，查看对象和技能目标不改写该值。我方获授机会后等待玩家决策，敌方交由AI决策；角色行为的生命周期、触发与生效时机由元技能统一管理。数据与表现分离，具体字段之外的结构、算法与协作路径在实施节点时讨论。', ''))
    for item in model.node('n13').refs:
        if not any(r.target_id == item.target_id for r in new_core.refs):
            new_core.refs.append(copy.deepcopy(item))
    # Redirect every original binding before deleting the old node.
    for node in model.nodes:
        for ref in node.refs:
            if ref.target_id == 'n13':
                ref.target_id = 'n36'
    model.nodes.remove(model.node('n13'))

    edit('n38', '同一行动机会只受理一项有效确认行为。提交者须与ElectedObject所表示的当前行动者一致，并满足当前机会与角色行为生命周期的受理条件；重复确认、执行期间再次提交及旧机会遗留命令均不能额外执行。元技能统一管理角色行为的生命周期、触发时机和生效时机；行为执行与必要结算完成后回排并关闭当前机会，再授予下一机会。选物和技能内的法术选择不能额外产生行动机会。自由查看与复合步骤的表述在实施对应交互时整理，并遵守已定的玩家操作和战斗规则状态边界。' + DEFER)
    # Core opportunity handling must not depend on the skill panel UI.
    model.node('n38').refs = [r for r in model.node('n38').refs if r.target_id != 'n27']
    add_ref('n38', 'n6')
    edit('n6', model.node('n6').body + '\n元技能统一管理角色行为的生命周期、触发时机、生效时机及完成或终止的交接，方便统一校验；各类行为沿用自身行为契约及效果结算职责。' + DEFER)
    if not any(o.name == '元技能' for o in model.node('n6').objects):
        model.node('n6').objects.append(M.ObjectItem('元技能', '角色行为生命周期的统一管理对象；触发、生效、完成与终止的具体协议在节点实施时讨论。'))

    edit('n21', '战斗HUD读取战斗净时长累计结果并显示本次战斗以秒计的耗时；收尾窗口读取停止累计后的结果。显示更新独立于累计逻辑，具体呈现与绑定在实施本节点时讨论。', '战斗净时长显示')
    add_ref('n21', clock)
    edit('n32', '时间轴推进至单位后默认选中该单位；查看其他单位只切换详情和行动槽，其面板不显示可操作按钮且标为不可操作，无法借查看提交其行动。战斗业务受理方校验行动主体是否为ElectedObject表示的当前行动者及当前机会是否可受理；界面按结果呈现权限。' + DEFER)
    add_ref('n32', 'n38')
    edit('n22', '轮到敌人获得行动机会时，由AI自动决策并执行最近敌对目标移动与待机的占位动作；通过统一的元技能行为生命周期完成行动，再按共享时间轴回排并交给下一行动者。正式模板由本路线后续条目补齐。' + DEFER)
    add_ref('n22', 'n36')
    add_ref('n22', 'n38')
    # Keep the approved detail description intact except for extracting camera movement.
    edit('n50', model.node('n50').body.replace('玩家能拖动场景观察战况、点选单位查看详情', '玩家能点选单位查看详情'))
    add_ref('n50', 'n41')

    for ident, text in {
        'n39': '失能结果接入当前行动资格校验与时间轴机会管理；涉及正在执行行为时由元技能统一承接生命周期。',
        'n40': '恢复结果接入行动资格和时间轴；由元技能统一承接恢复行为的触发与生效生命周期。',
        'n66': '持续伤害结算与元技能行为触发、生效及时间轴轮次边界对齐；效果规则仍归效果结算。',
        'n67': '限时状态的到期处理与轮次边界及元技能行为生命周期对齐，时间单位与具体触发口径在实施时讨论。',
        'n115': '后续波次新增单位接入既有时间轴，保留已在场单位的标记和行动槽；入轴依据在实施时明确。',
        'n129': '结束判定与元技能当前行为终止、时间轴停止授予新机会统一交接；旧选择及遗留命令失效。',
        'n130': '输出战斗结果时完成与行动调度的交接，结束后不再授予行动机会；具体顺序与清理在实施时讨论。',
    }.items():
        edit(ident, model.node(ident).body + '\n' + text + DEFER)
        add_ref(ident, 'n38')

    # Logical/UI route separation: UI reads logical output, never the reverse.
    for ident in ['n14', 'n15', 'n16', 'n37']:
        add_ref(ident, 'n36')

    # Group nodes into their final route order and re-number without rebinding targets.
    original_sections = [s for s in model.sections if s.id not in [logic, ui, observe, detail, camera]]
    ordered_sections = []
    for s in original_sections:
        ordered_sections.append(s)
        if s.id == 's5':
            ordered_sections.extend([model.section(logic), model.section(ui)])
        if s.id == 's9':
            ordered_sections.extend([model.section(observe), model.section(detail), model.section(camera)])
    model.sections = ordered_sections
    group = {logic: ['n36', 'n38', clock, save], ui: ['n14', 'n15', 'n16', 'n21', 'n37'], detail: ['n50'], camera: [pan, center]}
    ordered_nodes = []
    for s in model.sections:
        nodes = [model.node(i) for i in group[s.id]] if s.id in group else model.section_nodes(s.id)
        for index, node in enumerate(nodes, s.start_number):
            node.number = index
        ordered_nodes.extend(nodes)
    model.nodes = ordered_nodes
    for node in model.nodes:
        for ref in node.refs:
            target = model.node(ref.target_id)
            assert target is not None, (node.id, ref.raw)
            # Full route paths survive the split and round-trip without caches.
            if target.section_id in [logic, ui, detail, camera] or not ref.raw:
                ref.raw = model.index_label(target).replace(' ', '')
                ref.section = model.section(target.section_id).title
                ref.number = target.number
    M.sync_all_refs(model)
    M.resolve_refs(model)
    check = M.validate(model)
    assert check['stats']['errors'] == 0, check['issues']
    # Verify every textual dependency resolves to exactly the bound target.
    for node in model.nodes:
        for ref in node.refs:
            assert M.resolve_ref_text(model, ref.raw)[0] == ref.target_id, (node.id, ref.raw, ref.target_id)
    edges, _ = M.build_edges(model)
    upstream = {}
    for edge in edges:
        upstream.setdefault(edge['to'], set()).add(edge['from'])
    def ancestors(ident):
        seen = set(); pending = list(upstream.get(ident, []))
        while pending:
            current = pending.pop()
            if current not in seen:
                seen.add(current); pending.extend(upstream.get(current, []))
        return seen
    ui_ids = {n.id for n in model.section_nodes(ui)}
    assert not any(ancestors(n.id) & ui_ids for n in model.section_nodes(logic))
    assert 'n125' not in ancestors('n50'), '查看仍间接依赖撤退'
    assert 'n36' in ancestors('n22')
    assert len(model.nodes) == 149

    changes = []
    for old in before.nodes:
        new = model.node(old.id)
        if new is None:
            changes.append({'id': old.id, 'before': before.index_label(old), 'after': model.index_label(model.node('n36')), 'action': '合并删除；全部引用重定向'})
        elif old.to_dict() != new.to_dict():
            changes.append({'id': old.id, 'before': before.index_label(old), 'after': model.index_label(new), 'summary': new.summary, 'body_changed': old.body != new.body, 'objects_changed': old.objects != new.objects, 'refs_changed': old.refs != new.refs})
    for node in model.nodes:
        if before.node(node.id) is None:
            changes.append({'id': node.id, 'before': '', 'after': model.index_label(node), 'summary': node.summary, 'action': '新增'})
    candidate = M.serialize(model)
    write_json('N03_网络图候选模型.json', candidate)
    write_json('N03_节点映射与变更.json', changes)
    write_json('N03_执行基线.json', {'task': TASK, 'dataset': DATASET, 'model_hash': digest(original), 'candidate_hash': digest(candidate), 'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), 'original_stats': original['stats'], 'candidate_stats': candidate['stats'], 'view_ancestors_before': 62, 'view_ancestors_after': len(ancestors('n50')), 'checks': ['无未解析与环', '引用原文重解析目标一致', '逻辑不依赖UI', '查看不依赖撤退', '敌人AI依赖新时间轴1', '保留未改节点与用户既有修改']})
    print(json.dumps({'prepared': True, 'stats': candidate['stats'], 'changed_nodes': len(changes), 'observation_ancestors': len(ancestors('n50'))}, ensure_ascii=False))


def apply():
    baseline = json.loads((OUT / 'N03_执行基线.json').read_text(encoding='utf-8'))
    candidate = json.loads((OUT / 'N03_网络图候选模型.json').read_text(encoding='utf-8'))
    current = get_state()['model']
    assert digest(current) == baseline['model_hash'], '准备后图已发生变化，需重新审阅，禁止覆盖'
    assert digest(candidate) == baseline['candidate_hash']
    response = post('/api/op', {'op': 'replace', 'args': {'model': candidate}})
    actual = response['model']
    assert digest(actual) == digest(candidate), '写入结果与候选模型不一致'
    export = f'Output/{TASK}/N03_网络图导出.md'
    post('/api/export', {'path': export})
    write_json('N03_接口执行结果.json', {'dataset': DATASET, 'result_hash': digest(actual), 'stats': actual['stats'], 'export': export, 'api': '/api/op replace；/api/export', 'service': '复用已有127.0.0.1:8791服务；未启停服务或切换数据库'})
    print(json.dumps({'applied': True, 'stats': actual['stats'], 'export': export}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    apply() if args.apply else prepare()
