# -*- coding: utf-8 -*-
"""从结构化数据文件建库：把本任务的缺口与候选写成一个决策库。

用法：
  python build_decision_db.py --data <数据文件.json>
  python build_decision_db.py --data <数据文件.json> --db <输出库路径> --force

数据文件格式（JSON，UTF-8）：
  {
    "meta": {
      "title": "C-aa-bb-01 某系统缺口决策库",
      "chapter": "C-aa-bb-01",
      "domain": "某系统域",
      "analysis_doc": "Dsh/Output/C-aa-bb-01/C-aa-bb-01_某系统信息缺口分析_v1.md",
      "created_at": "2026-09-25"
    },
    "db_path": "Dsh/Output/C-aa-bb-01/C-aa-bb-01_某系统缺口决策库_v1.sqlite",
    "gaps": [
      {
        "gap_id": "XXX-GAP-001",
        "title": "缺口陈述，一句话说清缺什么、影响什么",
        "level": "B0",
        "source_ref": "来源文档与章节",
        "impact_scope": "受影响系统编号清单",
        "close_condition": "关闭条件",
        "owner": "游戏总监",
        "priority_round": "第一轮 骨架，XXX-Q-001",
        "options": [
          {"label": "A", "title": "候选 A：短标题",
           "detail": "方案正文：规则是什么、适用范围、状态变化、与既有系统的衔接",
           "tradeoff": "代价与影响", "recommended": true},
          {"label": "B", "title": "候选 B：短标题", "detail": "方案正文", "tradeoff": "代价与影响"},
          {"label": "C", "title": "候选 C：短标题", "detail": "方案正文", "tradeoff": "代价与影响"}
        ]
      }
    ]
  }

约束（建库后会自动校验，不满足时在输出中列出问题）：
  每项缺口 2 至 3 条候选，至多一条标记 recommended；
  建库时自动为每项缺口追加一条自定义预留行，使填写器始终呈现候选加自定义输入框。
"""
import argparse
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_locator import resolve_db, to_abs, to_rel  # noqa: E402
from decision_db import GapRecord, OptionRecord, build_decision_db  # noqa: E402


def load_data(path):
    data = json.load(io.open(path, encoding="utf-8"))
    if "gaps" not in data or not data["gaps"]:
        raise SystemExit("数据文件缺少 gaps 列表：%s" % path)
    return data


def to_records(data):
    gaps, options = [], {}
    for item in data["gaps"]:
        gaps.append(GapRecord(
            gap_id=item["gap_id"],
            title=item["title"],
            level=item.get("level", "B1"),
            status=item.get("status", "待裁定"),
            source_ref=item.get("source_ref", ""),
            impact_scope=item.get("impact_scope", ""),
            close_condition=item.get("close_condition", ""),
            owner=item.get("owner", "主策划"),
            priority_round=item.get("priority_round"),
        ))
        options[item["gap_id"]] = [
            OptionRecord(o["label"], o["title"], o["detail"], o["tradeoff"],
                         bool(o.get("recommended")))
            for o in item.get("options", [])
        ]
    return gaps, options


def main():
    parser = argparse.ArgumentParser(description="从数据文件建立决策库")
    parser.add_argument("--data", required=True, help="结构化数据文件（JSON）")
    parser.add_argument("--db", help="输出库路径，缺省时取数据文件中的 db_path")
    parser.add_argument("--force", action="store_true",
                        help="目标库已存在时覆盖（默认保留旧库并报错）")
    args = parser.parse_args()

    data = load_data(args.data)
    db_rel = args.db or data.get("db_path")
    if not db_rel:
        raise SystemExit("未指定输出库路径：请用 --db 或在数据文件中提供 db_path")
    db_path = to_abs(db_rel) if not os.path.isabs(db_rel) else db_rel

    if os.path.exists(db_path) and not args.force:
        raise SystemExit(
            "目标库已存在：%s\n按库内版本规则，请另存新版本（例如 _v2.sqlite）后重试，"
            "确认确实要覆盖时加 --force" % to_rel(db_path))

    meta = dict(data.get("meta", {}))
    meta.setdefault("created_by", "build_decision_db.py")
    gaps, options = to_records(data)

    summary = build_decision_db(db_path, meta, gaps, options)
    summary["path"] = to_rel(db_path)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    if summary.get("problems"):
        print("\n建库完成，但存在需要修正的问题，见上面的 problems 字段。")
    else:
        print("\n建库完成，校验项全部通过。可按建库说明文档的下一步启动填写器。")


if __name__ == "__main__":
    main()
