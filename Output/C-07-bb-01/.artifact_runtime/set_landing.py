# -*- coding: utf-8 -*-
"""通用工具：按映射回填归档表的设计落点，并按同一份映射重新导出回答归档文档。

用法：
    python Dsh/Output/C-07-bb-01/.artifact_runtime/set_landing.py <映射脚本>

映射脚本需要提供 LANDING = {gap_id: 落点文本} 与可选的 ARCHIVE_DOC。
本脚本用于修正在归档时被工具写入关闭条件的历史记录，也用于后续轮次登记真实落点。
"""
import io
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'Tool', '缺口决策系统', '建库工具'))
from db_locator import to_abs  # noqa: E402

DB = 'Dsh/Output/C-07-bb-01/C-07-bb-01_线索树与元进度缺口决策库_v1.sqlite'


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    ns = {}
    exec(io.open(sys.argv[1], encoding='utf-8').read(), ns)
    landing = ns['LANDING']
    conn = sqlite3.connect(to_abs(DB))
    cur = conn.cursor()
    rows = dict(cur.execute('SELECT gap_id, landed_at FROM gaps_archived'))
    changed = 0
    for gap_id, value in sorted(landing.items()):
        if gap_id not in rows:
            print('跳过（不在归档表）%s' % gap_id)
            continue
        if rows[gap_id] != value:
            cur.execute('UPDATE gaps_archived SET landed_at=? WHERE gap_id=?', (value, gap_id))
            changed += 1
    conn.commit()
    total = cur.execute('SELECT COUNT(*) FROM gaps_archived').fetchone()[0]
    conn.close()
    print('归档表共 %d 项，本次改写 %d 项' % (total, changed))


if __name__ == '__main__':
    main()
