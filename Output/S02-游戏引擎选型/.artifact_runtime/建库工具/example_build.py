# -*- coding: utf-8 -*-
"""决策库模板的使用示例：从零建立一个小型决策库并自检。

用途：
    1. 演示 decision_db 的最小调用方式，可直接复制到新章节的建库脚本里；
    2. 作为模板的回归测试，随时可用 python example_build.py 运行。

产物：Dsh/Tool/缺口决策系统/示例/example_decision_db.sqlite，
      仅用于演示，运行结束后自动删除。
"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from decision_db import (  # noqa: E402
    GapRecord, OptionRecord, build_decision_db, ensure_archive_table, ensure_meta,
    verify_decision_db)

EXAMPLE_DIR = os.path.abspath(os.path.join(HERE, "..", "示例"))
EXAMPLE_DB = os.path.join(EXAMPLE_DIR, "example_decision_db.sqlite")


def main():
    summary = build_decision_db(
        path=EXAMPLE_DB,
        meta={
            "title": "示例决策库",
            "chapter": "示例章节",
            "domain": "示例域",
            "analysis_doc": "示例信息缺口分析文档路径",
            "created_at": "2026-09-25",
            "created_by": "example_build.py",
        },
        gaps=[
            GapRecord(
                gap_id="EXAMPLE-GAP-001",
                title="示例缺口：某项前置决断尚未作出，影响后续规则写法",
                level="B0",
                source_ref="示例来源文档 §1.1",
                impact_scope="示例系统 A、示例系统 B",
                close_condition="作出裁定并写入正文",
                owner="游戏总监",
                priority_round="第一轮 骨架，EXAMPLE-Q-001",
            ),
            GapRecord(
                gap_id="EXAMPLE-GAP-002",
                title="示例缺口：另一项局部规则尚未定义",
                level="B1",
                source_ref="示例来源文档 §2.3",
                impact_scope="示例系统 C",
                close_condition="定义该规则",
                owner="主策划",
            ),
        ],
        options={
            "EXAMPLE-GAP-001": [
                OptionRecord("A", "候选 A：保留现状", "说明保留现状时的完整规则写法。",
                             "代价与影响说明。", True),
                OptionRecord("B", "候选 B：改为另一套规则",
                             "说明改为另一套规则时的完整规则写法。", "代价与影响说明。"),
                OptionRecord("C", "候选 C：拆成两条规则",
                             "说明拆成两条规则时的完整规则写法。", "代价与影响说明。"),
            ],
            "EXAMPLE-GAP-002": [
                OptionRecord("A", "候选 A：按甲方案定义", "甲方案正文。", "代价说明。"),
                OptionRecord("B", "候选 B：按乙方案定义", "乙方案正文。", "代价说明。", True),
            ],
        },
    )
    print(json.dumps(summary, ensure_ascii=False, indent=1))

    # 演示归档表与 meta 表的补建能力
    ensure_archive_table(EXAMPLE_DB)
    added = ensure_meta(EXAMPLE_DB, {"note": "补建 meta 表演示"})
    print("\n补建能力可用，meta 行数：", added)
    print("归档表校验：", verify_decision_db(EXAMPLE_DB)["archived"], "行")

    shutil.rmtree(EXAMPLE_DIR, ignore_errors=True)
    print("示例目录已清理：", not os.path.exists(EXAMPLE_DIR))


if __name__ == "__main__":
    main()
