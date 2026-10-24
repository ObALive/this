from pathlib import Path
import hashlib, json, re, sqlite3, subprocess, xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
ENGINE=Path('D:/myspace/Git/mygame')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def git(p,*args): return subprocess.check_output(['git','-C',str(p),*args]).decode('utf-8',errors='replace').strip()
groups={
 '10_MetaObject类型与组件底座代码设计案.md':['MetaObjects/MetaObjectDefinition.cs','MetaObjects/MetaObjectInstance.cs','MetaObjects/MetaObjectComponentDefinition.cs','MetaObjects/MetaObjectComponent.cs'],
 '20_对象组件与场景承载类型代码设计案.md':['MetaObjects/MetaObjectPreset.cs','MetaObjects/SceneCoordinateComponent.cs','MetaObjects/SceneTextureComponent.cs','MetaObjects/MovementFacingComponent.cs','MetaObjects/AttributeComponent.cs','MetaObjects/CellChanged.cs','MetaObjects/MovementCompleted.cs'],
 '30_MetaAction派生类型与动作组件代码设计案.md':['Battle/MetaActionDefinition.cs','Battle/MetaActionInstance.cs','Battle/MetaActionComponents.cs','MetaObjects/MovementActionComponent.cs'],
 '40_MetaActionLifecycle统一执行入口代码设计案.md':['Battle/MetaActionLifecycle.cs'],
 '50_TimeLineManager与战斗装配类型代码设计案.md':['Battle/TimeLineManager.cs','Battle/BattleTimelineController.cs','Battle/BattleTimelineConfiguration.cs','Battle/BattleBehaviorDefinition.cs','GameManager.cs','Debug/DebugPanel.cs'],
 '60_地图与移动适配类型代码设计案.md':['TilemapManager.cs','Player/GridClickInput.cs','Player/CharacterMovementController.cs','Player/MovementRange.cs','Player/MovementRangeOverlay.cs']}
projects={}
for name in ('Assembly-CSharp','Assembly-CSharp-Editor','Assembly-CSharp-firstpass'):
    p=ENGINE/(name+'.csproj'); tree=ET.parse(p); namespace={'m':'http://schemas.microsoft.com/developer/msbuild/2003'}
    def find(tag): return tree.findall('.//m:'+tag,namespace)
    projects[name]={'path':p.name,'sha256':sha(p),'assembly_name':[e.text for e in find('AssemblyName')],
      'compile':[e.attrib['Include'].replace('\\','/') for e in find('Compile')],
      'projects':[e.attrib['Include'] for e in find('ProjectReference')],
      'references':[e.attrib['Include'] for e in find('Reference')]}
sources=[]
for document,files in groups.items():
    for relative in files:
        p=ENGINE/'Assets/Script'/relative; content=p.read_text(encoding='utf-8-sig')
        declarations=[]
        for line,text in enumerate(content.splitlines(),1):
            match=re.match(r'\s*(?:public|private|internal|protected)\s+(?:(?:abstract|sealed|readonly|static|partial)\s+)*(class|interface|struct|enum)\s+(\w+)(?:\s*:\s*([^\{]+))?',text)
            if match: declarations.append({'kind':match[1],'type':match[2],'bases':(match[3] or '').strip(),'line':line})
        path=p.relative_to(ENGINE).as_posix()
        sources.append({'path':path,'sha256':sha(p),'document':document,'namespace':re.findall(r'^namespace\s+([^;{]+)',content,re.M),'types':declarations,'in_assembly_csharp':path in projects['Assembly-CSharp']['compile']})
settings=ROOT/'Tool/项目网络图/数据/数据管理.json'
database=settings.parent/json.loads(settings.read_text(encoding='utf-8'))['active_id']
conn=sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True); conn.row_factory=sqlite3.Row
nodes=[dict(r) for r in conn.execute("select n.*,s.title as route from nodes n join sections s on s.id=n.section_id where n.status='已实现' order by n.seq")]
for n in nodes:
    for table in ('node_refs','node_objects','node_notes'):
        n[table]=[dict(r) for r in conn.execute(f'select * from {table} where node_id=? order by seq',(n['id'],))]
conn.close()
protected={}
for directory in ('Rules','Code_Design','系统设计文档','架构设计文档','Tool/项目网络图'):
    for p in (ROOT/directory).rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts: protected[p.relative_to(ROOT).as_posix()]=sha(p)
assets=[p for p in (ENGINE/'Assets/GameData').rglob('*') if p.is_file()]
assets+=list((ENGINE/'Assets/Scenes').glob('*.unity'))
assets += [ENGINE/'ProjectSettings'/n for n in ('EditorBuildSettings.asset','TagManager.asset','ProjectVersion.txt')]
assets += [ENGINE/'Assets/M Studio/Art/Characters/Player/Body/QinRuofu/asfzxfzxd_0.prefab']
result={'date':'2026-10-24','workspace_head':git(ROOT,'rev-parse','HEAD'),'workspace_status':git(ROOT,'status','--porcelain'),
 'source_head':git(ENGINE,'rev-parse','HEAD'),'source_status':git(ENGINE,'status','--porcelain'),'projects':projects,
 'assets_asmdefs':[p.relative_to(ENGINE).as_posix() for p in (ENGINE/'Assets').rglob('*.asmdef')],
 'sources':sources,'assets':{p.relative_to(ENGINE).as_posix():sha(p) for p in assets},
 'database':{'path':str(database),'sha256':sha(database),'nodes':nodes},'protected':protected,
 'replaced_documents':git(ROOT,'ls-files','--','代码说明文档')}
with (OUT/'CO06-结构重写_源码结构基线_v1.json').open('x',encoding='utf-8') as stream: json.dump(result,stream,ensure_ascii=False,indent=2)
print(json.dumps({'sources':len(sources),'types':sum(len(s['types']) for s in sources),'all_in_assembly':all(s['in_assembly_csharp'] for s in sources),'assemblies':{k:v['assembly_name'] for k,v in projects.items()},'project_refs':{k:v['projects'] for k,v in projects.items()}},ensure_ascii=False))
