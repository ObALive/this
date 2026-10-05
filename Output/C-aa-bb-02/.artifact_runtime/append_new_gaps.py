# -*- coding: utf-8 -*-
"""把某一轮的新缺口数据追加进 C-aa-bb-01 决策库。

用法：
  python append_new_gaps.py <数据文件.json>

追加语义：编号不得与主表或归档表重复，重复编号会被拒绝；
不重建库、不影响既有归档数据。
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Dsh", "Tool", "缺口决策系统", "建库工具"))

from decision_db import GapRecord, OptionRecord, append_decision_db  # noqa: E402

if len(sys.argv) < 2:
    raise SystemExit("请提供缺口数据文件路径")
DATA_PATH = os.path.abspath(sys.argv[1])

DATA = json.load(io.open(DATA_PATH, encoding="utf-8"))
DB = os.path.join(ROOT, "Dsh", "Output", "C-aa-bb-01",
                  "C-aa-bb-01_跨域遗留问题决策库_v1.sqlite")

gaps, options = [], {}
for item in DATA["gaps"]:
    gaps.append(GapRecord(
        gap_id=item["gap_id"], title=item["title"], level=item["level"],
        status=item["status"], source_ref=item["source_ref"],
        impact_scope=item["impact_scope"], close_condition=item["close_condition"],
        owner=item["owner"], priority_round=item["priority_round"]))
    options[item["gap_id"]] = [
        OptionRecord(o["label"], o["title"], o["detail"], o["tradeoff"],
                     bool(o.get("recommended")))
        for o in item["options"]]

summary = append_decision_db(
    path=DB, gaps=gaps, options=options,
    analysis_doc="Dsh/Output/C-aa-bb-02/C-aa-bb-02_新问题清单_v2.md")

print(json.dumps(summary, ensure_ascii=False, indent=1))
