import re

path = r'D:/myspace/Git/mygame/Assets/Scenes/UI.unity'
text = open(path, encoding='utf-8').read()
blocks = re.split(r'^--- !u!(\d+) &(\d+).*$', text, flags=re.M)
objs = {}
i = 1
while i + 2 <= len(blocks):
    objs[blocks[i + 1]] = (blocks[i], blocks[i + 2])
    i += 3

def field(body, name):
    m = re.search(r'^[ \t]*' + name + r':[ \t]*(.*)$', body, re.M)
    return m.group(1).strip() if m else None

def go_name(gid):
    b = objs.get(gid)
    return field(b[1], 'm_Name') if b else 'MISSING'

def comp(fid):
    b = objs.get(fid)
    if not b: return None
    cls, body = b
    go = field(body, 'm_GameObject')
    go_id = re.search(r'fileID:\s*(\d+)', go).group(1) if go else None
    return {'class': cls, 'go': go_id, 'name': go_name(go_id), 'text': field(body, 'm_text'),
            'font': re.findall(r'm_fontAsset:\s*\{fileID:\s*\d+,\s*guid:\s*(\w+)', body)}

for label, fid in [('healthSummary','488543080'),('details','1538517151'),('hint','166982040'),
                   ('skillLabel0','1875193678'),('skillLabel1','1949239004'),
                   ('skillLabel2','58925814'),('skillLabel3','446884971')]:
    print(label, comp(fid))

# RectTransform for panel GO and HealthSummary GO
def rt_of(go_id):
    for fid, (cls, body) in objs.items():
        if cls == '224' and re.search(r'm_GameObject:\s*\{fileID:\s*' + go_id + r'\}', body):
            return fid, body
    return None, None

for label, go in [('panel','2067759692'),('health','488543078')]:
    fid, body = rt_of(go)
    if body:
        print(label, 'RT', fid, 'father', field(body,'m_Father'), 'size', field(body,'m_SizeDelta'),
              'anchorMin', field(body,'m_AnchorMin'), 'anchorMax', field(body,'m_AnchorMax'),
              'anchoredPos', field(body,'m_AnchoredPosition'))
