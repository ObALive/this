from pathlib import Path
import hashlib,json,re,sqlite3,subprocess
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
ENGINE=Path('D:/myspace/Git/mygame'); LIB=ROOT/'代码说明文档'
b=json.loads((OUT/'CO06-结构重写_源码结构基线_v1.json').read_text(encoding='utf-8'))
a=json.loads((OUT/'CO06-结构重写_程序集归属证据_v1.json').read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
errors=[]; types=[]; links=[]
for s in b['sources']:
    p=LIB/s['document']; content=p.read_text(encoding='utf-8')
    if sha(ENGINE/s['path'])!=s['sha256']: errors.append('源码基线变化:'+s['path'])
    if not a['scope_in_Assembly-CSharp'].get(s['path']): errors.append('程序集成员缺失:'+s['path'])
    for t in s['types']:
        present=t['type'] in content
        types.append({'source':s['path'],'type':t['type'],'bases':t['bases'],'line':t['line'],'document':s['document'],'present':present})
        if not present: errors.append('类型未解释:'+t['type'])
for p in LIB.glob('*.md'):
    c=p.read_text(encoding='utf-8')
    for target in re.findall(r'\]\(([^)]+)\)',c):
        target=unquote(target.split('#')[0]); q=Path(target) if re.match(r'^[A-Z]:[/\\]',target) else p.parent/target
        exists=q.exists(); links.append({'document':p.name,'target':target,'exists':exists})
        if not exists: errors.append('链接失效:'+target)
    if re.search(r'Output/|Report/|Task/|Tool/|Code_Design/|NR-\d',c): errors.append('过程引用越界:'+p.name)
    if p.name!='README.md':
        for text in ('解释范围','源码依据','核对基线','状态','更新日期','Assembly-CSharp'):
            if text not in c: errors.append('元信息缺失:'+p.name+':'+text)
    if any(line.rstrip()!=line for line in c.splitlines()): errors.append('行尾空格:'+p.name)
protected_changed=[p for p,h in b['protected'].items() if sha(ROOT/p)!=h]
assets_changed=[p for p,h in b['assets'].items() if sha(ENGINE/p)!=h]
projects_changed=[n for n in ('Assembly-CSharp','Assembly-CSharp-Editor','Assembly-CSharp-firstpass') if sha(ENGINE/(n+'.csproj'))!=a[n]['sha256']]
if protected_changed or assets_changed or projects_changed: errors.append('只读依据变化')
mapping={('角色移动',0):'20_对象组件与场景承载类型代码设计案.md',('角色属性',1):'20_对象组件与场景承载类型代码设计案.md',
 ('角色技能',1):'30_MetaAction派生类型与动作组件代码设计案.md',('逻辑',1):'50_TimeLineManager与战斗装配类型代码设计案.md',
 ('角色移动',1):'60_地图与移动适配类型代码设计案.md',('角色移动',2):'60_地图与移动适配类型代码设计案.md'}
nodes=[]
for n in b['database']['nodes']:
    document=mapping.get((n['route'],n['number']))
    nodes.append({'route':n['route'],'number':n['number'],'summary':n['summary'],'main_document':document})
    if not document or not (LIB/document).exists(): errors.append('节点遗漏:'+str(n['id']))
conn=sqlite3.connect(Path(b['database']['path']).resolve().as_uri()+'?mode=ro',uri=True)
current=set(conn.execute("select s.title,n.number from nodes n join sections s on s.id=n.section_id where status='已实现'"));conn.close()
if current!=set(mapping): errors.append('范围改变')
expected={'README.md','00_程序集与类型关系总览代码设计案.md',*{s['document'] for s in b['sources']}}
if set(p.name for p in LIB.glob('*.md'))!=expected: errors.append('库文件集合不符')
diff=subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True)
if diff.returncode: errors.append('git diff --check未通过')
result={'date':'2026-10-24','assembly_evidence':'CO06-结构重写_程序集归属证据_v1.json',
 'documents':sorted(expected),'types':types,'nodes':nodes,'links':links,'protected_changed':protected_changed,
 'assets_changed':assets_changed,'projects_changed':projects_changed,'errors':errors,
 'manual_review':'逐篇对照声明和调用核查继承、组合、配置引用、方法归属与生命周期统一入口；符号出现检查不替代语义验收。',
 'not_run':['工程编译','Unity自动测试','游戏播放','播放器构建']}
with (OUT/'CO06-结构重写_验收结果_v1.json').open('x',encoding='utf-8') as stream: json.dump(result,stream,ensure_ascii=False,indent=2)
print(json.dumps({'documents':len(expected),'types':len(types),'source_files':len(b['sources']),'nodes':len(nodes),'links':len(links),'errors':errors},ensure_ascii=False))
raise SystemExit(bool(errors))
