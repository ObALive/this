"""Check adopted rule structure and active chapter links without changing rules."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

root = Path(__file__).resolve().parents[2]
out = root / 'Output' / 'CO04-02-代码设计改进'
docs = {p.name[:2]: p for p in (root / 'Rules').glob('[0-9][0-9]_*.md')}
titles = {p.read_text(encoding='utf-8-sig').splitlines()[0].lstrip('# '): key for key, p in docs.items()}
titles['目录维护规范'] = '05'
chapters = {}
subsections = {}
errors = []

for key, path in docs.items():
    in_fence = False
    current = None
    main = set()
    subs = set()
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        if line.startswith('```'):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = re.match(r'^#+ ([一二三四五六七八九十]+)、', line)
        if match:
            current = match[1]
            if current in main:
                errors.append(f'{path.name}: duplicate chapter {current}')
            main.add(current)
        match = re.match(r'^#+ (\d+)\. ', line)
        if match and current:
            subs.add((current, match[1]))
    if in_fence:
        errors.append(f'{path.name}: unclosed code fence')
    chapters[key] = main
    subsections[key] = subs

reference_count = 0
for path in sorted((root / 'Rules').glob('*.md')):
    text = path.read_text(encoding='utf-8-sig')
    if path.name == 'README.md':
        text = text.split('# 六、废弃登记')[0]
    elif path.name == 'BaseRules.md':
        text = text.split('## 四、本文件的历史')[0]
    for line_number, line in enumerate(text.splitlines(), 1):
        matches = []
        for match in re.finditer(r'NR-(0[1-8])\s*§([一二三四五六七八九十]+)(?:\.(\d+))?', line):
            matches.append((match[1], match[2], match[3]))
        for match in re.finditer(r'《([^》]+)》\s*(?:§|第)([一二三四五六七八九十]+)(?:\.(\d+))?', line):
            if match[1] in titles:
                matches.append((titles[match[1]], match[2], match[3]))
        for key, chapter, subsection in matches:
            reference_count += 1
            if chapter not in chapters[key] or (subsection and (chapter, subsection) not in subsections[key]):
                errors.append(f'{path.name}:{line_number}: invalid NR-{key} {chapter}.{subsection or ""}')

spec = docs['06'].read_text(encoding='utf-8-sig')
candidate = (out / 'CO04-02_第三步_代码设计案编辑规范_候选稿.md').read_text(encoding='utf-8-sig')
body_start = '## 一、目标与完成尺度'
body_matches = spec[spec.index(body_start):] == candidate[candidate.index(body_start):]
if not body_matches:
    errors.append('NR-06 body differs from approved candidate')
if '| 状态 | 生效 |' not in spec or '候选正文' in spec:
    errors.append('NR-06 metadata was not adopted')

for key in ['01', '03', '04', '05', '06', '07', '08']:
    if '| 更新日期 | 2026-10-17 |' not in docs[key].read_text(encoding='utf-8-sig'):
        errors.append(f'NR-{key}: update date mismatch')

nr02_changed = subprocess.check_output(['git', 'diff', '--', 'Rules/02_任务执行规范.md'], cwd=root)
if nr02_changed:
    errors.append('NR-02 was unexpectedly changed')
if len(chapters['06']) != 15:
    errors.append('NR-06 must contain fifteen main chapters')

index = (root / 'Rules' / 'README.md').read_text(encoding='utf-8-sig')
if '| v12 | 2026-10-17 |' not in index:
    errors.append('Index adoption history missing')
if re.search(r'\n\n\| 2026-10-17 \| NR-06 的系统级', index):
    errors.append('Retirement row is disconnected from its table')

checks = {
    'baseline': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
    'nr06_main_chapters': len(chapters['06']),
    'active_explicit_references_checked': reference_count,
    'nr06_body_matches_approved_candidate': body_matches,
    'nr02_unchanged': not bool(nr02_changed),
    'rules_content_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root / 'Rules').glob('*.md'))},
    'errors': errors,
}
(out / 'CO04-02_Rules替换核对.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: v for k, v in checks.items() if k != 'rules_content_sha256'}, ensure_ascii=False, indent=2))
raise SystemExit(bool(errors))
