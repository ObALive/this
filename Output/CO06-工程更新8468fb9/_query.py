import sqlite3, sys

p = r'Tool/项目网络图/数据/N01_完整依赖清理新图_v2.sqlite'
conn = sqlite3.connect('file:' + p + '?mode=ro', uri=True)
conn.row_factory = sqlite3.Row

print('=== implemented ===')
q = """SELECT n.id, n.seq, n.status, v.index_label, v.summary, v.section_path
       FROM nodes n JOIN v_node v ON v.id=n.id WHERE n.status='已实现' ORDER BY n.seq"""
for r in conn.execute(q):
    print('%-5s seq=%-4s %s :: %s' % (r['id'], r['seq'], r['section_path'], r['summary']))

print()
print('=== counts ===')
for r in conn.execute('SELECT status, COUNT(*) c FROM nodes GROUP BY status'):
    print(r['status'], r['c'])

print()
print('=== sections ===')
for r in conn.execute('SELECT id, seq, title, level, parent_id, start_number FROM sections ORDER BY seq'):
    print('%-4s seq=%-4s L%s parent=%-4s n=%s | %s' % (r['id'], r['seq'], r['level'], r['parent_id'], r['start_number'], r['title']))
conn.close()
