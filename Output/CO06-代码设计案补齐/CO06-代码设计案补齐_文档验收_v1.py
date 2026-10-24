"""文档与证据静态核查；不执行 Unity，也不修改只读资料。"""
from pathlib import Path
import hashlib, json, re, sqlite3, subprocess
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
ENGINE = Path('D:/myspace/Git/mygame')
LIB = ROOT/'代码说明文档'
baseline = json.loads((OUT/'CO06-代码设计案补齐_执行基线_v1.json').read_text(encoding='utf-8'))
mapping = {
    ('角色移动',0): '10_对象与场景显示代码设计案.md',
    ('角色属性',1): '20_固定属性取值代码设计案.md',
    ('角色技能',1): '30_动作执行与交接代码设计案.md',
    ('角色移动',1): '40_点击移动与范围高亮代码设计案.md',
    ('角色移动',2): '40_点击移动与范围高亮代码设计案.md',
    ('逻辑',1): '50_共享时间轴与行动回排代码设计案.md',
}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
failures=[]
checked_links=[]
for p in LIB.glob('*.md'):
    content=p.read_text(encoding='utf-8')
    for target in re.findall(r'\]\(([^)]+)\)',content):
        target=unquote(target.split('#')[0])
        q=Path(target) if re.match(r'^[A-Z]:[/\\]',target) else p.parent/target
        checked_links.append({'document':p.name,'target':target,'exists':q.exists()})
        if not q.exists(): failures.append('失效链接:'+target)
    if re.search(r'Output/|Report/|Task/|Tool/|Code_Design/|NR-\d|n36|n18|n11|n10',content):
        failures.append('正文含过程或旧库引用:'+p.name)
    for field in ('解释范围','核对基线','状态','更新日期','实现定位'):
        if p.name!='README.md' and field not in content: failures.append('缺少文档项:'+p.name+':'+field)
covered=[]
for n in baseline['database']['implemented']:
    key=(n['route'],n['number'])
    target=mapping.get(key)
    if target is None or not (LIB/target).exists(): failures.append('未覆盖:'+str(key))
    covered.append({'route':key[0],'number':key[1],'summary':n['summary'],'document':target})
changed_protected=[p for p,h in baseline['protected_files'].items() if not (ROOT/p).exists() or sha(ROOT/p)!=h]
changed_source=[p for p,h in baseline['source']['files'].items() if not (ENGINE/p).exists() or sha(ENGINE/p)!=h]
if changed_protected: failures.append('只读资料基线变化')
if changed_source: failures.append('源码资产基线变化')
conn=sqlite3.connect(Path(baseline['database']['path']).resolve().as_uri()+'?mode=ro',uri=True)
current=set(conn.execute("SELECT s.title,n.number FROM nodes n JOIN sections s ON s.id=n.section_id WHERE status='已实现'"))
conn.close()
if current!=set(mapping): failures.append('现行已实现范围改变')

# 仅收集正在解释的工程引用；检查 GUID 实际指向，而不是只比较名称。
wanted={'85a0a22df9b38384c99bf9cbf15bac86','596d9e11bc4d5e044a15e5d0cfd21dc9',
 '788de14946752004887de6beac1456fd','96734cc7bf4ed9a49b0ae90b297ac3ba',
 'e14b245e45ba9fe48bd48741aef7ea26','cb046c5fa066b3943879537c2f3f6a5f',
 '998a365e0b6889f4bbbaf92a4781d90e','3935da40321e1734dae35f496e8bb526',
 '5cabb2fdfe008324984abcefaaf485c8','a803a687c9f0927489ebbe02a80597c1'}
resolved={}
for p in (ENGINE/'Assets').rglob('*.meta'):
    m=re.search(r'^guid: (\w+)',p.read_text(encoding='utf-8',errors='replace'),re.M)
    if m and m.group(1) in wanted:
        resolved[m.group(1)]=p.with_suffix('').relative_to(ENGINE).as_posix()
if set(resolved)!=wanted: failures.append('引用GUID缺失')
scene=(ENGINE/'Assets/Scenes/PersistanceScene.unity').read_text(encoding='utf-8')
blocks=dict(re.findall(r'^--- !u!\d+ &(\d+)\n(.*?)(?=^--- |\Z)',scene,re.M|re.S))
bindings=[('CHAR_PLAYER','401270075','85a0a22df9b38384c99bf9cbf15bac86'),
 ('CHAR_UNIT_02','1432622235','596d9e11bc4d5e044a15e5d0cfd21dc9'),
 ('CHAR_UNIT_03','1664658581','788de14946752004887de6beac1456fd')]
for name,fileid,guid in bindings:
    if guid not in blocks.get(fileid,'') or f'unitId: {name}\n    actor: {{fileID: {fileid}}}' not in scene:
        failures.append('场景绑定不符:'+name)
prefab=(ENGINE/resolved['cb046c5fa066b3943879537c2f3f6a5f']).read_text(encoding='utf-8')
if not ('SpriteRenderer:' in prefab and 'Animator:' in prefab and 'a803a687c9f0927489ebbe02a80597c1' in prefab):
    failures.append('显示预制体引用不符')

diff=subprocess.run(['git','-C',str(ROOT),'diff','--check'],capture_output=True,text=True,encoding='utf-8')
if diff.returncode: failures.append('git diff --check失败')
result={'date':'2026-10-24','documents':sorted(p.name for p in LIB.glob('*.md')),
 'node_coverage':covered,'checked_links':checked_links,'link_count':len(checked_links),
 'changed_protected':changed_protected,'changed_source':changed_source,'guid_targets':resolved,
 'referenced_asset_hashes':{p:sha(ENGINE/p) for p in resolved.values()},
 'static_bindings':'三角色标识→场景承载fileID→定义GUID；显示预制体→Animator Controller GUID',
 'git_diff_check':diff.returncode==0,'failures':failures,
 'manual_review':'结合正文阅读核查目的、流程、关键判断、协作、失败、边界、定位及状态；不以本脚本替代语义验收。',
 'not_run':['Unity编译','工程自动测试','游戏播放','播放器构建']}
with (OUT/'CO06-代码设计案补齐_静态验收_v1.json').open('x',encoding='utf-8') as stream:
    json.dump(result,stream,ensure_ascii=False,indent=2)
print(json.dumps({'documents':len(result['documents']),'nodes':len(covered),'links':len(checked_links),'failures':failures},ensure_ascii=False))
raise SystemExit(bool(failures))
