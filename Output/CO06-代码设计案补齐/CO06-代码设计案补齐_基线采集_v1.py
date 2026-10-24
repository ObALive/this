"""直接只读采集网络图、源码与只读目录身份，不初始化或修改数据库。"""
from pathlib import Path
import hashlib, json, sqlite3, subprocess, sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
ENGINE = Path('D:/myspace/Git/mygame')
def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args]).decode('utf-8', errors='replace').strip()
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
settings = ROOT / 'Tool/项目网络图/数据/数据管理.json'
active = json.loads(settings.read_text(encoding='utf-8'))['active_id']
database = settings.parent / active
conn = sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)
conn.row_factory = sqlite3.Row
def rows(sql, args=()):
    return [dict(r) for r in conn.execute(sql, args)]
nodes = rows('SELECT n.*,s.title AS route FROM nodes n JOIN sections s ON s.id=n.section_id ORDER BY n.seq')
implemented = [n for n in nodes if n['status'] == '已实现']
edges = rows('SELECT * FROM v_edge')
byid = {n['id']: n for n in nodes}
for n in implemented:
    for table in ('node_refs', 'node_objects', 'node_notes'):
        n[table] = rows(f'SELECT * FROM {table} WHERE node_id=? ORDER BY seq', (n['id'],))
    upstream = set()
    pending = [n['id']]
    while pending:
        current = pending.pop()
        for e in edges:
            if e['to_id'] == current and e['from_id'] not in upstream:
                upstream.add(e['from_id']); pending.append(e['from_id'])
    n['upstream'] = [byid[i] for i in sorted(upstream, key=lambda x: byid[x]['seq'])]
files = sorted((ENGINE/'Assets/Script').rglob('*.cs'))
files += [p for p in (ENGINE/'Assets/GameData').rglob('*') if p.is_file()]
files += list((ENGINE/'Assets/Scenes').glob('*.unity'))
files += [ENGINE/'ProjectSettings/EditorBuildSettings.asset', ENGINE/'ProjectSettings/ProjectVersion.txt', ENGINE/'ProjectSettings/TagManager.asset']
protected = {}
for directory in ('Rules', 'Code_Design', '系统设计文档', '架构设计文档', 'Tool/项目网络图'):
    for p in (ROOT/directory).rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:
            protected[p.relative_to(ROOT).as_posix()] = sha(p)
history = []
for rev in ('c744a32', '89a7d22', 'e422970', '9dc3cdd', '1c23dc3', 'af67237'):
    history.append({'commit': rev, 'changes': git(ENGINE, 'show', '--format=%H%n%s', '--name-status', rev)})
result = {'date': '2026-10-24', 'workspace_head': git(ROOT,'rev-parse','HEAD'),
    'workspace_status': git(ROOT,'status','--porcelain'),
    'database': {'path': str(database), 'selection': active, 'mode': 'ro', 'sha256': sha(database),
        'counts': rows('SELECT status,COUNT(*) AS count FROM nodes GROUP BY status'), 'implemented': implemented,
        'integrity': rows('PRAGMA integrity_check'), 'foreign_keys': rows('PRAGMA foreign_key_check'),
        'edges': edges},
    'source': {'root': str(ENGINE), 'head': git(ENGINE,'rev-parse','HEAD'), 'status': git(ENGINE,'status','--porcelain'),
        'files': {p.relative_to(ENGINE).as_posix(): sha(p) for p in files}, 'history': history},
    'protected_files': protected,
    'validation': '仅源码、配置和绑定静态核对；未编译、未测试、未运行游戏。'}
conn.close()
with (OUT/'CO06-代码设计案补齐_执行基线_v1.json').open('x',encoding='utf-8') as stream:
    json.dump(result,stream,ensure_ascii=False,indent=2)
print(json.dumps({'implemented': len(implemented), 'source_files':len(result['source']['files']), 'protected':len(protected)},ensure_ascii=False))
