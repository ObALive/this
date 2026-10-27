import re, json

path = r'D:/myspace/Git/mygame/Assets/Scenes/UI.unity'
text = open(path, encoding='utf-8').read()
blocks = re.split(r'^--- !u!(\d+) &(\d+).*$', text, flags=re.M)
objs = {}
i = 1
while i + 2 <= len(blocks) - 0:
    cls = blocks[i]; fid = blocks[i + 1]; body = blocks[i + 2]
    objs[fid] = (cls, body)
    i += 3

def go_name(go_id):
    b = objs.get(go_id)
    if not b: return 'MISSING'
    m = re.search(r'^\s*m_Name:\s*(.*)$', b[1], re.M)
    return m.group(1).strip() if m else '?'

fields = {
    'details': '1538517151', 'hint': '166982040', 'healthSummary': '488543080',
    'moveLabel': '474455404', 'moveButton': '2050392728', 'moveBackground': '2050392729',
    'skillButtons': ['228922413','1967859605','2036563005','775289352'],
    'skillLabels': ['1875193678','1949239004','58925814','446884971'],
}

def info(fid):
    if fid not in objs: return {'exists': False}
    cls, body = objs[fid]
    go = re.search(r'm_GameObject:\s*\{fileID:\s*(\d+)\}', body)
    go_id = go.group(1) if go else None
    fonts = re.findall(r'm_fontAsset:\s*\{fileID:\s*\d+,\s*guid:\s*(\w+)', body)
    txt = re.search(r'^\s*m_text:\s*(.*)$', body, re.M)
    raycast = re.search(r'm_RaycastTarget:\s*(\d+)', body)
    return {
        'exists': True, 'class': cls, 'gameObject': go_id, 'name': go_name(go_id) if go_id else None,
        'fonts': fonts, 'text': (txt.group(1)[:60] if txt else None),
        'raycast': raycast.group(1) if raycast else None,
        'onClick': ('m_OnClick' in body),
    }

out = {}
for k, v in fields.items():
    if isinstance(v, list):
        out[k] = {x: info(x) for x in v}
    else:
        out[k] = info(v)

print(json.dumps(out, ensure_ascii=False, indent=2))
