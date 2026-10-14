"""按用户规则清理显式依赖；保留自动链边，并逐对核对可达性。"""
from pathlib import Path
import sys,json,hashlib,argparse,threading,urllib.request,subprocess
from collections import defaultdict,deque
from datetime import datetime

sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/'Tool/项目网络图'))
import db,model as M,store,server
LIB=OUT/'N01_战斗玩家功能新图_v1.sqlite'
REPORT=ROOT/'Report/N01-战斗玩家功能补图_Report.md'
FILES=[LIB,OUT/'N01_战斗玩家功能新图_v2.md',OUT/'N01_新图完整模型_v2.json',OUT/'N01_功能覆盖数据_v2.json',REPORT]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def persist(name,value):
    (OUT/name).write_text(value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def parents(m):
    result=defaultdict(set)
    for e in M.build_edges(m)[0]:result[e['to']].add(e['from'])
    return result
def closure(m):
    ps=parents(m);result={}
    for node in m.nodes:
        seen=set();queue=list(ps[node.id])
        while queue:
            nid=queue.pop()
            if nid in seen:continue
            seen.add(nid);queue.extend(ps[nid])
        assert node.id not in seen,'依赖环'
        result[node.id]=seen
    return result
def short_path(m,node_id,target,max_depth=3):
    ps=parents(m)
    queue=deque((parent,[node_id,parent]) for parent in ps[node_id] if parent!=target)
    while queue:
        nid,path=queue.popleft()
        if len(path)-1>=max_depth:continue
        for upstream in ps[nid]:
            newpath=path+[upstream]
            if upstream==target:return newpath
            if upstream not in path:queue.append((upstream,newpath))
    return None

before=db.load_model(LIB)
assert not M.validate(before)['stats']['errors']
after=M.model_from_dict(db.model_payload(before))
removed=[]
def label(m,nid):return m.index_label(m.node(nid))
def remove(node,ref,reason,witness):
    removed.append({'node':label(after,node.id),'dependency':label(after,ref.target_id),'raw':ref.raw,'reason':reason,
                    'witness':[label(after,x) for x in witness]})
    node.refs.remove(ref)

# 先完成用户明确的同其他路线取最末项。链式先后顺序取工具的 section_nodes。
rank={n.id:i for s in after.sections for i,n in enumerate(after.section_nodes(s.id))}
for node in after.nodes:
    groups=defaultdict(list)
    for ref in node.refs:
        target=after.node(ref.target_id)
        assert target
        groups[target.section_id].append(ref)
    for sid,refs in groups.items():
        if sid==node.section_id:continue
        latest=max(refs,key=lambda r:rank[r.target_id])
        for ref in refs:
            if ref is not latest:
                remove(node,ref,'同一其他路线只保留最末依赖',[node.id,latest.target_id,ref.target_id])

# 自动递进本身已涵盖同路线早期节点，无需再写显式引用。
for node in after.nodes:
    for ref in list(node.refs):
        target=after.node(ref.target_id)
        if target.section_id==node.section_id and rank[target.id]<rank[node.id]:
            remove(node,ref,'本路线自动递进已包含该上游',[node.id,target.id])

# 用户的上游判据：经另一直接上游，沿依赖再走一或两步能到达候选。
# 只在当前仍保留的图中找替代路径，重复至不存在符合规则的显式引用。
passes=0
while True:
    count=len(removed);passes+=1
    for node in after.nodes:
        for ref in list(node.refs):
            witness=short_path(after,node.id,ref.target_id)
            if witness:remove(node,ref,'直接上游已依赖，或其所依赖节点的直接上游已包含',witness)
    if len(removed)==count:break

old_closure=closure(before);new_closure=closure(after)
assert old_closure==new_closure,'清理改变了构建前置可达关系'
assert all(len({after.node(r.target_id).section_id for r in n.refs})==len(n.refs) for n in after.nodes)
assert not any(short_path(after,n.id,r.target_id) for n in after.nodes for r in n.refs)
assert not M.validate(after)['stats']['errors']
plan={'time':datetime.now().astimezone().isoformat(),'before':M.serialize(before)['stats'],'after':M.serialize(after)['stats'],
      'removed_refs':len(removed),'changed_nodes':sum(n.refs!=after.node(n.id).refs for n in before.nodes),
      'reasons':{reason:sum(x['reason']==reason for x in removed) for reason in dict.fromkeys(x['reason'] for x in removed)},
      'all_ancestor_sets_equal':True,'passes':passes,'removed':removed,'files_to_update':[str(p.relative_to(ROOT)) for p in FILES],
      'before_file_sha256':sha(LIB)}
args=argparse.ArgumentParser();args.add_argument('--apply',action='store_true');opts=args.parse_args()
if not opts.apply:
    persist('N01_依赖清理方案_v1.json',plan)
    print(json.dumps({k:v for k,v in plan.items() if k!='removed'},ensure_ascii=False,indent=2))
    raise SystemExit(0)

# 遵守 NR-02 的改写前 Git 可复原性核验；已有未提交改动仍以当前库为准。
for path in FILES:
    relative=str(path.relative_to(ROOT)).replace('\\','/')
    subprocess.run(['git','cat-file','-e','HEAD:'+relative],cwd=ROOT,check=True,capture_output=True)
head=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,check=True,capture_output=True,text=True).stdout.strip()
origin=ROOT/'Tool/项目网络图/数据/项目网络图.sqlite';backup=OUT/'N01_原图一致性备份_v1.sqlite'
origin_sha=sha(origin);backup_sha=sha(backup)
store.DB_FILE=LIB;store.DATA_DIR=OUT;store.BACKUP_DIR=OUT;store.EXPORT_DIR=OUT
class Quiet(server.Handler):
    def log_message(self,*args):pass
http=server.ThreadingHTTPServer(('127.0.0.1',0),Quiet)
thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
api_log=[]
def api(path,payload):
    req=urllib.request.Request(f'http://127.0.0.1:{http.server_port}{path}',data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as response:result=json.loads(response.read())
    assert result['ok'];return result
try:
    for node in after.nodes:
        if node.refs==before.node(node.id).refs:continue
        payload={'node_id':node.id,'refs':[{'raw':r.raw,'target_id':r.target_id} for r in node.refs],'reparse':False}
        result=api('/api/op',{'op':'update_node','args':payload})
        api_log.append({'node':label(after,node.id),'args':payload,'log':result.get('log',[])})
    exported=api('/api/export',{'path':str((OUT/'N01_战斗玩家功能新图_v2.md').relative_to(ROOT)).replace('\\','/')})
    current=db.load_model(LIB)
    assert closure(current)==old_closure
    for old in before.nodes:
        new=current.node(old.id)
        assert old.body==new.body and old.summary==new.summary and old.objects==new.objects and old.notes==new.notes and old.manual==new.manual
        assert [(r.raw,r.target_id) for r in new.refs]==[(r.raw,r.target_id) for r in after.node(old.id).refs]
    assert exported['markdown']==M.to_markdown(current)
    persist('N01_新图完整模型_v2.json',db.model_payload(current))
    details=json.loads((OUT/'N01_功能覆盖数据_v2.json').read_text(encoding='utf-8'))
    key_by_label={d['new_location']:d['key'] for d in details}
    node_by_label={current.index_label(n):n for n in current.nodes}
    for d in details:
        d['refs']=[key_by_label[label(current,r.target_id)] for r in node_by_label[d['new_location']].refs]
    persist('N01_功能覆盖数据_v2.json',details)
    assert sha(origin)==origin_sha and sha(backup)==backup_sha
    verification={**plan,'after':M.serialize(current)['stats'],'version_basis':head,'database':db.verify(LIB),
                  'port':http.server_port,'new_file_sha256':sha(LIB),'original_file_unchanged':True,'backup_file_unchanged':True,
                  'node_body_summary_objects_notes_manual_unchanged':True,'export_matches_model':True,
                  'same_route_multiple_refs_remaining':0,'local_redundant_refs_remaining':0,
                  'api_operations':api_log,'full_coverage_achieved':False,'upstream_gaps_unchanged':14}
    persist('N01_依赖清理核验_v1.json',verification)
    persist('N01_依赖清理后模型校验_v1.json',M.validate(current))
    report=REPORT.read_text(encoding='utf-8')
    report=report.replace('| 报告版本 | v1 |','| 报告版本 | v2 |')
    report=report.replace('原 29 节点身份、对象技术说明、既有绑定引用和布局保存；','原 29 节点身份、对象技术说明和布局保存；按用户追加规则清理冗余绑定引用；')
    report=report.replace('145 个条目、309 条不同依赖边','145 个条目、'+str(verification['after']['edges'])+' 条不同依赖边')
    marker='## 6 文件变更列表'
    addition=f'''追加执行：用户要求清理冗余依赖。同一其他路线仅保留最末引用，自动递进涵盖的本路线引用删去；经另一直接上游的一或两步依赖涵盖的引用删去。显式引用从 {plan['before']['explicit_edges']} 条减为 {verification['after']['explicit_edges']} 条，删除 {len(removed)} 条，涉及 {plan['changed_nodes']} 个节点；不同依赖边由 {plan['before']['edges']} 减为 {verification['after']['edges']}。清理前后全部 145 个节点的上游可达集合逐项一致，节点正文、编号和对象说明不变。清理前文件已提交 Git，版本依据 `{head}`；结果与删除见 `N01_依赖清理核验_v1.json`、`N01_依赖清理说明_v1.md`。原先核验 JSON 属清理前取样，当前依赖以本次核验与新图库为准；14 项上游未决不受清理影响。\n\n'''
    report=report.replace(marker,addition+marker)
    REPORT.write_text(report,encoding='utf-8')
    lines=['# N01 依赖清理说明','',f"显式依赖 {plan['before']['explicit_edges']} → {verification['after']['explicit_edges']}；删除 {len(removed)} 条，涉及 {plan['changed_nodes']} 个节点。自动递进 {verification['after']['chain_edges']} 条保持，不同依赖边 {plan['before']['edges']} → {verification['after']['edges']}。145 个节点的完整上游可达集合逐项一致。",'',
           '当前可编辑库和最终 Markdown/完整模型已同步；原图与备份未修改，功能正文和技术说明保持。构建前置仍可沿保留依赖追溯，功能映射 JSON 的显式 refs 已同步。','',
           '规则：同一其他路线只保留最末节点；本路线自动递进涵盖的显式引用删除；另一直接上游依赖了该节点，或另一直接上游所依赖节点的直接上游为该节点时，删除重复引用。每次删除都基于当前仍保留的图，清理至没有符合上述规则的重复。','',
           '| 节点 | 删除引用 | 原因 | 替代路径 / 保留引用 |','| --- | --- | --- | --- |']
    for item in removed:lines.append('| '+item['node']+' | '+item['dependency']+' | '+item['reason']+' | '+' → '.join(item['witness'])+' |')
    lines+=['',f'改写前 Git 依据：`{head}`。API 临时服务仅监听 127.0.0.1:{http.server_port}，进程内定向库/导出至 N01 目录，完成后停止；未修改工具源码或持久环境变量。','',
            '未决仍为 14 项；本次只清理网络图书写，未改变规则、配置或完整覆盖状态。此前 309 条边和 210 条显式引用的核验是清理前记录，当前以本次核验为准。','']
    persist('N01_依赖清理说明_v1.md','\n'.join(lines))
    print(json.dumps({k:v for k,v in verification.items() if k not in ('removed','api_operations','database')},ensure_ascii=False,indent=2))
finally:
    http.shutdown();http.server_close();thread.join(timeout=5)
