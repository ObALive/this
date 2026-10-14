"""只对 N01 副本运行现有 HTTP 模型操作；不直接改 SQLite 行。"""
from pathlib import Path
import sys, json, hashlib, threading, urllib.request, csv
from datetime import datetime
from collections import Counter, defaultdict, deque

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'Tool/项目网络图'))
import db, model as M, store, server
from N01_补图规格_v1 import ROWS, SOURCES, GAPS, OUTSIDE

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def model_sha(m):
    return hashlib.sha256(json.dumps(db.model_payload(m), ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
def save(name, value):
    (OUT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2) if not isinstance(value, str) else value, encoding='utf-8')
def source_text(refs):
    result=[]
    for ref in refs if isinstance(refs,list) else refs.split(';'):
        code, clause=ref.split(':',1)
        path=SOURCES[code]
        assert (ROOT/path).exists(), path
        result.append(f'`{path}` §{clause}')
    return '<br>'.join(result)

manifest = json.loads((OUT/'N01_基线登记_v1.json').read_text(encoding='utf-8'))
backup=OUT/'N01_原图一致性备份_v1.sqlite'
editable=OUT/'N01_战斗玩家功能新图_v1.sqlite'
original=ROOT/'Tool/项目网络图/数据/项目网络图.sqlite'
base=db.load_model(backup)
assert model_sha(base)==manifest['model_sha256']
assert model_sha(db.load_model(editable))==manifest['model_sha256'], '副本已编辑，不重复覆盖'
assert model_sha(db.load_model(original))==manifest['model_sha256'], '原图已发生变化，需核实基线'
assert len({r['key'] for r in ROWS})==len(ROWS)
store.DB_FILE=editable
# export/save 的目录全部隔离到 N01，避免默认数据/导出下产生文件。
store.DATA_DIR=OUT
store.BACKUP_DIR=OUT
store.EXPORT_DIR=OUT
class QuietHandler(server.Handler):
    def log_message(self, *args):
        pass
http=server.ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
port=http.server_port
thread=threading.Thread(target=http.serve_forever,daemon=True)
thread.start()
log=[]
def call(path, body=None):
    raw=json.dumps(body,ensure_ascii=False).encode('utf-8') if body is not None else None
    req=urllib.request.Request(f'http://127.0.0.1:{port}{path}',data=raw,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=30) as res:
        data=res.read()
    value=json.loads(data) if path!='/api/markdown' else data.decode('utf-8')
    if isinstance(value,dict):
        assert value.get('ok'), value
    return value
def op(name,args):
    result=call('/api/op',{'op':name,'args':args})
    log.append({'op':name,'args':args,'log':result.get('log',[])})
    return result

try:
    payload=db.model_payload(base)
    payload['title']='N01 战斗玩家功能补图 · 已确定落点与待裁定事项'
    payload['source']='Task/N系列任务/N01-战斗玩家功能补图.md'
    payload['preamble']='本图从用户当前原图的一致性备份增量补齐战斗玩家功能。启动即进入预置战斗，固定输入仅隔离外部系统。每项正文为触发与可观察结果；原图组件及技术说明保持。G01—G14 为上游未决，具体见同目录 N01_未决事项_v1.md。带待裁定标记的条目及其依赖后继不计入完整可验收覆盖。此图尚未满足完整补图完成判据。技术选型与完整技术依赖审计由独立任务承接；未采用其他任务产物。'
    op('replace',{'model':payload})
    section_ids={s.title:s.id for s in base.sections}
    for route in dict.fromkeys(r['route'] for r in ROWS):
        if route not in section_ids:
            section_ids[route]=op('insert_section',{'title':route,'level':1,'start_number':1})['section_id']
    ids={n.id:n.id for n in base.nodes}
    gap_names={g[0]:g[1] for g in GAPS}
    for r in ROWS:
        body=r['body']
        if r['blockers']:
            body+='\n待裁定：'+'；'.join(g+ ' '+gap_names[g] for g in r['blockers'])+'。本条先承接已定部分，受影响验收暂不通过。'
        if r['key'] in ids:
            # reparse=False 保留原对象/路径/备注/依赖，不将正文中的解释误归类。
            op('update_node',{'node_id':ids[r['key']],'summary':r['summary'],'body':body,'reparse':False})
        else:
            ids[r['key']]=op('insert_node',{'section_id':section_ids[r['route']],'summary':r['summary'],'body':body})['node_id']
    state=call('/api/state')
    current=M.model_from_dict(state['model'])
    expected={}
    for r in ROWS:
        node=current.node(ids[r['key']])
        # 既有已绑定引用原文保留，新引用用工具当前索引绑定，避免后缀猜测。
        refs=[dict(raw=x.raw,target_id=x.target_id) for x in node.refs]
        for key in r['refs']:
            assert key in ids, f"{r['key']} -> {key}"
            target=current.node(ids[key])
            section=current.section(target.section_id)
            if target.id not in {x['target_id'] for x in refs}:
                refs.append({'raw':f'{section.title}{target.number}','target_id':target.id})
        if refs:
            op('update_node',{'node_id':node.id,'refs':refs,'reparse':False})
        expected[node.id]=[x['target_id'] for x in refs]
    state=call('/api/state')
    current=M.model_from_dict(state['model'])
    validation=M.validate(current)
    save('N01_模型校验_v1.json',validation)
    errors=[x for x in validation.get('issues',[]) if x['level']=='error']
    assert not errors, errors
    exported=call('/api/export',{'path':'Output/N01-战斗玩家功能补图/N01_战斗玩家功能新图_v1.md'})
    assert exported['markdown']==call('/api/markdown')==M.to_markdown(current)
    checks=db.verify(editable)
    assert checks['integrity']=='ok' and checks['foreign_key_errors']==0
    reloaded=db.load_model(editable)
    assert db.model_payload(current)==db.model_payload(reloaded)
    assert model_sha(db.load_model(original))==manifest['model_sha256']
    assert sha(original)==manifest['source_file_sha256']
    assert sha(backup)==manifest['backup_file_sha256']
    for node in current.nodes:
        assert [x.target_id for x in node.refs]==expected[node.id]
    object_preservation=[]
    for old in base.nodes:
        new=current.node(old.id)
        oldobjects=[o.to_dict() if hasattr(o,'to_dict') else vars(o) for o in old.objects]
        newobjects=[o.to_dict() if hasattr(o,'to_dict') else vars(o) for o in new.objects]
        assert oldobjects==newobjects, old.id
        assert old.notes==new.notes and old.manual==new.manual, old.id
        object_preservation.append({'original':base.index_label(old),'objects_unchanged':True,'notes_unchanged':True,'manual_unchanged':True})
    save('N01_API操作记录_v1.json',log)
    save('N01_新图完整模型_v1.json',db.model_payload(current))
    # 来源文件内容摘要：仅登记实际引用资料，无 N02 读取。
    source_files=[ROOT/'Rules/README.md',ROOT/'Rules/01_规范总则.md',ROOT/'Rules/02_任务执行规范.md',ROOT/'Rules/03_文档编辑规范.md',ROOT/'Rules/05_文档库组织规范.md',ROOT/'Rules/08_交互原语与交互语义设计规范.md',ROOT/'系统设计文档/README.md',ROOT/'系统设计文档/06-战斗/06_战斗索引.md',ROOT/'系统设计文档/00-总览/02_术语表.md',ROOT/'Tool/项目网络图/读库说明.md',ROOT/'Tool/项目网络图/使用说明.md']+[ROOT/p for p in SOURCES.values()]
    save('N01_资料登记_v1.json',[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in dict.fromkeys(source_files)])
    # 拓扑顺序及上游未决的传递阻塞。
    edges,_=M.build_edges(current)
    children=defaultdict(list)
    parents=defaultdict(list)
    for e in edges:
        children[e['from']].append(e['to'])
        parents[e['to']].append(e['from'])
    indeg={n.id:len(parents[n.id]) for n in current.nodes}
    queue=deque(nid for nid,d in indeg.items() if not d)
    order=[]
    while queue:
        nid=queue.popleft();order.append(nid)
        for nxt in children[nid]:
            indeg[nxt]-=1
            if not indeg[nxt]:queue.append(nxt)
    assert len(order)==len(current.nodes),'依赖环'
    effective={ids[r['key']]:set(r['blockers']) for r in ROWS}
    for nid in order:
        for nxt in children[nid]:
            effective[nxt].update(effective[nid])
    labels={r['key']:current.index_label(current.node(ids[r['key']])) for r in ROWS}
    details=[]
    for idx,r in enumerate(ROWS,1):
        details.append({**r,'feature_id':f'N01-F{idx:03}','new_location':labels[r['key']],
                        'original_locations':[base.index_label(base.node(x)) for x in r['original']],
                        'effective_blockers':sorted(effective[ids[r['key']]])})
    save('N01_功能覆盖数据_v1.json',details)
    fields=['feature_id','summary','prior','original_locations','new_location','sources','blockers','effective_blockers']
    with (OUT/'N01_功能覆盖对照_v1.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for d in details:
            writer.writerow({k:'；'.join(d[k]) if isinstance(d[k],list) else d[k] for k in fields})
    doc=['# N01 功能覆盖与变更对照','',f'日期：2026-10-14。基线模型 SHA256：`{manifest["model_sha256"]}`。','',
         '本表是规则到图上验收行为的拆分清单。原图判断读取了完整正文、依赖、对象路径/说明和备注，不能由同名概要推定覆盖。已有完整落点指该项局部行为完整，不代表整套战斗已完成。新图落点只表示完成设计承接；配置待给出、规则待裁定和依赖后继均不算已通过验收。','',
         f'原图 {len(base.sections)} 路线 / {len(base.nodes)} 条；新图 {len(current.sections)} 路线 / {len(current.nodes)} 条。原状态分布：{dict(Counter(r["prior"] for r in ROWS))}。直接带未决 {sum(bool(r["blockers"]) for r in ROWS)} 项，经依赖传播受影响 {sum(bool(x) for x in effective.values())} 项。','',
         '## 资料覆盖','',
         '战斗域索引的十二系统全文及四张战斗配置表逐项读取；按战斗职责延伸阅读物品、背包、物品操作总表、词条表、角色与小队、全局跨系统规则和术语表。范围外与占位记录单独列于本文件末尾，不以配置名称替代具体操作。','',
         '| 资料 | 本轮核对落点 |','| --- | --- |']
    for code,path in SOURCES.items():
        matches=[d['feature_id'] for d in details if any(s.startswith(code+':') for s in d['sources'])]
        doc.append(f'| `{path}` | '+('、'.join(matches) or '范围外与未决条款核对')+' |')
    doc+=['','## 原 29 条目变更','', '| 原落点与概要 | 处理 | 新落点 |','| --- | --- | --- |']
    for old in base.nodes:
        related=[d for d in details if old.id in d['original']]
        assert related,old.id
        doc.append(f'| {base.index_label(old)} · {old.summary} | '+('保留局部有效行为，细化验收正文' if related[0]['prior']=='已有完整落点' else '完善/拆分不完整行为；原组件和技术说明保留')+' | '+'<br>'.join(d['new_location']+' · '+d['summary'] for d in related)+' |')
    doc+=['','## 逐项功能对照','', '| 功能ID / 玩家目标 | 依据 | 原图判断与落点 | 新图落点 | 直接未决 / 依赖传递未决 |','| --- | --- | --- | --- | --- |']
    for d in details:
        doc.append(f'| {d["feature_id"]} · {d["summary"]} | {source_text(d["sources"])} | {d["prior"]}：'+('、'.join(d['original_locations']) or '—')+f' | {d["new_location"]} | '+('、'.join(d['blockers']) or '—')+' / '+('、'.join(d['effective_blockers']) or '—')+' |')
    doc+=['','## 本阶段范围外','', '| ID | 条款 | 依据 | 延期理由与战斗内承接 | 新图承接 |','| --- | --- | --- | --- | --- |']
    for code,name,source,reason,keys in OUTSIDE:
        doc.append(f'| {code} | {name} | {source_text(source)} | {reason} | '+'、'.join(labels[k] for k in keys.split())+' |')
    doc+=['','## 原图与现行规则的差异','',
          '- 角色属性5 的 20% 单次伤害受伤、二级伤势归零死亡没有现行设计依据，改为生命阈值与伤势两层模型并列 G03。',
          '- 时间轴1 的速度排序是初期阶段；正式回排补行为/技能后摇和速度补正，不擅定公式。',
          '- 敌人ai1 的最近目标移动是占位阶段；攻击、移动、能力、防御、读招、破招、撤退和波次分别补正式节点。',
          '- 角色技能3 的四类效果是原图组件试验，拆成固定伤害、方向位移、3×3 范围和 10% 最大生命伤害；不把它们等同于正式 A/B/C/D 全量技能清单。',
          '- 角色技能6 先无继承是明确的中间构建简化，继承效果与多产出计次由后续节点补齐。',
          '- 角色技能7 原有移动/待机/技能鼠标操作保留为分条语义，不创造新键位；原语、绑定以及隐藏交互等价入口缺口列 G12。',
          '- 瓦片地图4 小数通行成本来自当前原图，纳入路径预算；行动力换算仍依赖上游数值输入。',
          '- 原图“寻路”承接战场内部合法路径计算；系统 30 排除的是地图自动寻路入口，边界单独说明。',
          '- 新图保留全部原对象路径、备注、手工布局和既有绑定依赖；新增直接前置用明确目标绑定，未开展完整技术依赖审计。','']
    save('N01_功能覆盖与变更对照_v1.md','\n'.join(doc))
    gaps=['# N01 未决事项与裁定入口','',
          '状态：14 项未决。以下均未自行裁定，不能作为已完成覆盖计算。局部行为和配置入口已在新图保留，可在上游裁定后继续编辑。候选只描述需要明确的规则，不推荐新玩法。','',
          '| ID / 事项 | 依据 | 现状、冲突与影响 | 所需裁定或输入 | 直接涉及图上条目 |','| --- | --- | --- | --- | --- |']
    for code,name,source,problem,question in GAPS:
        involved=[labels[r['key']] for r in ROWS if code in r['blockers']]
        gaps.append(f'| {code} · {name} | {source_text(source)} | {problem} | {question} | '+'<br>'.join(involved)+' |')
    gaps+=['','## 交付判断','',
           '范围内已确定规则已有图上行为承接，但 G01—G14 的必要规则、配置及交互规格仍影响验收，完整覆盖尚未达成。本轮交付已完成的分析、新图和核验；不改上游设计，也不等待 N02 的分析。N02 同基线一致性仅能由外部按模型 SHA256 比对，本任务未读取其产物。','']
    save('N01_未决事项_v1.md','\n'.join(gaps))
    verification={
      'checked_at':datetime.now().astimezone().isoformat(),'stats':M.serialize(current)['stats'],
      'database':checks,'errors':errors,'original_file_unchanged':True,'original_model_unchanged':True,
      'backup_file_unchanged':True,'backup_recoverable':db.model_payload(db.load_model(backup))==db.model_payload(base),
      'export_matches_api_and_model':True,'reload_model_equal':True,'refs_match_expected_bindings':True,
      'original_object_notes_paths_preserved':object_preservation,
      'topological_order':[current.index_label(current.node(nid)) for nid in order],
      'base_model_sha256':manifest['model_sha256'],'new_model_sha256':model_sha(current),
      'new_file_sha256':sha(editable),'export_file_sha256':sha(OUT/'N01_战斗玩家功能新图_v1.md'),
      'feature_count':len(ROWS),'direct_blocked_count':sum(bool(r['blockers']) for r in ROWS),
      'effective_blocked_count':sum(bool(x) for x in effective.values()),'full_coverage_achieved':False,
      'outside_count':len(OUTSIDE),'upstream_gap_count':len(GAPS),'N02_baseline_comparison':'待外部核对，未读取 N02 产物',
    }
    save('N01_核验结果_v1.json',verification)
    print(json.dumps({k:v for k,v in verification.items() if k not in ('topological_order','original_object_notes_paths_preserved','database')},ensure_ascii=False,indent=2))
finally:
    http.shutdown();http.server_close();thread.join(timeout=5)
    timestamp=datetime.now().astimezone().isoformat()
    save('system_operation_log.md',f'''# N01 系统操作记录

时间：{timestamp}
执行命令：`python -X utf8 Output/N01-战斗玩家功能补图/N01_执行补图_v1.py`
执行目的：通过现有项目网络图 HTTP 模型 API 编辑 N01 副本并在任务目录导出。
影响范围：仅 `Output/N01-战斗玩家功能补图/`；本机临时服务监听 `127.0.0.1:{port}`，在脚本内将 store 的库和导出路径定向到本目录。未修改用户环境变量、默认原图库或工具代码。
执行结果：执行细节见 API 操作记录与核验结果；服务在 finally 中停止，端口释放。
恢复方案：原图备份保持不变；需要重新构建时选择新的产物名称或经授权编辑副本。不要对默认原图库导入、重置或替换。

基线备份采用 SQLite 在线 backup API，源连接只读；未直接改业务表行。
''')
