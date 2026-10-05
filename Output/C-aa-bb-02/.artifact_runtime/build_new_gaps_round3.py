# -*- coding: utf-8 -*-
"""为 C-aa-bb-01 决策库构造第三轮缺口数据（XDM-GAP-021 起）。"""
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, "..", "C-aa-bb-02_新缺口数据_v2.json"))

DATA = {
    "meta": {
        "title": "C-aa-bb-01 跨域遗留问题决策库 第三轮缺口",
        "chapter": "C-aa-bb-02",
        "domain": "01-07 全域跨域移交与零散遗留问题",
        "analysis_doc": "Dsh/Output/C-aa-bb-02/C-aa-bb-02_新问题清单_v2.md",
        "created_at": "2026-09-27",
    },
    "gaps": [],
}


def gap(gap_id, title, level, status, source_ref, impact_scope, close_condition,
        owner, priority_round, options=None):
    return {
        "gap_id": gap_id, "title": title, "level": level, "status": status,
        "source_ref": source_ref, "impact_scope": impact_scope,
        "close_condition": close_condition, "owner": owner,
        "priority_round": priority_round, "options": options or [],
    }


def opt(label, title, detail, tradeoff, recommended=False):
    return {"label": label, "title": title, "detail": detail,
            "tradeoff": tradeoff, "recommended": recommended}


DATA["gaps"].append(gap(
    "XDM-GAP-021",
    "未通关结局三种收尾情形在达成记录中的落点未定：结局类型已合并为一种，但三种情形各需一段说明文案与一条记录，落点字段没有规则",
    "B1", "待裁定",
    "C-aa-bb-02 第二轮回答 XDM-GAP-019；07-线索树与元进度/40-局末结算与写入/40_局末结算与写入设计_v2.5.md 的 3.7 与 3.13；01-通用系统/20-信息传递系统/20_信息传递系统设计_v2.5.md 的 3.4 待设计清单",
    "07-40 局末结算与写入、01-20 信息传递系统、06-A0 战斗目标与结果、02-30 事件系统、01-50 存档与持久化",
    "定义三种收尾情形在达成记录中的字段落点与文案承载方式",
    "主策划", "第三轮 收尾澄清",
    [
        opt("A", "候选 A：达成记录增设触发起因项，取枚举值",
            "达成记录的未通关结局条目增设一项触发起因，取值为关底未达标、主线中断与全队失去行动能力三者之一，由判定方在结局成立时写入。结算界面按该取值取对应的说明文案，统计信息可以直接按该字段分组。",
            "三种情形在数据上可区分，文案与统计都有稳定依据，后续补做复盘功能时不需要再改结构。代价是达成记录增加一项字段，结算组件需要按判定来源写入该字段。",
            recommended=True),
        opt("B", "候选 B：复用失败环节字段承载触发起因",
            "不新增字段，把三种情形写入既有的失败环节字段，字段取值沿用关底未达标、主线中断与全队失去行动能力的表述，结算界面按取值选择文案。",
            "字段数量不变，与既有的失败环节概念连续。代价是失败一词与合并后的未通关语义不完全吻合，字段命名需要一并调整，否则后续读库时容易把合并后的结局当成失败结局。"),
        opt("C", "候选 C：不加区分，只记录未通关结局与时间",
            "达成记录只记录未通关结局与达成时间，不区分三种情形；说明文案按结局类型统一撰写一段，不按情形分别撰写。",
            "写入项最少，结算组件不需要读取判定来源，文案只需一段。代价是三种情形在叙事上的差异无法呈现，玩家在局末无法分辨本局是因为主线中断还是因为全队失去行动能力而收尾。"),
    ]))

with io.open(OUT, "w", encoding="utf-8") as fh:
    json.dump(DATA, fh, ensure_ascii=False, indent=2)

print("写出第三轮缺口数据：%s" % OUT)
for g in DATA["gaps"]:
    print("  %s %s %s 候选 %d" % (g["gap_id"], g["level"], g["status"], len(g["options"])))
