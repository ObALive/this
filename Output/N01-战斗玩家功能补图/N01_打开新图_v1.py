"""复用原工具打开 N01 独立库，并把默认导出限制在本任务目录。"""
from pathlib import Path
import sys, os

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT/'Tool/项目网络图'))
import store, server

database = Path(os.environ.get('PN_DB') or OUT/'N01_战斗玩家功能新图_v1.sqlite').resolve()
if database.parent != OUT or not database.exists():
    raise SystemExit('PN_DB 必须是本任务目录内已经存在的副本库。')
store.DB_FILE = database
store.DATA_DIR = OUT
store.BACKUP_DIR = OUT
store.EXPORT_DIR = OUT
if __name__ == '__main__':
    raise SystemExit(server.main())
