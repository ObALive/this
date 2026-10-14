"""一次性副本上运行原工具前端冒烟，产物库不接受测试写入。"""
from pathlib import Path
import sys, subprocess, json, sqlite3, threading, urllib.request
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/'Tool/项目网络图'))
import db, model as M, server, store
original=OUT/'N01_战斗玩家功能新图_v1.sqlite'
test=OUT/'N01_前端核验临时库_v1.sqlite'
assert not test.exists()
with db.connect(original,readonly=True) as source,sqlite3.connect(test) as target:
    source.backup(target)
store.DB_FILE=test
store.DATA_DIR=OUT;store.BACKUP_DIR=OUT;store.EXPORT_DIR=OUT
class Quiet(server.Handler):
    def log_message(self,*args):pass
http=server.ThreadingHTTPServer(('127.0.0.1',0),Quiet)
thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
try:
    result=subprocess.run(['node',str(ROOT/'Tool/项目网络图/测试/smoke_dom.js'),f'http://127.0.0.1:{http.server_port}'],capture_output=True,text=True,encoding='utf-8',cwd=ROOT,timeout=60)
    record={'test':'现有前端 DOM 与 HTTP 冒烟','port':http.server_port,'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'temporary_database':str(test),
            'model_restored':db.model_payload(db.load_model(original))==db.model_payload(db.load_model(test)),
            'limitations':'现有测试采用 DOM 垫片，覆盖载入、图渲染、详情和编辑保存；不等同于游戏行为验证或人工视觉审美验收。'}
    (OUT/'N01_前端核验结果_v1.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print(result.stdout);print(result.stderr)
    assert result.returncode==0 and record['model_restored']
finally:
    http.shutdown();http.server_close();thread.join(timeout=5)
