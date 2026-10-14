from pathlib import Path
import sys, json, sqlite3, hashlib
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'Tool/项目网络图'))
import db, model

source = ROOT / 'Tool/项目网络图/数据/项目网络图.sqlite'
backup = OUT / 'N01_原图一致性备份_v1.sqlite'
editable = OUT / 'N01_战斗玩家功能新图_v1.sqlite'
assert not backup.exists() and not editable.exists(), '已有产物，禁止覆盖基线'
with db.connect(source, readonly=True) as src, sqlite3.connect(backup) as dst:
    src.backup(dst)
with db.connect(backup, readonly=True) as src, sqlite3.connect(editable) as dst:
    src.backup(dst)
m = db.load_model(backup)
payload = db.model_payload(m)
def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
manifest = {
    'sampled_at': datetime.now().astimezone().isoformat(),
    'source': str(source), 'backup': str(backup), 'editable': str(editable),
    'model_sha256': digest(payload),
    'source_file_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'backup_file_sha256': hashlib.sha256(backup.read_bytes()).hexdigest(),
    'model_equal_at_sampling': payload == db.model_payload(db.load_model(source)),
    'stats': model.serialize(m)['stats'], 'database_check': db.verify(backup),
    'N02_comparison': '未读取 N02 产物；同基线协作以此模型 SHA256 为比对依据，跨任务一致性待外部核对。',
}
(OUT / 'N01_基线登记_v1.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
(OUT / 'N01_原图完整模型_v1.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
(OUT / 'N01_原图导出_v1.md').write_text(model.to_markdown(m), encoding='utf-8')
print(json.dumps(manifest, ensure_ascii=False, indent=2))
