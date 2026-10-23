from pathlib import Path
import subprocess
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
LIBS=('系统设计文档','架构设计文档','Code_Design')
def renamed(text):
    return text.replace('元技能','元动作').replace('元效果','元持续效果')
planned=[]
for library in LIBS:
    for file in (ROOT/library).rglob('*'):
        if not file.is_file() or file.suffix not in ('.md','.csv'):
            continue
        before=file.read_bytes()
        text=before.decode('utf-8-sig')
        after_text=renamed(text)
        old=file.relative_to(ROOT).as_posix()
        new=renamed(old)
        if text==after_text and old==new:
            continue
        subprocess.run(['git','cat-file','-e','HEAD:'+old],cwd=ROOT,check=True)
        assert (ROOT/new).resolve().is_relative_to(ROOT.resolve())
        if old!=new:
            assert not (ROOT/new).exists(), new
        data=after_text.encode('utf-8')
        if before.startswith(b'\xef\xbb\xbf'): data=b'\xef\xbb\xbf'+data
        planned.append((old,new,before,data))
assert len({new for _,new,_,_ in planned})==len(planned)
manifest=OUT/'C-aa-bb-04_命名与路径映射_v1.json'
assert not manifest.exists()
# 先写引用内容，再在同一工作区内改文件名，最后改目录名。
for old,_,before,data in planned:
    p=ROOT/old
    assert p.read_bytes()==before
    p.write_bytes(data)
for old,_,_,_ in planned:
    p=ROOT/old
    if renamed(p.name)!=p.name:
        p.rename(p.with_name(renamed(p.name)))
for library in LIBS:
    dirs=sorted((p for p in (ROOT/library).rglob('*') if p.is_dir() and renamed(p.name)!=p.name),key=lambda p:len(p.parts),reverse=True)
    for p in dirs:
        target=p.with_name(renamed(p.name))
        assert p.resolve().is_relative_to((ROOT/library).resolve())
        assert target.resolve().is_relative_to((ROOT/library).resolve())
        assert not target.exists()
        p.rename(target)
for old,new,_,data in planned:
    assert (ROOT/new).read_bytes()==data
manifest.write_text(json.dumps([{'old_path':old,'new_path':new,'before_sha256':hashlib.sha256(b).hexdigest(),'after_sha256':hashlib.sha256(a).hexdigest()} for old,new,b,a in planned],ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'files':len(planned),'renamed_paths':[{'from':a,'to':b} for a,b,_,_ in planned if a!=b]},ensure_ascii=False,indent=2))
