from pathlib import Path
import hashlib,json,re,sqlite3,subprocess,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
ENGINE=Path('D:/myspace/Git/mygame'); LIB=ROOT/'代码说明文档'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def git(p,*args): return subprocess.check_output(['git','-C',str(p),*args]).decode('utf-8',errors='replace').strip()
def write(name,value):
    with (OUT/name).open('x',encoding='utf-8') as f: json.dump(value,f,ensure_ascii=False,indent=2)
old=json.loads((ROOT/'Output/CO06-结构重写/CO06-结构重写_源码结构基线_v1.json').read_text(encoding='utf-8'))
sources=[]
for item in old['sources']+[{'path':'Assets/Script/UI/UnitDetailsPanel.cs','document':'70_UnitDetailsPanel与移动选择界面代码设计案.md'}]:
    p=ENGINE/item['path']; content=p.read_text(encoding='utf-8-sig'); types=[]
    for line,text in enumerate(content.splitlines(),1):
        m=re.match(r'\s*(?:public|private|internal|protected)\s+(?:(?:abstract|sealed|readonly|static|partial)\s+)*(class|interface|struct|enum)\s+(\w+)(?:\s*:\s*([^\{]+))?',text)
        if m: types.append({'kind':m[1],'type':m[2],'bases':(m[3] or '').strip(),'line':line})
    sources.append({'path':item['path'],'document':item['document'],'sha256':sha(p),'changed':item.get('sha256')!=sha(p),'types':types})
projects={}
for name in ('Assembly-CSharp','Assembly-CSharp-Editor','Assembly-CSharp-firstpass'):
    p=ENGINE/(name+'.csproj'); tree=ET.parse(p)
    def find(tag): return [e for e in tree.iter() if e.tag.rsplit('}',1)[-1]==tag]
    projects[name]={'sha256':sha(p),'assembly_name':[e.text for e in find('AssemblyName')],
      'compile':[e.attrib['Include'].replace('\\','/') for e in find('Compile')],
      'projects':[e.attrib['Include'] for e in find('ProjectReference')],'references':[e.attrib['Include'] for e in find('Reference')]}
protected={}
for directory in ('Rules','Code_Design','系统设计文档','架构设计文档','Tool/项目网络图'):
    for p in (ROOT/directory).rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts: protected[p.relative_to(ROOT).as_posix()]=sha(p)
assets=[p for p in (ENGINE/'Assets/GameData').rglob('*') if p.is_file()]+list((ENGINE/'Assets/Scenes').glob('*.unity'))
assets += [ENGINE/'ProjectSettings'/n for n in ('EditorBuildSettings.asset','TagManager.asset','ProjectVersion.txt')]
data=ROOT/'Tool/项目网络图/数据'; database=data/json.loads((data/'数据管理.json').read_text(encoding='utf-8'))['active_id']
conn=sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True); conn.row_factory=sqlite3.Row
nodes=[dict(r) for r in conn.execute("select n.*,s.title as route from nodes n join sections s on s.id=n.section_id where n.status='已实现'")];conn.close()
scene=(ENGINE/'Assets/Scenes/UI.unity').read_text(encoding='utf-8'); blocks=dict(re.findall(r'^--- !u!\d+ &(\d+)\n(.*?)(?=^--- |\Z)',scene,re.M|re.S))
ui_block=next(v for v in blocks.values() if 'd9ac9dd00d5e5b54c8b8495a6f8f5aa5' in v)
fields=dict(re.findall(r'^  (details|hint|moveLabel|moveButton|moveBackground): \{fileID: (\d+)\}',ui_block,re.M))
binding={field:{'fileID':i,'exists':i in blocks,'font':re.findall(r'm_fontAsset: .*guid: (\w+)',blocks.get(i,''))} for field,i in fields.items()}
for p in LIB.glob('*.md'): subprocess.run(['git','cat-file','-e','HEAD:'+p.relative_to(ROOT).as_posix()],cwd=ROOT,check=True)
result={'date':'2026-10-24','workspace_head':git(ROOT,'rev-parse','HEAD'),'source_head':git(ENGINE,'rev-parse','HEAD'),
 'source_status':git(ENGINE,'status','--porcelain'),'delta':git(ENGINE,'diff','--name-status','c744a32','HEAD'),
 'sources':sources,'projects':projects,'assets':{p.relative_to(ENGINE).as_posix():sha(p) for p in assets},
 'protected':protected,'implemented_nodes':nodes,'ui_bindings':binding,'ui_panel_block':ui_block}
write('CO06-工程更新3911fe3_基线_v1.json',result)
print(json.dumps({'scripts':len(sources),'types':sum(len(s['types']) for s in sources),'changed_scripts':[s['path'] for s in sources if s['changed']],'all_in_assembly':all(s['path'] in projects['Assembly-CSharp']['compile'] for s in sources),'ui_bindings':binding},ensure_ascii=False))
