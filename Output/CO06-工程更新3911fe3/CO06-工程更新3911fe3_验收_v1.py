from pathlib import Path
import hashlib,json,re,subprocess
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
ENGINE=Path('D:/myspace/Git/mygame'); LIB=ROOT/'代码说明文档'
b=json.loads((OUT/'CO06-工程更新3911fe3_基线_v1.json').read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
errors=[]; types=[]; links=[]
for s in b['sources']:
    if sha(ENGINE/s['path'])!=s['sha256']: errors.append('源码变化:'+s['path'])
    c=(LIB/s['document']).read_text(encoding='utf-8')
    if s['path'] not in b['projects']['Assembly-CSharp']['compile']: errors.append('程序集归属不符:'+s['path'])
    for t in s['types']:
        types.append({'type':t['type'],'source':s['path'],'document':s['document'],'present':t['type'] in c})
        if t['type'] not in c: errors.append('类型缺失:'+t['type'])
for p in LIB.glob('*.md'):
    content=p.read_text(encoding='utf-8')
    if b['source_head'] not in content: errors.append('基线缺失:'+p.name)
    if 'c744a32' in content or '27 份脚本' in content or '59 个' in content: errors.append('过期说明:'+p.name)
    if re.search(r'Output/|Report/|Task/|Tool/|Code_Design/|NR-\d',content): errors.append('越界引用:'+p.name)
    for target in re.findall(r'\]\(([^)]+)\)',content):
        target=unquote(target.split('#')[0].strip('<>')); q=Path(target) if re.match(r'^[A-Z]:[/\\]',target) else p.parent/target
        links.append({'document':p.name,'target':target,'exists':q.exists()})
        if not q.exists(): errors.append('失效链接:'+target)
    if any(line.rstrip()!=line for line in content.splitlines()): errors.append('尾空格:'+p.name)
changed={category:[p for p,h in b[category].items() if sha((ROOT if category=='protected' else ENGINE)/p)!=h] for category in ('protected','assets')}
if any(changed.values()): errors.append('只读资料变化')
for name,project in b['projects'].items():
    if sha(ENGINE/(name+'.csproj'))!=project['sha256']: errors.append('工程配置变化:'+name)
if len(b['ui_bindings'])!=5 or not all(x['exists'] for x in b['ui_bindings'].values()): errors.append('面板引用缺失')
font_meta=(ENGINE/'Assets/GameData/UI/UnitDetails SDF.asset.meta').read_text(encoding='utf-8')
font=re.search(r'^guid: (\w+)',font_meta,re.M)[1]
if any(x['font']!=[font] for name,x in b['ui_bindings'].items() if name in ('details','hint','moveLabel')): errors.append('字体引用不符')
checks={
 '普通鼠标须先选择':'public bool CanAcceptPlayerInput => IsMovementSelected;' in (ENGINE/'Assets/Script/Player/CharacterMovementController.cs').read_text(encoding='utf-8'),
 '右键优先':'if (Input.GetMouseButtonDown(1)) { ProcessCancel(); return; }' in (ENGINE/'Assets/Script/Player/GridClickInput.cs').read_text(encoding='utf-8'),
 '范围不再逐帧主动刷新':'private void LateUpdate()' not in (ENGINE/'Assets/Script/Player/MovementRange.cs').read_text(encoding='utf-8'),
 '显示重绘版本复位':'renderedVersion = -1;' in (ENGINE/'Assets/Script/Player/MovementRangeOverlay.cs').read_text(encoding='utf-8'),
 '按钮语义只选择':'.TryMoveToCell(' not in (ENGINE/'Assets/Script/UI/UnitDetailsPanel.cs').read_text(encoding='utf-8')}
if not all(checks.values()): errors.append('关键行为与文档不符')
diff=subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True)
if diff.returncode: errors.append('diff检查失败')
result={'date':'2026-10-24','source_head':b['source_head'],'documents':sorted(p.name for p in LIB.glob('*.md')),
 'types':types,'links':links,'checks':checks,'changed_readonly':changed,'ui_font_guid':font,'errors':errors,
 'range':'原六项节点继续覆盖；UI与协作变化根据用户跟进工程更新的明确授权纳入，未回写网络图状态',
 'not_run':['Unity编译','工程测试/UnitDetailsVerification','游戏播放','播放器构建']}
with (OUT/'CO06-工程更新3911fe3_验收结果_v1.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps({'documents':len(result['documents']),'types':len(types),'links':len(links),'errors':errors},ensure_ascii=False))
raise SystemExit(bool(errors))
