# -*- coding: utf-8 -*-
"""C-07-bb-02 收口检查的引用与口径校验（不依赖第三轮裁定）。

用法：
    python Dsh/Output/C-07-bb-01/.artifact_runtime/verify_closeout.py

检查项：
  1. 全库现行设计文档中指向设计文档与配置表的引用是否存在；
  2. 07 域四份正文引用其他文档章节号时，被引章节是否存在；
  3. 07 域四份正文的章节编号是否连续、内部交叉引用是否指向存在的章节；
  4. 四张扩展配置表的表头列是否在正文中有对应说明；
  5. 决策库主表是否只保留待裁定项、归档记录是否有落点。
"""
import io
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'Tool', '缺口决策系统', '建库工具'))
from db_locator import WORKSPACE, to_abs, to_rel  # noqa: E402

DESIGN = os.path.join(WORKSPACE, 'Dsh', 'Design')
DOMAIN = os.path.join(DESIGN, '07-线索树与元进度')
DB = 'Dsh/Output/C-07-bb-01/C-07-bb-01_线索树与元进度缺口决策库_v1.sqlite'

DOC_REF = re.compile(r'`([^`]*?(?:\.md|\.csv))`')
SECTION_REF = re.compile(r'([0-9]{2}-[0-9]{2}(?:-[0-9]{2})?)[^\n]{0,40}?§\s?([0-9]+(?:\.[0-9]+)*)')
INTERNAL = re.compile(r'见\s*([0-9]+\.[0-9]+(?:\.[0-9]+)?)')


def read(path):
    return io.open(path, encoding='utf-8').read()


def current_docs():
    """现行文档 = 每个目录内版本号最高的 .md 文件（README 与模板除外）。"""
    best = {}
    for root, _dirs, files in os.walk(DESIGN):
        if '_模板' in root:
            continue
        for name in files:
            if not name.endswith('.md') or name == 'README.md':
                continue
            m = re.search(r'_v([0-9]+(?:\.[0-9]+)?)\.md$', name)
            ver = float(m.group(1)) if m else 0.0
            key = os.path.join(root, re.sub(r'_v[0-9.]+\.md$', '', name))
            if key not in best or best[key][0] < ver:
                best[key] = (ver, os.path.join(root, name))
    return [p for _v, p in best.values()]


BASENAME_INDEX = None


def basename_lookup():
    """按文件名建立索引，用于解析只写文件名的简写引用。"""
    global BASENAME_INDEX
    if BASENAME_INDEX is None:
        BASENAME_INDEX = {}
        for root, _dirs, files in os.walk(DESIGN):
            for name in files:
                if name.endswith(('.md', '.csv')):
                    BASENAME_INDEX.setdefault(name, []).append(os.path.join(root, name))
    return BASENAME_INDEX


def resolve_ref(path, ref):
    """把文档内的引用解析成绝对路径，支持索引相对、同级、域根、Design 根与仅文件名五种写法。"""
    ref = ref.replace('/', os.sep)
    here = os.path.dirname(path)
    domain = os.path.dirname(here)
    roots = [here, os.path.dirname(here), domain, DESIGN, WORKSPACE]
    if ref.endswith('.md') or ref.endswith('.csv'):
        for base in roots:
            cand = os.path.join(base, ref)
            if os.path.exists(cand):
                return cand
        hits = basename_lookup().get(os.path.basename(ref), [])
        if len(hits) == 1:
            return hits[0]
    return None


def check_doc_refs(problems):
    checked = 0
    for path in current_docs():
        text = read(path)
        for ref in {m.group(1) for m in DOC_REF.finditer(text)}:
            if '://' in ref or ref.startswith('Dsh'):
                continue
            # 指向 Output 的过程性文档不在设计库内，跳过
            if ref.startswith('C-') or ref.startswith('A0') and ref.startswith('C-'):
                continue
            if re.match(r'^C-[0-9]', ref) or '/C-' in ref or '\\C-' in ref:
                continue
            checked += 1
            if resolve_ref(path, ref) is None:
                problems.append('引用缺失 %s -> %s' % (to_rel(path).replace('\\', '/'), ref))
    return checked


def section_numbers(path):
    nums = set()
    for line in read(path).split('\n'):
        m = re.match(r'^#{2,4}\s+([0-9]+(?:\.[0-9]+)*)', line)
        if m:
            nums.add(m.group(1))
    return nums


def check_domain_sections(problems):
    docs = {}
    for root, _dirs, files in os.walk(DOMAIN):
        for name in files:
            if name.endswith('.md'):
                docs[name] = os.path.join(root, name)

    # 4.1 章节编号连续
    for name, path in sorted(docs.items()):
        text = read(path)
        tops = [int(m.group(1)) for m in re.finditer(r'^##\s+([0-9]+)\s', text, re.M)]
        if tops:
            expect = list(range(1, len(tops) + 1))
            if sorted(tops) != expect:
                problems.append('%s 顶级章节编号不连续：%s' % (name, tops))

    # 4.2 内部交叉引用
    for name, path in sorted(docs.items()):
        nums = section_numbers(path)
        for m in INTERNAL.finditer(read(path)):
            target = m.group(1)
            if target not in nums and not any(n.startswith(target + '.') for n in nums):
                problems.append('%s 内部引用 见 %s 指向不存在的章节' % (name, target))

    # 4.3 跨文档章节引用
    chapter_index = {}
    for name, path in docs.items():
        chapter_index[name] = section_numbers(path)
    return docs, chapter_index


def check_table_columns(problems):
    for name, doc in (('10_节点类型表_v1.csv', '10_线索树核心设计_v2.md'),
                      ('10_节点关系表_v1.csv', '10_线索树核心设计_v2.md'),
                      ('10_传闻表_v1.csv', '10_线索树核心设计_v2.md'),
                      ('30_概率池表_v1.csv', '30_概率池联动设计_v2.md')):
        table = None
        for root, _dirs, files in os.walk(DOMAIN):
            if name in files:
                table = os.path.join(root, name)
        if not table:
            problems.append('配置表不存在：%s' % name)
            continue
        rows = [r for r in read(table).split('\n') if r.strip()]
        cols = rows[0].split(',')
        if len(cols) < 6:
            problems.append('%s 列数过少：%d' % (name, len(cols)))
        last = rows[-1].split(',')
        if len(last) != len(cols):
            problems.append('%s 待补充行列数与表头不一致：%d vs %d' % (name, len(last), len(cols)))
        if not last[0].endswith('TBD-001'):
            problems.append('%s 末行不是待补充记录：%s' % (name, last[0]))
    return True


def check_db(problems):
    conn = sqlite3.connect(to_abs(DB))
    cur = conn.cursor()
    pending = cur.execute("SELECT g.gap_id, d.status FROM gaps g JOIN decisions d"
                          " ON d.gap_id = g.gap_id WHERE d.status <> '待裁定'").fetchall()
    if pending:
        problems.append('主表存在已裁定的项：%s' % pending)
    no_landing = cur.execute("SELECT COUNT(*) FROM gaps_archived"
                             " WHERE landed_at IS NULL OR TRIM(landed_at) = ''").fetchone()[0]
    if no_landing:
        problems.append('归档表有 %d 项缺少设计落点' % no_landing)
    dup = cur.execute("SELECT COUNT(*) FROM (SELECT gap_id FROM gaps_archived WHERE gap_id IN"
                      " (SELECT gap_id FROM gaps))").fetchone()[0]
    if dup:
        problems.append('归档表与主表编号重复 %d 项' % dup)
    stats = {
        '主表缺口': cur.execute('SELECT COUNT(*) FROM gaps').fetchone()[0],
        '归档': cur.execute('SELECT COUNT(*) FROM gaps_archived').fetchone()[0],
    }
    conn.close()
    return stats


def check_landing(problems):
    """核对归档表里每条设计落点声称的章节是否真的存在于目标文档。

    落点文本形如“07-10 §3.6、§3.7；07-20 §3.4；术语表新增……”，本函数取出
    文档代号与随后的 § 号，逐个核对目标文档是否存在对应章节。
    """
    doc_map = {
        '07-10': '07-线索树与元进度/10-线索树核心/10_线索树核心设计_v2.md',
        '07-20': '07-线索树与元进度/20-剪枝系统/20_剪枝系统设计_v2.md',
        '07-30': '07-线索树与元进度/30-概率池联动/30_概率池联动设计_v2.md',
        '07-40': '07-线索树与元进度/40-局末结算与写入/40_局末结算与写入设计_v2.md',
        '10': '07-线索树与元进度/10-线索树核心/10_线索树核心设计_v2.md',
        '20': '07-线索树与元进度/20-剪枝系统/20_剪枝系统设计_v2.md',
        '30': '07-线索树与元进度/30-概率池联动/30_概率池联动设计_v2.md',
        '40': '07-线索树与元进度/40-局末结算与写入/40_局末结算与写入设计_v2.md',
        '02-20': '02-时间与事件/20-日程系统/20_日程系统设计_v2.md',
        '30-10': '02-时间与事件/30-事件系统/30-10-触发条件/30-10_触发条件设计_v2.md',
        '03-30': '03-世界结构与结局/30-剧情与叙事内容/30_剧情与叙事内容设计_v1.md',
        '03-20': '03-世界结构与结局/20-大关与结局体系/20_大关与结局体系设计_v1.md',
    }
    cache = {}
    checked = 0
    conn = sqlite3.connect(to_abs(DB))
    rows = list(conn.execute('SELECT gap_id, landed_at FROM gaps_archived'))
    conn.close()
    for gap_id, landing in rows:
        if not landing:
            continue
        for m in re.finditer(r'([0-9]{2}(?:-[0-9]{2})?(?:-[0-9]{2})?)\s*(§[0-9][0-9.,、§ ]*)', landing):
            code, section_text = m.group(1), m.group(2)
            path = doc_map.get(code)
            if not path:
                continue
            abs_path = os.path.join(DESIGN, path.replace('/', os.sep))
            if not os.path.exists(abs_path):
                problems.append('%s 落点指向不存在的文档：%s' % (gap_id, code))
                continue
            if abs_path not in cache:
                cache[abs_path] = section_numbers(abs_path)
            nums = cache[abs_path]
            for sec in re.findall(r'[0-9]+(?:\.[0-9]+)*', section_text):
                checked += 1
                if sec not in nums and not any(n.startswith(sec + '.') for n in nums):
                    problems.append('%s 落点声称 %s §%s，该章节不存在' % (gap_id, code, sec))
    return len(rows), checked


def main():
    problems = []
    refs = check_doc_refs(problems)
    _docs, _idx = check_domain_sections(problems)
    check_table_columns(problems)
    stats = check_db(problems)
    archived, landing_checked = check_landing(problems)

    print('检查范围：%d 份现行设计文档，%d 处文档引用' % (len(current_docs()), refs))
    print('决策库：%s；归档落点核对 %d 项、%d 处章节引用'
          % ('，'.join('%s %d' % (k, v) for k, v in stats.items()), archived, landing_checked))
    if problems:
        print('\n发现 %d 处问题：' % len(problems))
        for p in problems:
            print('  - %s' % p)
    else:
        print('\n未发现问题。')


if __name__ == '__main__':
    main()
