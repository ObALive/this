# -*- coding: utf-8 -*-
"""回填 C-07-bb-01 决策库归档表的设计落点，并重新导出回答归档文档。

用法：
    python Dsh/Output/C-07-bb-01/.artifact_runtime/fix_archive_landing.py           # 预览
    python Dsh/Output/C-07-bb-01/.artifact_runtime/fix_archive_landing.py --apply   # 写入

背景：归档工具原先把缺口的关闭条件写入 gaps_archived.landed_at，该字段的语义是
“结论落到哪份文档”，与关闭条件不是一回事。本脚本把 landed_at 改写为本轮实际的
设计落点，并按同一份映射重新生成 `C-07-bb-02_回答归档_v1.md`。
"""
import io
import sqlite3
import sys

sys.path.insert(0, __file__.rsplit('\\', 1)[0])
import os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'Tool', '缺口决策系统', '建库工具'))
from db_locator import to_abs  # noqa: E402

APPLY = '--apply' in sys.argv
DB = 'Dsh/Output/C-07-bb-01/C-07-bb-01_线索树与元进度缺口决策库_v1.sqlite'
ARCHIVE_DOC = 'Dsh/Output/C-07-bb-01/C-07-bb-02_回答归档_v1.md'

LANDING = {
    'MET-GAP-001': '07-10 §3.1、§3.2；新建 10_节点类型表_v1.csv、10_节点关系表_v1.csv；术语表新增节点类型、节点关系、上游节点；交互逻辑 63；决策 39',
    'MET-GAP-002': '07-10 §3.5；07-20 §3.1；术语表新增锁定节点、开放阈值；交互逻辑 63；决策 39',
    'MET-GAP-003': '07-10 §3.4；07-40 §3.5、§3.6；术语表新增传闻、传闻表；决策 40',
    'MET-GAP-004': '07-10 §3.5（界面框架归属）；07-40 §3.3（结算界面列入后续版本）',
    'MET-GAP-005': '07-10 §3.2（节点加边读图）、§3.4（空行占位）、§4（读图规则）',
    'MET-GAP-006': '07-10 §3.3、§3.4；07-40 §3.6；新建 10_传闻表_v1.csv；03-30 §5；决策 40',
    'MET-GAP-007': '07-10 §3.3；01-20 §3.2、§4；交互逻辑 48 补充口径；决策 40',
    'MET-GAP-008': '07-10 §3.3；新建 10_传闻表_v1.csv；术语表新增传闻；决策 40',
    'MET-GAP-009': '07-10 §1（功能边界）；交互逻辑 59；决策 41',
    'MET-GAP-010': '07-10 §3.8；01-10 §3.7；02-40 §4.2；02-20 §4.3；术语表新增信息揭露列表',
    'MET-GAP-011': '07-10 §3.9；07-40 §3.1；交互逻辑 13 口径延续',
    'MET-GAP-012': '07-10 §3.6；02-30-10 §4.4；术语表新增锁定节点、开放阈值；交互逻辑 63',
    'MET-GAP-013': '07-10 §3.6；07-20 §3.1；术语表新增上游节点',
    'MET-GAP-014': '07-20 §3.2；07-10 §3.5（封锁标注）；交互逻辑 5 口径延续',
    'MET-GAP-015': '07-20 §3.3、§3.5、§3.7；07-20 §3.4；交互逻辑 5 口径延续',
    'MET-GAP-016': '07-20 §3.3；09-20 §4.1 输入契约；01-50 §4 跨局数据',
    'MET-GAP-017': '07-20 §3.4；01-20 §4 文本库口径延续',
    'MET-GAP-018': '07-10 §3.8；01-10 §3.7；02-20 §4.3；交互逻辑 20 修订',
    'MET-GAP-019': '07-20 §3.5；交互逻辑第五节建议 2 标记为已裁定挂起；术语表已移除术语新增剪枝预览面板',
    'MET-GAP-020': '07-20 §3.2；07-10 §3.6；03-20 §5；术语表无新增',
    'MET-GAP-021': '07-20 §3.6；09-20 §3 保留待拍板登记',
    'MET-GAP-022': '07-30 §3.1；新建 30_概率池表_v1.csv；术语表新增概率池表；交互逻辑 59；决策 42',
    'MET-GAP-023': '07-30 §3.2、§3.3；02-30 §4.8；术语表新增全局事件池、当前事件池；交互逻辑 60；决策 43',
    'MET-GAP-024': '07-30 §3.6；交互逻辑 62；决策 44',
    'MET-GAP-025': '07-30 §3.8；交互逻辑 61；术语表已移除术语新增概率池可视化；决策 44',
    'MET-GAP-026': '07-30 §3.5；09-30 §4.1；09 索引第三节',
    'MET-GAP-027': '07-30 §3.4；02-40 §4.1；交互逻辑 60；决策 43',
    'MET-GAP-028': '07-30 §3.7；09-20 §4.1；09 索引第三节',
    'MET-GAP-029': '07-40 §3.1；决策 45；交互逻辑 29 口径延续',
    'MET-GAP-030': '07-40 §3.4、§3.11；决策 45；01-50 §6 口径延续',
    'MET-GAP-031': '07-40 §3.3；决策 45；07-10 §3.10；后续澄清见 MET-GAP-047',
    'MET-GAP-032': '07-40 §3.6；07-10 §3.4；03-30 §5；决策 40',
    'MET-GAP-033': '07-40 §3.11（同节点按内容标识去重）；后续澄清见 MET-GAP-058',
    'MET-GAP-034': '07-40 §3.4、§3.7；决策 45',
    'MET-GAP-035': '07-40 §3.7；03-20 §5；决策 45',
    'MET-GAP-036': '07-40 §3.9；决策 45；后续澄清见 MET-GAP-048',
    'MET-GAP-037': '07-40 §3.8；03-20 §5；决策 45',
    'MET-GAP-038': '07-40 §3.5；01-50 §2 口径延续；后续澄清见 MET-GAP-058',
    'MET-GAP-039': '07-40 §3.3（结算界面列入后续版本）',
    'MET-GAP-040': '07-40 §3.3；交互逻辑第五节；各系统文档研讨增量要点节的剔除；决策 46；剔除明细见 C-07-bb-02_建议稿剔除清单_v1.md',
    'MET-GAP-041': '07-40 §3.3（世界线结算叙事卡片挂起）；03-10 §4.1',
    'MET-GAP-042': '07-10 §4；术语表第三节；交互逻辑无新增；决策记录无新增',
    'MET-GAP-043': '07-40 §3.10；02-30 §4.4 口径延续',
    'MET-GAP-044': '07-10 §3.8；02-20 §4.3；01-10 §3.7；交互逻辑 20 修订',
    'MET-GAP-045': '07-20 §3.3；01-50 §4 口径延续',
    'MET-GAP-046': '07-10 §3.8；01-10 §3.7；交互逻辑 20 修订',
}


def main():
    db_path = to_abs(DB)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    rows = list(cur.execute('SELECT gap_id, landed_at FROM gaps_archived ORDER BY gap_id'))
    # 第一轮 46 项按 LANDING 改写；其余轮次沿用库内已有的落点（由 set_landing.py 登记）
    extra = {g: v for g, v in rows if g not in LANDING}
    changed = 0
    for gap_id, old in rows:
        if gap_id not in LANDING:
            continue
        new = LANDING[gap_id]
        if old != new:
            changed += 1
            if APPLY:
                cur.execute('UPDATE gaps_archived SET landed_at=? WHERE gap_id=?', (new, gap_id))
    if APPLY:
        conn.commit()

    # 重新导出回答归档文档
    cur.row_factory = sqlite3.Row
    data = list(cur.execute(
        'SELECT gap_id,title,level,priority_round,owner,decision_status,chosen_label,'
        'chosen_title,answer_text,extra_requirement,conclusion,landed_at'
        ' FROM gaps_archived ORDER BY gap_id'))
    conn.close()

    if APPLY:
        write_archive(data)
    print('落点需要改写 %d 项；模式：%s' % (changed, '写入' if APPLY else '预览'))


def write_archive(data):
    out = [
        '# C-07-bb-02 回答归档（v1）', '',
        '| 项目 | 内容 |',
        '| --- | --- |',
        '| 文档定位 | 汇总 C-07-bb-01 决策库全部已裁定问题的结论、补充要求与设计落点 |',
        '| 归档落点 | `C-07-bb-01_线索树与元进度缺口决策库_v1.sqlite` 的 gaps_archived 表 |',
        '| 设计落点 | `Dsh/Design/07-线索树与元进度/` 四份正文与四张扩展配置表，跨域同步见各系统变更记录 |',
        '| 构成 | 第一轮 46 项（MET-GAP-001 至 046）、第二轮 12 项（MET-GAP-047 至 058）、第三轮 4 项（MET-GAP-059 至 062） |',
        '| 主表状态 | 归档 62 项，主表无待裁定项 |',
        '| 后续问题 | `C-07-bb-02_新问题清单_v1.md`（12 项，编号 MET-GAP-047 起） |',
        '| 归档人 | C-07-bb-02 |',
        '| 归档日期 | 2026-09-26 |', '',
        '共 %d 项，全部已裁定。其中采用候选 %d 项，自定义方案 %d 项。'
        % (len(data),
           sum(1 for r in data if r['decision_status'] == '已选候选'),
           sum(1 for r in data if r['decision_status'] == '自定义方案')),
        '', '---', '', '## 一、归档明细', '',
        '| 编号 | 原问题 | 等级 | 裁定方式 | 结论摘要 | 设计落点 |',
        '| --- | --- | --- | --- | --- | --- |',
    ]
    for r in data:
        if r['chosen_title']:
            concl = r['chosen_title'].replace('候选 %s：' % r['chosen_label'], '')
            basis = '候选 %s' % r['chosen_label']
        else:
            concl = (r['answer_text'] or '').replace('\n', ' ')
            basis = '自定义方案'
        extra = (r['extra_requirement'] or '').replace('\n', ' ')
        if extra:
            concl = concl + '；补充要求：' + extra
        out.append('| %s | %s | %s | %s | %s | %s |'
                   % (r['gap_id'], r['title'], r['level'], basis, concl, r['landed_at']))
    out += ['', '## 二、变更记录', '',
            '| 版本 | 日期 | 变更 | 依据任务 |',
            '| --- | --- | --- | --- |',
            '| v1 | 2026-09-26 | 归档第一轮 46 项并登记设计落点 | C-07-bb-02 |',
            '| v2 | 2026-09-26 | 补充第二轮 12 项（MET-GAP-047 至 058）的结论与设计落点 | C-07-bb-02（第二轮） |',
            '| v3 | 2026-09-26 | 补充第三轮 4 项（MET-GAP-059 至 062）的结论与设计落点，库内归档共 62 项，主表清零 | C-07-bb-02（第三轮） |', '']
    io.open(to_abs(ARCHIVE_DOC), 'w', encoding='utf-8', newline='\n').write('\n'.join(out))


if __name__ == '__main__':
    main()
