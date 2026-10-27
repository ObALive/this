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

def gid_of_rt(fid):
    return field(objs[fid][1], 'm_GameObject') if fid in objs else None

def name_of_go_raw(v):
    if not v: return None
    m = re.search(r'fileID:\s*(\d+)', v)
    if not m: return None
    fid = m.group(1)
    b = objs.get(fid)
    if not b: return 'MISSING'
    cls, body = b
    if cls == '224':
        go = field(body, 'm_GameObject')
        if go:
            return name_of_go_raw(go)
        return 'RT-WITHOUT-GO'
    return field(body, 'm_Name')

# find RT for a GO
def rt_of_go(go_id):
    for fid, (cls, body) in objs.items():
        if cls == '224' and re.search(r'm_GameObject:\s*\{fileID:\s*' + go_id + r'\}', body):
            return fid
    return None

gos = {
    'panel': '2067759692', 'BaseSkills': '573850293', 'HealthSummary': '488543078',
    'Skill1': '228922411', 'Skill2': '1967859603', 'Skill3': '2036563003', 'Skill4': '775289350',
}
for label, go in gos.items():
    rt = rt_of_go(go)
    if rt:
        father = field(objs[rt][1], 'm_Father')
        print('%-14s go=%s rt=%s fatherName=%s' % (label, go, rt, name_of_go_raw(father)))
    else:
        print(label, 'no RT')

# label fathers
for label, fid in [('label0','1875193678'),('label1','1949239004'),('label2','58925814'),('label3','446884971')]:
    body = objs[fid][1]
    go = re.search(r'fileID:\s*(\d+)', field(body,'m_GameObject')).group(1)
    rt = rt_of_go(go)
    father = field(objs[rt][1], 'm_Father') if rt else None
    print('%-8s go=%s fatherName=%s' % (label, go, name_of_go_raw(father)))

# BaseSkills rect
srt = rt_of_go('573850293')
body = objs[srt][1]
for k in ('m_AnchorMin','m_AnchorMax','m_AnchoredPosition','m_SizeDelta'):
    print('BaseSkills', k, field(body,k))
