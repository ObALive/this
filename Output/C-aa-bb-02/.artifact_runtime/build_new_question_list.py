# -*- coding: utf-8 -*-
"""由新缺口数据文件生成可读的新问题清单。"""
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
DATA = json.load(io.open(os.path.join(HERE, "..", "C-aa-bb-02_新缺口数据_v1.json"),
                         encoding="utf-8"))

lines = [
    "# C-aa-bb-02 新问题清单（v1）", "",
    "| 项目 | 内容 |", "| --- | --- |",
    "| 文档定位 | 记录本轮回填后仍未澄清到可直接实现粒度的问题，每项附候选与推荐 |",
    "| 裁定入口 | `Dsh/Output/C-aa-bb-01/C-aa-bb-01_跨域遗留问题决策库_v1.sqlite`，可用填写器逐项裁定 |",
    "| 问题来源 | C-aa-bb-02 回答中自定义方案引出的新问题面，以及回填过程中发现的规则分叉 |",
    "| 编号规则 | 沿用 XDM-GAP 前缀从 017 起递增，不与已归档的 001 至 016 重复 |",
    "| 更新日期 | 2026-09-27 |", "",
]

for item in DATA["gaps"]:
    lines += [
        "## %s %s" % (item["gap_id"], item["title"]), "",
        "| 字段 | 内容 |", "| --- | --- |",
        "| 等级 | %s |" % item["level"],
        "| 责任方 | %s |" % item["owner"],
        "| 来源 | %s |" % item["source_ref"],
        "| 影响范围 | %s |" % item["impact_scope"],
        "| 关闭条件 | %s |" % item["close_condition"], "",
    ]
    for opt in item["options"]:
        mark = "（推荐）" if opt.get("recommended") else ""
        lines += [
            "**%s%s**" % (opt["title"], mark), "",
            "方案：%s" % opt["detail"], "",
            "代价与影响：%s" % opt["tradeoff"], "",
        ]
    lines += ["---", ""]

lines += [
    "## 变更记录", "",
    "| 版本 | 日期 | 变更 | 依据任务 |", "| --- | --- | --- | --- |",
    "| v1 | 2026-09-27 | 建立新问题清单：由本轮自定义方案与规则分叉引出 4 项问题（XDM-GAP-017 至 020），每项附候选与推荐 | C-aa-bb-02 |",
]

OUT = os.path.join(ROOT, "Dsh", "Output", "C-aa-bb-02", "C-aa-bb-02_新问题清单_v1.md")
with io.open(OUT, "w", encoding="utf-8", newline="") as fh:
    fh.write("\n".join(lines) + "\n")
print("写出新问题清单：%s" % OUT)
