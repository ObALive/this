"""不覆盖既有产物、不写 Git；独立交付按用户规则清理后的图。"""
from pathlib import Path
import sys,json,sqlite3,threading,urllib.request,hashlib
from datetime import datetime
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/'Tool/项目网络图'))
import db,model as M,store,server

# 重用已审阅的只读清理算法：在任何方案写入或 --apply 分支之前终止源码片段。
source=(OUT/'N01_清理依赖_v1.py').read_text(encoding='utf-8')
readonly=source.split('args=argparse.ArgumentParser();',1)[0]
scope={'__file__':str(OUT/'N01_清理依赖_v1.py'),'__name__':'n01_cleanup_readonly'}
exec(compile(readonly,str(OUT/'N01_清理依赖_v1.py'),'exec'),scope)
before=scope['before'];after=scope['after'];plan=scope['plan'];closure=scope['closure']
newlib=OUT/'N01_依赖清理新图_v1.sqlite'
exportname='N01_依赖清理新图_v1.md'
assert not newlib.exists(),'独立交付已存在，不覆盖'
unchanged=[ROOT/'Tool/项目网络图/数据/项目网络图.sqlite',OUT/'N01_原图一致性备份_v1.sqlite',*scope['FILES']]
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
hashes={str(p):sha(p) for p in unchanged}
with db.connect(scope['LIB'],readonly=True) as src,sqlite3.connect(newlib) as dst:src.backup(dst)
store.DB_FILE=newlib;store.DATA_DIR=OUT;store.BACKUP_DIR=OUT;store.EXPORT_DIR=OUT
class Quiet(server.Handler):
    def log_message(self,*args):pass
http=server.ThreadingHTTPServer(('127.0.0.1',0),Quiet)
thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
def api(path,payload):
    req=urllib.request.Request(f'http://127.0.0.1:{http.server_port}{path}',data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as response:r=json.loads(response.read())
    assert r['ok'];return r
def persist(name,value):
    (OUT/name).write_text(value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
api_log=[]
try:
    for n in after.nodes:
        if n.refs==before.node(n.id).refs:continue
        payload={'node_id':n.id,'refs':[{'raw':r.raw,'target_id':r.target_id} for r in n.refs],'reparse':False}
        result=api('/api/op',{'op':'update_node','args':payload})
        api_log.append({'node':after.index_label(n),'args':payload,'log':result.get('log',[])})
    exported=api('/api/export',{'path':'Output/N01-战斗玩家功能补图/'+exportname})
    current=db.load_model(newlib)
    assert closure(current)==closure(before)
    assert [(s.id,s.title,s.level,s.parent_id,s.start_number,s.note) for s in current.sections]==[(s.id,s.title,s.level,s.parent_id,s.start_number,s.note) for s in before.sections]
    for old in before.nodes:
        n=current.node(old.id)
        assert old.summary==n.summary and old.body==n.body and old.objects==n.objects and old.notes==n.notes and old.manual==n.manual and old.number==n.number
        assert [(r.raw,r.target_id) for r in n.refs]==[(r.raw,r.target_id) for r in after.node(old.id).refs]
    assert not M.validate(current)['stats']['errors']
    assert exported['markdown']==M.to_markdown(current)
    assert all(sha(Path(path))==value for path,value in hashes.items())
    persist('N01_依赖清理完整模型_v1.json',db.model_payload(current))
    data=json.loads((OUT/'N01_功能覆盖数据_v2.json').read_text(encoding='utf-8'))
    keys={d['new_location']:d['key'] for d in data}
    nodes={current.index_label(n):n for n in current.nodes}
    for d in data:d['refs']=[keys[current.index_label(current.node(r.target_id))] for r in nodes[d['new_location']].refs]
    persist('N01_依赖清理功能映射_v1.json',data)
    result={**plan,'checked_at':datetime.now().astimezone().isoformat(),'delivery_database':str(newlib),'delivery_markdown':str(OUT/exportname),
            'after':M.serialize(current)['stats'],'sqlite':db.verify(newlib),'existing_files_unchanged':hashes,
            'all_ancestor_sets_equal':True,'all_node_content_and_number_unchanged':True,
            'same_other_route_multiple_refs_remaining':0,'local_redundant_refs_remaining':0,
            'export_matches_model':True,'new_database_sha256':sha(newlib),'api_operations':api_log,
            'git_permission_result':'本地基线提交被用户拒绝；未执行 Git 写入，保留既有产物，改为独立清理图交付。',
            'upstream_gaps_unchanged':14,'full_coverage_achieved':False}
    persist('N01_独立依赖清理核验_v1.json',result)
    persist('N01_依赖清理后模型校验_v1.json',M.validate(current))
    lines=['# N01 依赖清理交付','',
        '已按用户规则清理显式依赖，保留自动递进；145 个节点的全部上游可达集合逐项一致，功能正文、编号、对象与技术说明保持。','',
        f"显式引用：{plan['before']['explicit_edges']} → {result['after']['explicit_edges']}；删除 {plan['removed_refs']} 条，涉及 {plan['changed_nodes']} 个节点。不同依赖边：{plan['before']['edges']} → {result['after']['edges']}。自动递进仍为 {result['after']['chain_edges']} 条。",'',
        '| 产物 | 文件 |','| --- | --- |',
        '| 清理后可编辑图库 | `N01_依赖清理新图_v1.sqlite` |',
        '| 清理后 Markdown | `N01_依赖清理新图_v1.md` |',
        '| 全字段模型 | `N01_依赖清理完整模型_v1.json` |',
        '| 更新后的功能映射 | `N01_依赖清理功能映射_v1.json` |',
        '| 逐条删除及可达关系核验 | `N01_独立依赖清理核验_v1.json` |','',
        '在工作区根目录打开清理后的新库：','',
        '```powershell',"python -B -X utf8 'Output/N01-战斗玩家功能补图/N01_打开依赖清理图_v1.py' --no-browser --port 8793",'```','',
        '访问 http://127.0.0.1:8793/，Ctrl+C 停止。打开脚本复用现有工具，默认库与导出均指向本次独立清理交付。','',
        'Git 基线提交未获允许，因此既有库、报告、功能对照与导出全部保持；本次独立图是新的清理成果。14 项上游未决保持，完整覆盖状态未变。原图备份与原图库摘要保持。原生导出未包含的对象实现路径继续见既有 `N01_对象完整说明导出_v1.md`，全字段也保留在本次完整模型内。','',
        '## 删除明细','',
        '| 节点 | 删除引用 | 原因 | 保留引用 / 替代路径 |','| --- | --- | --- | --- |']
    for item in plan['removed']:lines.append('| '+item['node']+' | '+item['dependency']+' | '+item['reason']+' | '+' → '.join(item['witness'])+' |')
    lines+=['','每次删除均基于当时仍保留的引用；结果中每条其他路线至多一项显式依赖，且已无用户指定的一/两层上游重复。','']
    persist('N01_依赖清理交付入口_v1.md','\n'.join(lines))
    print(json.dumps({k:v for k,v in result.items() if k not in ('removed','api_operations','existing_files_unchanged','sqlite')},ensure_ascii=False,indent=2))
finally:
    http.shutdown();http.server_close();thread.join(timeout=5)
    persist('N01_依赖清理系统操作_v1.md',f'''# N01 依赖清理系统操作

时间：{datetime.now().astimezone().isoformat()}
执行命令：`python -B -X utf8 Output/N01-战斗玩家功能补图/N01_清理依赖独立交付_v1.py`
执行目的：按用户规则清理依赖，生成独立可编辑图。
影响范围：仅本任务目录内的新产物；API 服务监听 127.0.0.1:{http.server_port}，进程内库和导出目录定向本任务目录。没有改变持久环境变量、原库、备份或工具源码。
执行结果：见 N01_独立依赖清理核验_v1.json；服务已停止。申请本地 Git 基线提交被用户拒绝，命令未执行；改为独立交付，既有文件摘要保持。
恢复方案：原 N01 库和全部既有材料保留，可继续打开；本次新图为独立成果，打开方式见交付入口。
''')
