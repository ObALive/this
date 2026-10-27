import re, sys

path = r'D:/myspace/Git/mygame/Assets/Scenes/UI.unity'
text = open(path, encoding='utf-8').read()
blocks = re.split(r'^--- !u!(\d+) &(\d+).*$', text, flags=re.M)
# blocks: [pre, cls, id, body, cls, id, body, ...]
objs = {}
i = 1
while i + 2 < len(blocks) + 1 and i + 2 <= len(blocks):
    cls = blocks[i]; fid = blocks[i + 1]; body = blocks[i + 2]
    objs[fid] = (cls, body)
    i += 3

def name_of_go(go_id):
    if go_id in objs:
        m = re.search(r'^\s*m_Name:\s*(.*)$', objs[go_id][1], re.M)
        return m.group(1).strip() if m else '?'
    return 'MISSING'

def describe(fid):
    if fid not in objs:
        return 'MISSING'
    cls, body = objs[fid]
    m = re.search(r'm_GameObject:\s*\{fileID:\s*(\d+)\}', body)
    go = m.group(1) if m else None
    script = re.search(r'm_Script:\s*\{fileID:\s*\d+,\s*guid:\s*(\w+)', body)
    onClick = 'm_OnClick' in body
    return 'class=%s gameObject=%s (%s) script=%s onClickBlock=%s' % (
        cls, go, name_of_go(go) if go else '-', script.group(1) if script else '-', onClick)

targets = {
    'details': '1538517151',
    'hint': '166982040',
    'healthSummary': '488543080',
    'moveLabel': '474455404',
    'moveButton': '2050392728',
    'moveBackground': '2050392729',
    'skillButton0': '228922413',
    'skillButton1': '1967859605',
    'skillButton2': '2036563005',
    'skillButton3': '775289352',
    'skillLabel0': '1875193678',
    'skillLabel1': '1949239004',
    'skillLabel2': '58925814',
    'skillLabel3': '446884971',
}
for k, v in targets.items():
    print('%-14s %-12s %s' % (k, v, describe(v)))

print()
print('panel component 2067759694 parent go:', name_of_go(re.search(r'm_GameObject:\s*\{fileID:\s*(\d+)\}', objs['2067759694'][1]).group(1)))

# Check skill button OnClick persistent calls
for k in ['skillButton0','skillButton1','skillButton2','skillButton3']:
    fid = targets[k]
    body = objs[fid][1]
    seg = body[body.find('m_OnClick'):] if 'm_OnClick' in body else ''
    m = re.search(r'm_OnClick:\s*\n((?:\s+.*\n){0,12})', body)
    print('---', k, '---')
    print(m.group(0)[:400] if m else 'no m_OnClick')
