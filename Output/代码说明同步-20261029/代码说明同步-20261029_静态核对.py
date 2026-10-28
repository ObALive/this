from pathlib import Path
import re,json,subprocess,hashlib,xml.etree.ElementTree as ET
ROOT=Path(r'D:\myspace\Git\this')
PROJECT=Path(r'D:\myspace\Git\mygame')
DOCS=ROOT/'代码说明文档'
OUT=ROOT/'Output'/'代码说明同步-20261029'
BASE=json.loads((OUT/'代码说明同步-20261029_核对基线.json').read_text(encoding='utf-8'))
issues=[]; links=[]; checks=[]
def check(name,ok,evidence):
    checks.append({'check':name,'passed':bool(ok),'evidence':evidence})
    if not ok: issues.append(name)
def read(rel): return (PROJECT/rel).read_text(encoding='utf-8-sig')
def blocks(rel):
    text=read(rel)
    return {m.group(1):m.group(2) for m in re.finditer(r'^--- !u!\d+ &(\d+)\r?\n(.*?)(?=^--- !u!|\Z)',text,re.M|re.S)}
def guid(rel): return re.search(r'^guid: (\w+)',read(rel+'.meta'),re.M).group(1)
files=sorted(DOCS.glob('*.md'))
for p in files:
    text=p.read_text(encoding='utf-8')
    check(p.name+' 编码与代码围栏','\ufffd' not in text and text.count('```')%2==0,'UTF-8; paired fences')
    fields=['核对基线','状态','更新日期']+([] if p.name=='README.md' else ['解释范围','源码依据','关联设计'])
    check(p.name+' 元信息',all('| '+f+' |' in text for f in fields) and BASE['projectHead'] in text and '2026-10-29' in text,fields)
    for target in re.findall(r'\[[^\]]+\]\((<[^>]+>|[^)]+)\)',text):
        target=target.strip('<>'); part=target.split('#',1)[0]
        if not part or re.match(r'https?://',part): continue
        dest=Path(part) if re.match(r'^[A-Za-z]:/',part) else p.parent/part
        ok=dest.exists(); links.append({'document':p.name,'target':target,'exists':ok})
        if not ok: issues.append(p.name+': broken link '+target)
    forbidden=['不再','不是','原先','原本','此前','旧版','本轮','本次','改为','迁移','收录','补上','版本沿革','ActionTargetComponent','ActionRecoveryComponent','MovementEffectComponent','WaitEffectComponent','MetaActionInstance.TryExecute','IMovementCapability.TryMove']
    found=[t for t in forbidden if t in text]
    check(p.name+' 沿革与接口查漏',not found,found)
# XML is generated without a namespace; local tag names also support namespaced project files.
xml=ET.parse(PROJECT/'Assembly-CSharp.csproj')
compile_paths={e.attrib['Include'].replace('\\','/') for e in xml.iter() if e.tag.rsplit('}',1)[-1]=='Compile'}
source_paths=sorted({x['target'].replace('D:/myspace/Git/mygame/','') for x in links if x['target'].endswith('.cs')})
sources=[]; declarations={}
for rel in source_paths:
    text=read(rel)
    decl=re.findall(r'\b(?:class|enum|interface|struct)\s+(\w+)(?:\s*<[^>{}]+>)?\s*(?::\s*([^\n{]+))?',text)
    sources.append({'file':rel,'inAssemblyCSharp':rel in compile_paths,'namespaces':re.findall(r'(?m)^\s*namespace\s+([^\s{;]+)',text),'declarations':[d[0] for d in decl]})
    for name,bases in decl: declarations[name]={'source':rel,'bases':bases.strip(),'text':text}
check('链接源码 Compile 归属',all(s['inAssemblyCSharp'] for s in sources),[s['file'] for s in sources if not s['inAssemblyCSharp']])
check('链接源码全局命名空间',all(not s['namespaces'] for s in sources),'Assembly-CSharp.csproj + namespace declarations')
for p in files:
    text=p.read_text(encoding='utf-8')
    for base,derived in re.findall(r'^\s*(\w+)\s+<\|--\s+(\w+)\s*$',text,re.M):
        valid=derived in declarations and re.search(r'\b'+base+r'\b',declarations[derived]['bases'])
        check(p.name+' 继承 '+derived+' : '+base,valid,declarations.get(derived,{}).get('bases','missing'))
    for typ,member in set(re.findall(r'\b([A-Z]\w+)\.([A-Za-z]\w+)\b',text)):
        if typ in declarations and member not in {"cs", "asset", "unity", "csproj"}:
            # This is a lexical declaration/source sanity check; manual review establishes ownership.
            valid=re.search(r'\b'+re.escape(member)+r'\b',declarations[typ]['text'])
            check(p.name+' 成员定位 '+typ+'.'+member,valid,declarations[typ]['source'])
scene=blocks('Assets/Scenes/PersistanceScene.unity')
router=next((k for k,v in scene.items() if re.search(r'^  m_Name: ActionRouter$',v,re.M)),None)
check('ActionRouter 根物体',router is not None and 'm_IsActive: 1' in scene.get(router,''),router)
router_components={}
for typ in ['ActionRouterManager','MovementEffectExecutor','WaitEffectExecutor']:
    g=guid('Assets/Script/Battle/'+typ+'.cs')
    hits=[(k,v) for k,v in scene.items() if 'guid: '+g+',' in v]
    ok=len(hits)==1 and 'm_GameObject: {fileID: '+str(router)+'}' in hits[0][1] and 'm_Enabled: 1' in hits[0][1]
    router_components[typ]=hits[0][0] if hits else None
    check('Router 同物体组件 '+typ,ok,{'guid':g,'fileID':router_components[typ]})
controller_guid=guid('Assets/Script/Battle/BattleTimelineController.cs')
controller=next(v for v in scene.values() if 'guid: '+controller_guid+',' in v)
check('BattleTimelineController.actionRouter 引用','actionRouter: {fileID: '+router_components['ActionRouterManager']+'}' in controller,router_components['ActionRouterManager'])
for name,typ,kind,timing in [('MovementAction','MovementPacketBuilderDefinition',0,'MovementTiming'),('WaitAction','WaitPacketBuilderDefinition',1,'WaitTiming')]:
    text=read('Assets/GameData/Battle/'+name+'.asset')
    configured=text.split('  references:',1)[0]
    check(name+' 单构造器配置',len(re.findall(r'^  - rid:',configured,re.M))==1 and 'class: '+typ+',' in text and 'targetKind: '+str(kind) in text and 'guid: '+guid('Assets/GameData/Battle/'+timing+'.asset')+',' in text,typ)
    check(timing+' 后摇 10',bool(re.search(r'^  recovery: 10(?:\.0)?$',read('Assets/GameData/Battle/'+timing+'.asset'),re.M)),timing)
wait_guid=guid('Assets/GameData/Battle/WaitAction.asset')
move_guid=guid('Assets/GameData/Battle/MovementAction.asset')
for rel,maximum,value,attrs in [('Assets/GameData/MetaObjects/Player.asset',100,100,(5,10,1)),('Assets/GameData/Battle/Unit_02_Timeline.asset',150,120,(3,14,1.25)),('Assets/GameData/Battle/Unit_03_Timeline.asset',80,60,(7,8,0.8))]:
    text=read(rel)
    check(rel+' 四槽待机和移动引用',text.count('guid: '+wait_guid+',')==4 and text.count('guid: '+move_guid+',')==1,'four WaitAction references + one MovementAction')
    expected=['meterId: Health','minimum: 0','maximum: '+str(maximum),'initialValue: '+str(value)]
    check(rel+' Health 测试数据',all(x in text for x in expected),expected)
    check(rel+' 属性数据',all(re.search(r'^        '+k+': '+str(v)+r'$',text,re.M) for k,v in zip(['actionPoints','strength','actionSpeed'],attrs)),attrs)
ui=blocks('Assets/Scenes/UI.unity')
panel_guid=guid('Assets/Script/UI/UnitDetailsPanel.cs')
panel=next(v for v in ui.values() if 'guid: '+panel_guid+',' in v)
expected_fields={'details':'1538517151','hint':'166982040','healthSummary':'488543080','moveLabel':'474455404','moveButton':'2050392728','moveBackground':'2050392729'}
check('底部面板字段与本场景对象',all(k+': {fileID: '+v+'}' in panel and v in ui for k,v in expected_fields.items()),expected_fields)
buttons=re.search(r'  skillButtons:\n(.*?)  skillLabels:',panel,re.S).group(1)
labels=re.search(r'  skillLabels:\n(.*)',panel,re.S).group(1)
check('四对技能按钮和标签',re.findall(r'fileID: (\d+)',buttons)==['228922413','1967859605','2036563005','775289352'] and re.findall(r'fileID: (\d+)',labels)==['1875193678','1949239004','58925814','446884971'],'serialized arrays')
check('面板高度与 Canvas 配置',any('m_SizeDelta: {x: 0, y: 236}' in v for v in ui.values()) and any('m_ReferenceResolution: {x: 1280, y: 720}' in v and 'm_MatchWidthOrHeight: 0.5' in v for v in ui.values()) and any('m_SortingOrder: 20' in v for v in ui.values()),'UI.unity serialized values')
font=guid('Assets/GameData/UI/UnitDetails SDF.asset')
check('TMP 字体引用',font=='3e2ea7fb08197d249a0a4dbdff44ac4d' and 'guid: '+font+',' in read('Assets/Scenes/UI.unity'),font)
changed=[rel for rel,digest in BASE['projectFileHashes'].items() if hashlib.sha256((PROJECT/rel).read_bytes()).hexdigest()!=digest]
status=subprocess.check_output(['git','status','--porcelain'],cwd=PROJECT,text=True)
check('工程文件哈希保持',not changed,{'files':len(BASE['projectFileHashes']),'changed':changed})
check('工程 HEAD 保持',subprocess.check_output(['git','rev-parse','HEAD'],cwd=PROJECT,text=True).strip()==BASE['projectHead'],BASE['projectHead'])
check('工程 Git 工作区保持干净',status=='',status)
check('Markdown 文件链接',all(x['exists'] for x in links),{'checked':len(links)})
result={'date':'2026-10-29','documents':len(files),'linksChecked':len(links),'sourceFilesChecked':len(sources),'checks':checks,'issues':issues,'sources':sources,'links':links,'projectHashFiles':len(BASE['projectFileHashes']),'projectGitStatus':status,'validationScope':'源码与静态资产一致性核对；不执行 Unity 编译或播放'}
(OUT/'代码说明同步-20261029_核对结果.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'documents':len(files),'links':len(links),'sources':len(sources),'checks':len(checks),'issues':issues},ensure_ascii=False))
raise SystemExit(1 if issues else 0)
