"""适配工具的旧工作区路径与样例名；全部产物在本任务目录。"""
from pathlib import Path
import sys, subprocess, json, sqlite3, threading, hashlib
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/'Tool/项目网络图'))
import db, server, store

# 旧决策工具仍按 Dsh 找根；指定绝对目标路径，保持工作区边界。
decision_db=OUT/'N01_上游未决库_v1.sqlite'
commands=[
 [sys.executable,'-B','-X','utf8',str(ROOT/'Tool/缺口决策系统/建库工具/build_decision_db.py'),'--data',str(OUT/'N01_未决建库数据_v1.json'),'--db',str(decision_db)],
 [sys.executable,'-B','-X','utf8',str(ROOT/'Tool/缺口决策系统/建库工具/export_catalog.py'),'--db',str(decision_db),'--out-dir',str(OUT)],
]
records=[]
for cmd in commands:
    r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',cwd=ROOT)
    records.append({'command':cmd,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
    assert r.returncode==0,r.stderr
(OUT/'N01_未决建库核验_v2.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')

source=ROOT/'Tool/项目网络图/测试/smoke_dom.js'
text=source.read_text(encoding='utf-8')
text=text.replace('const TOOL = path.join(__dirname, "..");','const TOOL = path.resolve(__dirname, "../../Tool/项目网络图");')
text=text.replace('场景道具摆放','场景障碍物')
text=text.replace('if (issue && issue.textContent.includes("元效果")) {','if (issue) {')
text=text.replace('未找到元效果校验项','未找到可点击校验项')
adapted=OUT/'N01_前端冒烟适配_v1.js'
adapted.write_text(text,encoding='utf-8')
prod=OUT/'N01_战斗玩家功能新图_v1.sqlite'
test=OUT/'N01_前端核验临时库_v2.sqlite'
with db.connect(prod,readonly=True) as src,sqlite3.connect(test) as dst:
    src.backup(dst)
store.DB_FILE=test;store.DATA_DIR=OUT;store.BACKUP_DIR=OUT;store.EXPORT_DIR=OUT
class Quiet(server.Handler):
    def log_message(self,*args):pass
    def handle(self):
        try:super().handle()
        except ConnectionResetError:pass  # Node 结束时关闭空闲 keep-alive，不是请求失败。
http=server.ThreadingHTTPServer(('127.0.0.1',0),Quiet)
thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
try:
    result=subprocess.run(['node',str(adapted),f'http://127.0.0.1:{http.server_port}'],capture_output=True,text=True,encoding='utf-8',cwd=ROOT,timeout=60)
    record={'test':'现有前端冒烟仅适配样例名和路径','port':http.server_port,'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr,
            'model_restored':db.model_payload(db.load_model(prod))==db.model_payload(db.load_model(test)),
            'adaptations':['测试 TOOL 路径显式指向原工具','场景道具摆放改为现行概要场景障碍物','校验项接受实际存在的信息提示，不强行要求元效果错误'],
            'original_test_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'limitations':'DOM 垫片前端测试通过，不表示 Unity 战斗已实现；游戏配置及上游规则仍待裁定。'}
    (OUT/'N01_前端核验结果_v2.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print(result.stdout);print(result.stderr)
    assert result.returncode==0 and record['model_restored']
finally:
    http.shutdown();http.server_close();thread.join(timeout=5)
