from pathlib import Path
import sys,json,hashlib,subprocess,re
from datetime import datetime
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/'Tool/项目网络图'))
import db,model as M
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
manifest=json.loads((OUT/'N01_基线登记_v1.json').read_text(encoding='utf-8'))
check=json.loads((OUT/'N01_核验结果_v2.json').read_text(encoding='utf-8'))
m=db.load_model(OUT/'N01_战斗玩家功能新图_v1.sqlite')
assert sha(ROOT/'Tool/项目网络图/数据/项目网络图.sqlite')==manifest['source_file_sha256']
assert sha(OUT/'N01_原图一致性备份_v1.sqlite')==manifest['backup_file_sha256']
assert sha(OUT/'N01_战斗玩家功能新图_v1.sqlite')==check['new_file_sha256']
assert M.to_markdown(m)==(OUT/'N01_战斗玩家功能新图_v2.md').read_text(encoding='utf-8')
features=json.loads((OUT/'N01_功能覆盖数据_v2.json').read_text(encoding='utf-8'))
assert len(features)==len(m.nodes)==145
assert len({d['new_location'] for d in features})==145
browser=json.loads((OUT/'N01_最终浏览器读取_v1.json').read_text(encoding='utf-8'))
assert browser['nodes']==browser['rows']==145
detail=json.loads((OUT/'N01_最终详情读取_v1.json').read_text(encoding='utf-8'))
assert detail['dialogOpen'] and detail['objectRows']==2
assert any('占用' in text for text in detail['notes'])
for row in json.loads((OUT/'N01_资料登记_v1.json').read_text(encoding='utf-8')):
    assert sha(ROOT/row['path'])==row['sha256'],row['path']
report=ROOT/'Report/N01-战斗玩家功能补图_Report.md'
headings=re.findall(r'^## (\d+) ',report.read_text(encoding='utf-8'),re.M)
assert headings==[str(i) for i in range(1,12)]
status=subprocess.run(['git','-c','core.quotepath=false','status','--porcelain','--untracked-files=all'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',check=True).stdout
for line in status.splitlines():
    path=line[3:].strip('"')
    assert path.startswith('Output/N01-战斗玩家功能补图/') or path=='Report/N01-战斗玩家功能补图_Report.md',line
inventory=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(OUT.iterdir()) if p.is_file()]
result={'checked_at':datetime.now().astimezone().isoformat(),'status':'Blocked','full_coverage_achieved':False,
        'original_unchanged':True,'backup_unchanged':True,'new_database_matches_final_check':True,
        'all_registered_sources_unchanged':True,'report_sections':11,'coverage_rows':145,
        'browser_rendered_nodes':browser['nodes'],'browser_detail_preserves_object_description':True,
        'graph':M.validate(m)['stats'],'all_changes_inside_authorized_paths':True,
        'git_status':status,'files':inventory,'report_sha256':sha(report)}
(OUT/'N01_收口检查_v1.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ('files','git_status')},ensure_ascii=False,indent=2))
