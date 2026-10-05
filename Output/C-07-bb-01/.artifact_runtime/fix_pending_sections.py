# -*- coding: utf-8 -*-
"""C-07-bb-02 收尾：把仍以“研讨增量要点（待拍板）”形态存在的章节改为未决问题登记。

用法：
    python Dsh/Output/C-07-bb-01/.artifact_runtime/fix_pending_sections.py           # 预览
    python Dsh/Output/C-07-bb-01/.artifact_runtime/fix_pending_sections.py --apply   # 写入

决策 46 要求设计正文只承载已敲定内容。建议稿条目若确实仍是开放问题，应保留为
“未敲定问题”的登记形态，不保留“待拍板建议”的框架。本脚本只改写章节标题与条目
措辞，并把这批改写并入文件当日的既有变更记录行；不改写其他内容。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'Tool', '缺口决策系统', '建库工具'))
from db_locator import to_abs  # noqa: E402

APPLY = '--apply' in sys.argv

HEAD_OLD = '## 3 研讨增量要点（待拍板）'
HEAD_NEW = '## 3 未敲定问题（待设计）'

EDITS = [
    ('01-通用系统/40-角色与小队/40_角色与小队设计_v1.md',
     '- B01 战斗研讨 3.1：装备格总表（角色 × 部位 × 数量）与本系统的角色定义直接相关，需与 06-60 联合产出；\n- C02 总监指令：队友获取途径（事件招募 / 线索树解锁）必须有人认领——本系统认领。',
     '- 装备格总表的角色侧输入未定义：角色专长与装备槽的对应关系需要本系统与 06-60 联合产出（来源：06-60 §2、09-10 §2 台账）；\n- 队友获取途径及其与线索树人物节点的对应方式未定义：事件招募 / 线索树解锁 / 其他三条路径的选择与获取、失去规则需要确定（来源：C02 总监指令）。'),
    ('09-数值与配置/10-数值模型/10_数值模型设计_v1.md',
     '- B01 评价书 P0-1：窗口期松紧、持续时间、错过后果可见度的参数空间需用纸面原型验证"机会成本"体感是否成立；\n- B01 评价书 3.2：趣味矩阵参数敏感（窗口太松无张力、太紧变惩罚）。',
     '- 窗口期松紧、持续时间与错过后果可见度的参数空间未定：需要用纸面原型验证"机会成本"体感是否成立，参数空间与验证方式由数值侧与 02 域共同给出（来源：02 域问题汇总排除说明）；\n- 趣味矩阵的参数敏感度未定：窗口太松无张力、太紧变惩罚，需要一组可校验的参数区间（来源：创意文档 §12 随机性与难度体系）。'),
    ('03-世界结构与结局/20-大关与结局体系/20_大关与结局体系设计_v1.md',
     '- B01 评价书 4.4⑤："隐藏关底对常规游玩体验几乎没有影响"与"主线分支内容"并置略反直觉，建议明确其为"世界观补完内容"而非"主线内容"。',
     '- 隐藏关底的定位措辞待修订："对常规游玩体验几乎没有影响"与"主线分支内容"并置容易误读，需要统一为世界观补完内容的表述（来源：创意文档 §6.2 的定位表述）。'),
    ('09-数值与配置/30-难度体系/30_难度体系设计_v1.md',
     '- B01 评价书 3.2：趣味矩阵参数敏感——窗口太松无张力、太紧变惩罚，难度体系必须与窗口期参数联动校验；\n- C02 总监指令：通关后挑战等级、类似杀戮尖塔进阶的模式需立项。',
     '- 难度与窗口期参数的联动校验标准未定义：窗口太松无张力、太紧变惩罚，需要一组联动校验口径（来源：09-10 §2 台账、02 域窗口期数值项）；\n- 通关后挑战等级的立项未完成：解锁条件、每级变化维度与上限需要确定（来源：C02 总监指令）。'),
    ('01-通用系统/60-设置与辅助功能/60_设置与辅助功能设计_v1.md',
     '- B01 评价书 4.3①：行动槽表达建议改图标+颜色——颜色方案必须与色盲模式兼容（与 06-50 联调）；',
     '- 行动槽表达的色盲兼容口径未定义：四类动作的图标与颜色包装已由 06-40 定案，本系统需要确定颜色方案必须通过哪些色盲兼容检查（来源：06-40 §3.2、C-06-bb-02 回答 CBT-GAP-029）。'),
]

MERGE_NOTE = '另按决策 46 把第 3 节的“研讨增量要点（待拍板）”改为未决问题登记（只留缺什么，不留建议框架）。'


def main():
    changed = 0
    for rel, old, new in EDITS:
        path = to_abs('Dsh/Design/' + rel)
        if not os.path.isfile(path):
            print('MISS 文件缺失 %s' % rel)
            continue
        text = io.open(path, encoding='utf-8').read()
        n_head = text.count(HEAD_OLD)
        n_body = text.count(old)
        if n_head != 1 or n_body != 1:
            print('MISS %s 标题命中 %d 正文命中 %d' % (rel, n_head, n_body))
            continue
        text = text.replace(HEAD_OLD, HEAD_NEW).replace(old, new)
        # 把说明并入当日既有变更记录行；没有当日行时新增一行
        line = '| v1.9 | 2026-09-26 | 全域剔除建议稿独有内容'
        if '2026-09-26' in text and '| 2026-09-26 |' in text:
            idx = text.find('| 2026-09-26 |')
            start = text.rfind('\n', 0, idx) + 1
            end = text.find('\n', idx)
            row = text[start:end]
            if MERGE_NOTE not in row:
                text = text[:end] + '；' + MERGE_NOTE + text[end:]
        else:
            text = text.rstrip('\n') + '\n| v2 | 2026-09-26 | %s | C-07-bb-02 |\n' % MERGE_NOTE
        changed += 1
        if APPLY:
            io.open(path, 'w', encoding='utf-8', newline='\n').write(text)
    print('改写 %d 份；模式：%s' % (changed, '写入' if APPLY else '预览'))


if __name__ == '__main__':
    main()
