"""临时探针：只读查询两份既有决策库的归档状态，用于本次缺口分析取证。"""
import sqlite3

DBS = [
    r"Dsh/Output/C-06-bb-01/C-06-bb-01_战斗系统缺口决策库_v1.sqlite",
    r"Dsh/Output/C-07-bb-01/C-07-bb-01_线索树与元进度缺口决策库_v1.sqlite",
]

for p in DBS:
    con = sqlite3.connect(p)
    cur = con.cursor()
    print("==", p)
    print("gaps:", cur.execute("select count(*) from gaps").fetchone()[0],
          "archived:", cur.execute("select count(*) from gaps_archived").fetchone()[0])
    cols = [d[1] for d in cur.execute("pragma table_info(gaps_archived)").fetchall()]
    print("archived cols:", cols)
    for r in cur.execute(
        "select gap_id, substr(title,1,60), decision_status, landed_at from gaps_archived "
        "order by gap_id"
    ).fetchall():
        print(" |".join(str(x).replace("\n", " ")[:70] for x in r))
    con.close()
    print()
