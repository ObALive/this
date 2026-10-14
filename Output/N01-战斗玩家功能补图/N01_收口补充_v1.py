"""收口逐条检查补充目标类型与效果终止的独立验收单位。"""
from pathlib import Path
import sys,json,threading,urllib.request,hashlib,csv
from collections import defaultdict,deque,Counter
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/'Tool/项目网络图'))
import model as M,db,server,store
from N01_补图规格_v1 import ROWS,SOURCES,GAPS

extra=[
 dict(key='R09',route='目标类型与持续战斗',summary='全歼目标进度',body='击杀战斗配置中的敌方单位后，显式全歼目标的进度即时变化；是否涵盖后续未刷波次以及最终敌方清除的结束判定待 G01。预置配置不得将每波清场自行当作整场胜利。',sources=['A0:3.1、3.2','90:3.5'],refs=['D01','D09'],original=[],prior='没有落点',blockers=['G01','G09']),
 dict(key='R10',route='目标类型与持续战斗',summary='指定精英目标进度',body='配置显式击败精英目标时，仅配置声明的精英状态改变推进该目标；击败其他敌人不代替指定精英，达到已声明条件时记录达成，战斗结束时点待 G01。',sources=['A0:3.1、3.2'],refs=['D01'],original=[],prior='没有落点',blockers=['G01','G09']),
 dict(key='R11',route='目标类型与持续战斗',summary='指定道具破坏进度',body='配置显式破坏指定道具目标时，指定道具的已提交破坏状态推进该目标；其他道具变化不替代该目标。保全道具类目标被提前破坏时走目标失效判定；条件与阈值由目标配置提供。',sources=['A0:3.1、3.2'],refs=['W02','R02'],original=[],prior='没有落点',blockers=['G01','G09']),
 dict(key='R12',route='目标类型与持续战斗',summary='隐藏目标发现与达成',body='配置为隐藏的目标不在启动时作为显式条件公开；玩家的已提交行动满足其配置条件时记录发现或达成。发现与显示的具体时点和条件缺少规则，待 G01/G09，不自行增加探索玩法。',sources=['A0:3.1'],refs=['E01','R01'],original=[],prior='没有落点',blockers=['G01','G09']),
 dict(key='R13',route='目标类型与持续战斗',summary='持续战斗无轮次上限',body='目标尚未达成且敌方尚未全灭时继续按时间轴给予行动机会，系统不以战斗轮次数达到内置上限结束。临时验收可延长已配置战斗的运行次数，只验证无系统轮限，不作为新目标条件。',sources=['A0:3.2'],refs=['T03','R02'],original=[],prior='没有落点',blockers=['G01']),
 dict(key='F08',route='效果结算',summary='免疫终止状态效果',body='目标的已配置免疫规则使状态附加无效时，按该状态的登记规则移除或停止生效，详情更新有效状态。免疫介入层与时点待 G07。',sources=['EFF:EFF-STATE-001','75:3.4'],refs=['F01'],original=[],prior='没有落点',blockers=['G07','G09']),
 dict(key='F09',route='效果结算',summary='解除条件移除状态',body='已提交行为满足状态来源配置的解除条件时移除该状态并更新详情；其他尚未满足解除条件的来源状态保留。具体解除条件和触发顺序由配置及 G07 承接。',sources=['EFF:EFF-STATE-001','75:3.5'],refs=['F01'],original=[],prior='没有落点',blockers=['G07','G09']),
 dict(key='F10',route='效果结算',summary='投掷一次性效果移除',body='投掷动作结算结束时移除本次一次性投掷效果，已生成的落地物按其归属保留；不因效果结束清除物品或容器内容。',sources=['75:3.5','EFF:EFF-THROW-001','80:5'],refs=['I09'],original=[],prior='没有落点',blockers=['G07','G08']),
]
prod=OUT/'N01_战斗玩家功能新图_v1.sqlite';backup=OUT/'N01_原图一致性备份_v1.sqlite'
manifest=json.loads((OUT/'N01_基线登记_v1.json').read_text(encoding='utf-8'))
prior=json.loads((OUT/'N01_功能覆盖数据_v1.json').read_text(encoding='utf-8'))
before=db.load_model(prod)
loc_to_id={before.index_label(n):n.id for n in before.nodes}
ids={d['key']:loc_to_id[d['new_location']] for d in prior}
store.DB_FILE=prod;store.DATA_DIR=OUT;store.BACKUP_DIR=OUT;store.EXPORT_DIR=OUT
class Quiet(server.Handler):
    def log_message(self,*args):pass
http=server.ThreadingHTTPServer(('127.0.0.1',0),Quiet)
thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
operations=[]
def api(path,body=None):
    req=urllib.request.Request(f'http://127.0.0.1:{http.server_port}{path}',data=json.dumps(body,ensure_ascii=False).encode() if body else None,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as response:r=json.loads(response.read())
    assert r['ok'];return r
def op(kind,args):
    r=api('/api/op',{'op':kind,'args':args});operations.append({'op':kind,'args':args});return r
def persist(name,value):
    (OUT/name).write_text(value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def sources_text(items):
    return '<br>'.join('`'+SOURCES[x.split(':',1)[0]]+'` §'+x.split(':',1)[1] for x in items)
try:
    sections={s.title:s.id for s in before.sections}
    for r in extra:
        if r['route'] not in sections:
            sections[r['route']]=op('insert_section',{'title':r['route'],'level':1})['section_id']
        assert not any(n.summary==r['summary'] for n in before.nodes),'禁止重复执行收口补充'
        body=r['body']+'\n待裁定：'+'；'.join(r['blockers'])+'。受影响验收暂不通过。'
        ids[r['key']]=op('insert_node',{'section_id':sections[r['route']],'summary':r['summary'],'body':body})['node_id']
    current=M.model_from_dict(api('/api/state')['model'])
    for r in extra:
        refs=[]
        for key in r['refs']:
            target=current.node(ids[key]);sec=current.section(target.section_id)
            refs.append({'raw':sec.title+str(target.number),'target_id':target.id})
        op('update_node',{'node_id':ids[r['key']],'refs':refs,'reparse':False})
    # 最小验收单元收口：限时移除、免疫、解除和一次性结束分开。
    narrowed={
      'F04':'限时效果到达来源配置的持续时间时移除，详情更新有效状态；具体时间单位与到期触发点待 G07/G09。',
      'F07':'战斗结束后保留角色生命、伤势以及配置为战斗外有效的效果；各类结束原因的收尾适用性待 G10。保存到外部存档延期。',
    }
    for key,body in narrowed.items():
        op('update_node',{'node_id':ids[key],'body':body+'\n待裁定：'+('G07 G09' if key=='F04' else 'G10')+'。受影响验收暂不通过。','reparse':False})
    # 正式结束判定依赖已构建的各目标类型。
    old=current.node(ids['R06'])
    refs=[{'raw':r.raw,'target_id':r.target_id} for r in old.refs]
    for key in ['R09','R10','R11','R12','R13']:
        target=current.node(ids[key]);sec=current.section(target.section_id)
        refs.append({'raw':sec.title+str(target.number),'target_id':target.id})
    op('update_node',{'node_id':old.id,'refs':refs,'reparse':False})
    current=M.model_from_dict(api('/api/state')['model'])
    validation=M.validate(current)
    assert validation['stats']['errors']==0,validation['issues']
    exported=api('/api/export',{'path':'Output/N01-战斗玩家功能补图/N01_战斗玩家功能新图_v2.md'})
    assert exported['markdown']==M.to_markdown(current)
    allrows=ROWS+extra
    parents=defaultdict(list);children=defaultdict(list)
    edges,_=M.build_edges(current)
    for e in edges:parents[e['to']].append(e['from']);children[e['from']].append(e['to'])
    degrees={n.id:len(parents[n.id]) for n in current.nodes};queue=deque(nid for nid,d in degrees.items() if not d);order=[]
    while queue:
        nid=queue.popleft();order.append(nid)
        for nxt in children[nid]:
            degrees[nxt]-=1
            if not degrees[nxt]:queue.append(nxt)
    assert len(order)==len(current.nodes)
    effective={ids[r['key']]:set(r['blockers']) for r in allrows}
    for nid in order:
        for nxt in children[nid]:effective[nxt].update(effective[nid])
    base=db.load_model(backup);details=[]
    for index,r in enumerate(allrows,1):
        node=current.node(ids[r['key']]);d={**r,'body':node.body,'feature_id':f'N01-F{index:03}',
          'new_location':current.index_label(node),'original_locations':[base.index_label(base.node(x)) for x in r['original']],
          'effective_blockers':sorted(effective[node.id])}
        details.append(d)
    persist('N01_功能覆盖数据_v2.json',details)
    fields=['feature_id','summary','prior','original_locations','new_location','sources','blockers','effective_blockers']
    with (OUT/'N01_功能覆盖对照_v2.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for d in details:w.writerow({k:'；'.join(d[k]) if isinstance(d[k],list) else d[k] for k in fields})
    doc=['# N01 最终功能覆盖对照','',f'2026-10-14。最终新图：{len(current.sections)} 路线、{len(current.nodes)} 条。原图判断、资料核对、29 条变更、范围外条款和差异详见 `N01_功能覆盖与变更对照_v1.md`；本表包含收口补充并为最终图的功能映射。',
         '',f'直接未决 {sum(bool(r["blockers"]) for r in allrows)} 项，包含依赖传播共 {sum(bool(v) for v in effective.values())} 项受影响；仅计图上规则承接，不等于功能实现或验收通过。',
         '', '| 功能 ID / 目标 | 依据 | 原图状态与落点 | 最终新图落点 | 直接 / 传递未决 |','| --- | --- | --- | --- | --- |']
    for d in details:doc.append(f'| {d["feature_id"]} · {d["summary"]} | {sources_text(d["sources"])} | {d["prior"]}：'+('、'.join(d['original_locations']) or '—')+f' | {d["new_location"]} | '+('、'.join(d['blockers']) or '—')+' / '+('、'.join(d['effective_blockers']) or '—')+' |')
    doc+=['','收口拆分：限时移除、免疫终止、解除条件与投掷一次性结束分别验收；目标系统补充全歼、精英、道具破坏、隐藏目标与无轮次上限，各节点正文直接列触发与观察结果。','',
          '未决仍为 G01—G14。新增目标类型也受 G01/G09 约束，新增效果终止受 G07/G08/G09 约束。未决库的影响清单是首轮提问时取样；最终影响以本表和 v2 JSON 为准。','']
    persist('N01_功能覆盖与变更对照_v2.md','\n'.join(doc))
    # 原生 Markdown 导出不含 ObjectItem.path；附全量对象清单补齐展示。
    objects=['# N01 对象完整说明导出','',
             '原工具 Markdown 导出保存正文、依赖与对象名称/备注，但不序列化对象的实现路径字段。本附表与新图库共同保存这些原图技术说明，不改变工具源码。SQLite 库与完整模型 JSON 保留全部字段。','',
             '| 图上落点 | 对象 | 说明/备注 | 实现路径字段 |','| --- | --- | --- | --- |']
    for n in current.nodes:
        for o in n.objects:objects.append('| '+current.index_label(n)+' | '+o.name+' | '+(o.note or '—').replace('\n','<br>').replace('|','\|')+' | '+(o.path or '—').replace('\n','<br>').replace('|','\|')+' |')
    persist('N01_对象完整说明导出_v1.md','\n'.join(objects)+'\n')
    assert sha(ROOT/'Tool/项目网络图/数据/项目网络图.sqlite')==manifest['source_file_sha256']
    assert sha(backup)==manifest['backup_file_sha256']
    assert db.model_payload(db.load_model(prod))==db.model_payload(current)
    for n in base.nodes:
        assert vars(current.node(n.id))['objects']==n.objects
    verify={'stats':validation['stats'],'database':db.verify(prod),'original_file_unchanged':True,'backup_file_unchanged':True,
            'model_reload_equal':True,'export_matches_native_model':True,'object_path_export_supplement':'N01_对象完整说明导出_v1.md',
            'base_model_sha256':manifest['model_sha256'],'new_file_sha256':sha(prod),'markdown_sha256':sha(OUT/'N01_战斗玩家功能新图_v2.md'),
            'topological_order':[current.index_label(current.node(nid)) for nid in order],
            'feature_count':len(details),'direct_blocked_count':sum(bool(r['blockers']) for r in allrows),'effective_blocked_count':sum(bool(v) for v in effective.values()),
            'upstream_gap_count':len(GAPS),'full_coverage_achieved':False,'N02_baseline_comparison':'未读取产物，待外部按登记模型摘要比对'}
    persist('N01_核验结果_v2.json',verify);persist('N01_模型校验_v2.json',validation)
    persist('N01_新图完整模型_v2.json',db.model_payload(current));persist('N01_收口API操作记录_v1.json',operations)
    print(json.dumps({k:v for k,v in verify.items() if k not in ('topological_order','database')},ensure_ascii=False,indent=2))
finally:
    http.shutdown();http.server_close();thread.join(timeout=5)
