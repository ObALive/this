"""打开依赖清理成果；默认导出限定在 N01 目录。"""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/'Tool/项目网络图'))
import store,server
store.DB_FILE=OUT/'N01_依赖清理新图_v1.sqlite'
assert store.DB_FILE.exists(),'请先生成依赖清理成果'
store.DATA_DIR=OUT;store.BACKUP_DIR=OUT;store.EXPORT_DIR=OUT
if __name__=='__main__':raise SystemExit(server.main())
