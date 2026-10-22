"""Read-only verification of the delivered graph and maintained documents."""
from __future__ import annotations
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'Tool/项目网络图'))
import db
import model as M

checks = []
def check(name, condition, evidence=''):
    checks.append({'check': name, 'passed': bool(condition), 'evidence': evidence})


database = ROOT / 'Tool/项目网络图/数据/N01_完整依赖清理新图_v2.sqlite'
conn = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
check('SQLite完整性', conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok')
check('外键完整性', not conn.execute('PRAGMA foreign_key_check').fetchall())
conn.close()
model = db.load_model(database)
view = M.serialize(model)
check('无未解析引用或依赖环', view['stats']['errors'] == 0 and view['stats']['unresolved_refs'] == 0, str(view['stats']))
check('无警告', view['stats']['warnings'] == 0)
check('原时间轴1独立节点删除', model.node('n13') is None)
core = model.node('n36')
check('原6成为逻辑1', model.index_label(core) == '时间轴/逻辑 1' and '回排' in core.body)
obj = next(o for o in core.objects if o.name == 'TimeLineManager')
check('TimeLineManager职责归入新1', 'ElectedObject' in obj.note and '元技能' in obj.note and obj.path == '' and '整场战斗的唯一事件管理器' not in obj.note)
check('元技能统一生命周期', '生命周期' in model.node('n6').body and '生效时机' in model.node('n6').body)
check('查看节点仅抽出镜头内容', model.node('n50').body == '玩家能点选单位查看详情；查看不提交行为，不改变当前行动者。行动槽跟随被查看单位，权限由战斗进入路线的操作权限条目统一约束。')
check('平移缩放合并为一个节点', sum(n.summary == '战场镜头平移和缩放' for n in model.nodes) == 1)
check('镜头定位独立节点', sum(n.summary == '镜头定位当前行动者' for n in model.nodes) == 1)
check('净时长累计和显示分离', model.index_label(model.node('n147')) == '时间轴/逻辑 3' and model.index_label(model.node('n21')) == '时间轴/UI 4')
check('保存恢复接入边界登记', '实际存档服务' in model.node('n148').body and '延期' in model.node('n148').body)
check('总量', len(model.nodes) == 149 and len(model.sections) == 24)

edges, _ = M.build_edges(model)
upstream = {}
for edge in edges:
    upstream.setdefault(edge['to'], set()).add(edge['from'])
def ancestors(ident):
    pending = list(upstream.get(ident, [])); seen = set()
    while pending:
        value = pending.pop()
        if value not in seen:
            seen.add(value); pending.extend(upstream.get(value, []))
    return seen
logic_ids = {n.id for n in model.nodes if model.section(n.section_id).title == '逻辑'}
ui_ids = {n.id for n in model.nodes if model.section(n.section_id).title == 'UI'}
check('时间轴逻辑不直接或传递依赖UI', not any(ancestors(i) & ui_ids for i in logic_ids))
check('详情查看解除撤退前置', 'n125' not in ancestors('n50'), f"前置数量：62→{len(ancestors('n50'))}")
check('AI以新时间轴1为前置', 'n36' in ancestors('n22'))
check('全部引用文本可独立解析', all(M.resolve_ref_text(model, r.raw)[0] == r.target_id for n in model.nodes for r in n.refs))
check('图导出与库一致', (OUT / 'N03_网络图导出.md').read_text(encoding='utf-8') == M.to_markdown(model))
candidate = json.loads((OUT / 'N03_网络图候选模型.json').read_text(encoding='utf-8'))
check('落库模型与候选一致', view == candidate)

manifest_path = OUT / 'N03_设计文件变更.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
extra = '系统设计文档/README.md'
if not any(x['path'] == extra for x in manifest):
    before = subprocess.check_output(['git', 'show', 'HEAD:' + extra], cwd=ROOT).decode('utf-8').replace('\r\n', '\n')
    manifest.append({'path': extra, 'head_exists': True, 'before_sha256': hashlib.sha256(before.encode()).hexdigest()})

new_links = []
bad_links = []
new_illegal = []
for entry in manifest:
    path = entry['path']; text = (ROOT / path).read_text(encoding='utf-8')
    entry['after_sha256'] = hashlib.sha256(text.encode()).hexdigest()
    head = subprocess.run(['git', 'cat-file', '-e', 'HEAD:' + path], cwd=ROOT, capture_output=True)
    check('可复原：' + path, head.returncode == 0)
    diff = subprocess.run(['git', '-c', 'core.safecrlf=false', 'diff', '--no-ext-diff', '--unified=0', '--', path], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', check=True).stdout
    added = '\n'.join(x[1:] for x in diff.splitlines() if x.startswith('+') and not x.startswith('+++'))
    check('无替换字符：' + path, '\ufffd' not in text)
    for ref in re.findall(r'`([^`]+\.md)`', added):
        ref_path = Path(ref)
        options = [ROOT / ref_path, ROOT / '系统设计文档' / ref_path, (ROOT / path).parent / ref_path]
        found = any(p.is_file() for p in options)
        # Existing short-name references can resolve by their unique file name.
        if not found and '/' not in ref and '\\' not in ref:
            found = len(list((ROOT / '系统设计文档').rglob(ref))) == 1
        new_links.append((path, ref))
        if not found:
            bad_links.append((path, ref))
    if path.startswith('系统设计文档/') and path != extra:
        for token in re.findall(r'(?:Code_Design/|Task/|Output/|Report/|Tool/|Rules/|REQ-[A-Z0-9-]+)', added):
            new_illegal.append((path, token))
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
check('新增引用落点存在', not bad_links, str(bad_links))
check('系统设计新增内容无越界引用及过程编号', not new_illegal, str(new_illegal))
term_text = (ROOT / '系统设计文档/00-总览/02_术语表.md').read_text(encoding='utf-8')
term_rows = re.findall(r'^\| T-(\d+) \|', term_text, re.M)
check('术语编号唯一', len(term_rows) == len(set(term_rows)))
check('新术语登记齐全', all(str(i) in term_rows for i in range(188, 195)))
overview = (ROOT / '系统设计文档/06-战斗/10-战斗总览/10_战斗总览设计.md').read_text(encoding='utf-8')
behavior = (ROOT / '系统设计文档/06-战斗/85-战斗行为系统/85_战斗行为系统设计.md').read_text(encoding='utf-8')
meta = (ROOT / '系统设计文档/01-通用系统/70-元技能/70_元技能设计补充说明.md').read_text(encoding='utf-8')
arch = (ROOT / '架构设计文档/架构设计案.md').read_text(encoding='utf-8')
check('交互与角色行为边界已定义', all(s in overview for s in ['三者独立', '受到伤害、治疗', '平移、缩放', '角色实际执行的战斗行为']))
check('正式状态与UI延伸及表现区分', all(s in behavior for s in ['UI延伸变量', '相机位置与缩放', '当前行动者始终属于战斗规则状态']))
check('元技能生命周期权威定义存在', '### 4.3 角色行为生命周期' in meta and '移动、技能释放、容器搜刮、场景交互、撤退与防御待机' in meta)
check('架构模块及协作同步', all(s in arch for s in ['| 01-通用系统 | 70 | 元技能 |', '| M05 | 01-70、', '9.5.3.1 战斗行动机会与角色行为的交接', '逻辑推进与净时长累计独立于这些界面能力']))
whitespace = subprocess.run(['git', '-c', 'core.safecrlf=false', 'diff', '--check', '--', *[x['path'] for x in manifest]], cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
check('Git差异空白检查', whitespace.returncode == 0, whitespace.stdout)
result = {'date': '2026-10-22', 'stats': view['stats'], 'changed_design_files': len(manifest), 'checks': checks, 'passed': all(x['passed'] for x in checks), 'limits': ['核验设计与网络图，未实现或运行Unity战斗程序', '技术路径及未定规则输入按用户决定留到节点实施时讨论', '已有其他任务的过程文件与代码设计案未被改写']}
(OUT / 'N03_核验结果.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
lines = ['# N03 核验结果', '', f"总结果：{'通过' if result['passed'] else '未通过'}；{len(checks)}项检查，设计文档{len(manifest)}份。", '', '| 检查项 | 结果 | 说明 |', '| --- | --- | --- |']
for item in checks:
    evidence = item['evidence'].replace('|', '／').replace('\n', ' ')
    lines.append(f"| {item['check']} | {'通过' if item['passed'] else '失败'} | {evidence} |")
lines += ['', '## 验证边界', '', *['- ' + x for x in result['limits']]]
(OUT / 'N03_核验结果.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(json.dumps({'passed': result['passed'], 'checks': len(checks), 'failed': [x for x in checks if not x['passed']], 'design_files': len(manifest)}, ensure_ascii=False))
sys.exit(0 if result['passed'] else 1)
