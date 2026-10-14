"""上游缺少设计依据时采用现有工具的开放填写状态，不编造候选玩法。"""
from pathlib import Path
import sys, json, subprocess
sys.dont_write_bytecode = True
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
from N01_补图规格_v1 import GAPS, SOURCES
coverage=json.loads((OUT/'N01_功能覆盖数据_v1.json').read_text(encoding='utf-8'))
records=[]
for code,title,sources,problem,question in GAPS:
    refs=[]
    for source in sources.split(';'):
        key,clause=source.split(':',1)
        refs.append(SOURCES[key]+' §'+clause)
    records.append({
        'gap_id':'N01-GAP-'+code[1:].zfill(3), 'title':title,
        'level':'B0' if code in ('G01','G02','G03','G04','G07','G08','G10','G11') else 'B1',
        'status':'开放填写','source_ref':'；'.join(refs),
        'impact_scope':'；'.join(d['new_location'] for d in coverage if code in d['blockers']),
        'close_condition':question,
        'owner':'游戏总监 / 对应内容与数值设计方' if code=='G09' else '游戏总监 / 对应规则设计方',
        'priority_round':'N01 第一轮；对应图上 '+code,
        'options':[], 'analysis_detail':problem,
    })
data={'meta':{'title':'N01 战斗玩家功能上游未决库','chapter':'N01-战斗玩家功能补图','domain':'06-战斗及必要战斗内通用规则',
              'analysis_doc':'Output/N01-战斗玩家功能补图/N01_未决事项_v1.md','created_at':'2026-10-14'},
      'db_path':'Output/N01-战斗玩家功能补图/N01_上游未决库_v1.sqlite','gaps':records}
path=OUT/'N01_未决建库数据_v1.json'
path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
commands=[
 [sys.executable,'-B','-X','utf8',str(ROOT/'Tool/缺口决策系统/建库工具/build_decision_db.py'),'--data',str(path)],
 [sys.executable,'-B','-X','utf8',str(ROOT/'Tool/缺口决策系统/建库工具/export_catalog.py'),'--db',str(OUT/'N01_上游未决库_v1.sqlite'),'--out-dir',str(OUT)],
]
outputs=[]
for cmd in commands:
    result=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
    outputs.append({'command':cmd,'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
    assert result.returncode==0, result.stderr
(OUT/'N01_未决建库核验_v1.json').write_text(json.dumps(outputs,ensure_ascii=False,indent=2),encoding='utf-8')
print(outputs[0]['stdout']);print(outputs[1]['stdout'])
