from pathlib import Path
import sys,json,subprocess,sqlite3,threading,hashlib
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/'Tool/项目网络图'))
import db,model as M,server,store
prod=OUT/'N01_战斗玩家功能新图_v1.sqlite'
temporary=OUT/'N01_最终前端核验临时库_v1.sqlite'
assert not temporary.exists()
before=hashlib.sha256(prod.read_bytes()).hexdigest()
with db.connect(prod,readonly=True) as src,sqlite3.connect(temporary) as dst:src.backup(dst)
store.DB_FILE=temporary;store.DATA_DIR=OUT;store.BACKUP_DIR=OUT;store.EXPORT_DIR=OUT
class Quiet(server.Handler):
    def log_message(self,*args):pass
    def handle(self):
        try:super().handle()
        except ConnectionResetError:pass
http=server.ThreadingHTTPServer(('127.0.0.1',0),Quiet)
thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
try:
    r=subprocess.run(['node',str(OUT/'N01_前端冒烟适配_v1.js'),f'http://127.0.0.1:{http.server_port}'],capture_output=True,text=True,encoding='utf-8',cwd=ROOT,timeout=60)
    final=db.load_model(prod)
    record={'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'port':http.server_port,
      'model_restored':db.model_payload(final)==db.model_payload(db.load_model(temporary)),
      'production_file_unchanged':hashlib.sha256(prod.read_bytes()).hexdigest()==before,
      'final_stats':M.serialize(final)['stats'],'export_equal':M.to_markdown(final)==(OUT/'N01_战斗玩家功能新图_v2.md').read_text(encoding='utf-8'),
      'graph_errors':M.validate(final)['stats']['errors'],'sqlite_integrity':db.verify(prod)['integrity'],
      'services':'本次临时测试服务在 finally 中停止；供用户审阅的独立服务另行登记。',
      'limitations':'只验图模型、现有网页和编辑保存，未实现 Unity，未决事项未伪装成验收通过。'}
    (OUT/'N01_最终前端核验结果_v1.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    assert r.returncode==0 and record['model_restored'] and record['production_file_unchanged'] and record['export_equal']
    print(json.dumps({k:v for k,v in record.items() if k not in ('stdout','stderr')},ensure_ascii=False,indent=2))
finally:
    http.shutdown();http.server_close();thread.join(timeout=5)
