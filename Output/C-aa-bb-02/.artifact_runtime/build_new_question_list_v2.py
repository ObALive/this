# -*- coding: utf-8 -*-
"""由第三轮缺口数据生成新问题清单 v2。"""
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
DATA = json.load(io.open(os.path.join(HERE, "..", "C-aa-bb-02_新缺口数据_v2.json"),
                         encoding="utf-8"))

lines = [
    "# C-aa-bb-02 新问题清单（v2）", "",
    "| 项目 | 内容 |", "| --- | --- |",
    "| 文档定位 | 记录第二轮回填后仍未澄清到可直接实现粒度的问题，每项附候选与推荐 |",
    "| 裁定入口 | `Dsh/Output/C-aa-bb-01/C-aa-bb-01_跨域遗留问题决策库_v1.sqlite`，可用填写器逐项裁定 |",
    "| 问题来源 | 第二轮裁定把结局体系统一为三种之后，三种收尾情形在达成记录中的落点没有规则 |",
    "| 编号规则 | 沿用 XDM-GAP 前缀从 021 起递增，不与已归档的 001 至 020 重复 |",
    "| 上一版本 | `C-aa-bb-02_新问题清单_v1.md`（XDM-GAP-017 至 020 已裁定并归档） |",
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
    "| v1 | 2026-09-27 | 建立新问题清单：4 项问题（XDM-GAP-017 至 020），全部已裁定并归档 | C-aa-bb-02 |",
    "| v2 | 2026-09-27 | 重建为 1 项（XDM-GAP-021）：未通关结局三种收尾情形在达成记录中的落点 | C-aa-bb-02（第二轮） |",
]

OUT = os.path.join(ROOT, "Dsh", "Output", "C-aa-bb-02", "C-aa-bb-02_新问题清单_v2.md")
with io.open(OUT, "w", encoding="utf-8", newline="") as fh:
    fh.write("\n".join(lines) + "\n")
print("写出新问题清单：%s" % OUT)
