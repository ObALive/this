from pathlib import Path
import subprocess
import hashlib
import json
import re
import csv
import io

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
LIBS=('系统设计文档','架构设计文档','Code_Design')
mapping=json.loads((OUT/'C-aa-bb-04_命名与路径映射_v1.json').read_text(encoding='utf-8'))
files=[p for lib in LIBS for p in (ROOT/lib).rglob('*') if p.is_file() and p.suffix in ('.md','.csv')]
results=[]
def check(name,condition,detail=None):
    results.append({'check':name,'passed':bool(condition),'detail':detail})

bad_names=[str(p.relative_to(ROOT)) for p in files if '元技能' in str(p) or '元效果' in str(p) or re.search('元技能|元效果',p.read_text(encoding='utf-8-sig'))]
check('三个设计库的正文与路径使用最终命名',not bad_names,bad_names)
bad_refs=[]; ref_count=0
for p in files:
    if p.suffix!='.md':continue
    for value in re.findall(r'`([^`\n]+)`',p.read_text(encoding='utf-8-sig')):
        if not ('元动作' in value or '元持续效果' in value) or not value.endswith(('.md','.csv')):continue
        ref_count+=1
        if value.split('/')[0] in LIBS:
            targets=[ROOT/value]
        else:
            targets=[p.parent/value]+[ROOT/lib/value for lib in LIBS]
        valid=any(t.exists() for t in targets)
        if not valid and '/' not in value:
            valid=len([f for f in files if f.name==value])==1
        if not valid:bad_refs.append({'file':str(p.relative_to(ROOT)),'reference':value})
check('相关文档引用均可解析',not bad_refs,{'checked':ref_count,'unresolved':bad_refs})

stale=[]
pattern=re.compile('全部效果|技能的效果一律|伤害、状态与增益统一|效果是唯一|任何系统产生效果|投掷类效果|一次性移除|EFF-THROW-001')
for p in files:
    for n,line in enumerate(p.read_text(encoding='utf-8-sig').splitlines(),1):
        if pattern.search(line):stale.append({'file':str(p.relative_to(ROOT)),'line':n,'text':line})
check('泛化职责及一次性投掷元效果引用查漏',not stale,stale)

effect_path='系统设计文档/06-战斗/75-元持续效果系统/75_元持续效果表.csv'
throw_path='系统设计文档/06-战斗/80-技能与库存联动/80_投掷组件表.csv'
for p,count,key in [(effect_path,15,'元持续效果ID'),(throw_path,13,'ID')]:
    raw=(ROOT/p).read_text(encoding='utf-8-sig')
    table=list(csv.reader(io.StringIO(raw)))
    check('CSV 列数及唯一 ID：'+p,all(len(r)==count for r in table) and len({r[0] for r in table[1:]})==len(table)-1,{'columns':count,'rows':len(table)-1})
effects=list(csv.DictReader(io.StringIO((ROOT/effect_path).read_text(encoding='utf-8-sig'))))
check('元持续效果清单保留五项持续规则及扩展项',set(r['元持续效果ID'] for r in effects)=={'EFF-ATTR-001','EFF-STATE-001','EFF-DOT-001','EFF-PIERCE-001','EFF-INHERIT-001','EFF-TBD-001'})

original_effect='系统设计文档/06-战斗/75-元效果系统/75_元效果表.csv'
old=list(csv.DictReader(io.StringIO(subprocess.check_output(['git','show','HEAD:'+original_effect],cwd=ROOT).decode('utf-8-sig'))))
lookup={r['元效果ID']:r for r in old}
protected=('叠加规则','同名判定依据','强度方向','持续时间','移除条件','战斗外可生效','Demo状态')
check('持续规则原有叠加与期限配置保持',all(all(r[k]==lookup[r['元持续效果ID']][k] for k in protected) for r in effects))
old_throw=list(csv.DictReader(io.StringIO(subprocess.check_output(['git','show','HEAD:'+throw_path],cwd=ROOT).decode('utf-8-sig'))))
new_throw=list(csv.DictReader(io.StringIO((ROOT/throw_path).read_text(encoding='utf-8-sig'))))
check('投掷资格、伤害基础、后摇基础及组件 ID 保持',all(all(a[k]==b[k] for k in ('ID','投掷资格','伤害基础','后摇基础','与其他组件的关系')) for a,b in zip(old_throw,new_throw)) and len(old_throw)==len(new_throw))

status_files=('01-通用系统/70_元动作代码设计案.md','06-战斗/40_技能系统代码设计案.md','06-战斗/80_技能与库存联动代码设计案.md','05-运营与经济/05_物品系统代码设计案.md')
index=(ROOT/'Code_Design/README.md').read_text(encoding='utf-8-sig')
check('四份受影响技术稿及索引明确待修订',all('| 状态 | 待修订 |' in (ROOT/'Code_Design'/p).read_text(encoding='utf-8-sig') and any('`'+p+'` |' in line and '| 待修订 |' in line for line in index.splitlines()) for p in status_files))
check('执行契约及混合分层缺口具有关闭条件',all(value in (ROOT/path).read_text(encoding='utf-8-sig') for path,value in [('Code_Design/01-通用系统/70_元动作代码设计案.md','REQ-SKILLDEF-06'),('Code_Design/06-战斗/80_技能与库存联动代码设计案.md','REQ-SKILLITEM-13')]))
meta=(ROOT/'系统设计文档/01-通用系统/70-元动作/70_元动作设计补充说明.md').read_text(encoding='utf-8-sig')
effect=(ROOT/'系统设计文档/06-战斗/75-元持续效果系统/75_元持续效果系统设计.md').read_text(encoding='utf-8-sig')
check('两种实例的生效、挂载与销毁边界有明确陈述',all(v in meta for v in ('即时性效果实例生效后销毁','持续性效果实例解除挂载并销毁','技能元对象定义及组件配置')) and all(v in effect for v in ('持续参与相关规则的计算、判定或触发结算','即时性效果实例生效后销毁','持续时间结束后其运行实例解除挂载并销毁')))
check('本任务过程编号未进入三个设计库',all('C-aa-bb-04' not in p.read_text(encoding='utf-8-sig') for p in files))

bad_ws=[]
manifest=[]
for r in mapping:
    p=ROOT/r['new_path']
    before=subprocess.check_output(['git','show','HEAD:'+r['old_path']],cwd=ROOT)
    data=p.read_bytes()
    manifest.append({'original_path':r['old_path'],'current_path':r['new_path'],'baseline_sha256':hashlib.sha256(before).hexdigest(),'current_sha256':hashlib.sha256(data).hexdigest(),'renamed':r['old_path']!=r['new_path']})
    if any(line.rstrip()!=line for line in data.decode('utf-8-sig').splitlines()):bad_ws.append(r['new_path'])
check('45 份设计库文件均有已提交原稿依据',len(manifest)==45)
check('包含新路径文件在内无行尾空白',not bad_ws,bad_ws)
diff=subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
check('git diff --check',diff.returncode==0,diff.stdout)
allowed={r['current_path'] for r in manifest}|{r['original_path'] for r in manifest}
changed=subprocess.check_output(['git','diff','--name-only','-z'],cwd=ROOT).decode('utf-8').split('\0')
unexpected=[p for p in changed if p and p not in allowed and p not in ('Report/C-aa-bb-04_Report.md','Tool/项目网络图/数据/N01_完整依赖清理新图_v2.sqlite')]
check('已跟踪文件变更范围保持隔离',not unexpected,unexpected)

target=OUT/'C-aa-bb-04_一致性核验结果_v1.json'
target2=OUT/'C-aa-bb-04_最终文件清单_v1.json'
assert not target.exists() and not target2.exists()
target.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
target2.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'checks':len(results),'passed':sum(r['passed'] for r in results),'failed':[r for r in results if not r['passed']],'files':len(manifest),'related_references':ref_count},ensure_ascii=False,indent=2))
raise SystemExit(0 if all(r['passed'] for r in results) else 1)
