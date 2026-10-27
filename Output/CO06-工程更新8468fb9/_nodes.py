import sqlite3

p = r'Tool/项目网络图/数据/N01_完整依赖清理新图_v2.sqlite'
conn = sqlite3.connect('file:' + p + '?mode=ro', uri=True)
conn.row_factory = sqlite3.Row

ids = [r['id'] for r in conn.execute("SELECT id FROM nodes WHERE status='已实现' ORDER BY seq")]
for nid in ids:
    n = conn.execute("""SELECT n.*, v.index_label, v.section_path FROM nodes n
                        JOIN v_node v ON v.id=n.id WHERE n.id=?""", (nid,)).fetchone()
    print('=' * 90)
    print('NODE %s | %s | number=%s | summary=%s' % (n['id'], n['section_path'], n['number'], n['summary']))
    print('--- body ---')
    print(n['body'])
    objs = conn.execute("SELECT seq,name,note,path FROM node_objects WHERE node_id=? ORDER BY seq", (nid,)).fetchall()
    if objs:
        print('--- objects (%d) ---' % len(objs))
        for o in objs:
            print('  [%s] %s' % (o['seq'], o['name']))
            print('      note: %s' % (o['note'] or ''))
            print('      path: %s' % (o['path'] or ''))
    notes = conn.execute("SELECT seq,text FROM node_notes WHERE node_id=? ORDER BY seq", (nid,)).fetchall()
    if notes:
        print('--- notes (%d) ---' % len(notes))
        for o in notes:
            print('  [%s] %s' % (o['seq'], o['text']))
    refs = conn.execute("""SELECT r.seq,r.raw,r.section,r.number,r.target_id,r.reason FROM node_refs r
                           WHERE r.node_id=? ORDER BY r.seq""", (nid,)).fetchall()
    if refs:
        print('--- refs (%d) ---' % len(refs))
        for o in refs:
            tgt = ''
            if o['target_id']:
                t = conn.execute('SELECT index_label, summary FROM v_node WHERE id=?', (o['target_id'],)).fetchone()
                tgt = '-> %s %s' % (t['index_label'], t['summary']) if t else '-> ?'
            else:
                tgt = 'UNRESOLVED (%s)' % (o['reason'] or '')
            print('  [%s] %-24s %s' % (o['seq'], o['raw'], tgt))
    # downstream
    down = conn.execute("""SELECT v.index_label, v.summary FROM v_edge e JOIN v_node v ON v.id=e.from_id
                           WHERE e.to_id=? """, (nid,)).fetchall()
    if down:
        print('--- depended on by (%d) ---' % len(down))
        for o in down:
            print('  %s %s' % (o['index_label'], o['summary']))
conn.close()
