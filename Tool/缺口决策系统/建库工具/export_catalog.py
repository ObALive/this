# -*- coding: utf-8 -*-
"""从决策库导出可读文本：候选清单与作答模板。

用法：
  python export_catalog.py                                   # 自动选取工作区内第一个决策库
  python export_catalog.py --db <库路径>                     # 指定决策库
  python export_catalog.py --db <库路径> --out-dir <目录>     # 指定输出目录，缺省为库所在目录

输出：
  {库名}_候选清单_v{版本}.md   全部缺口与候选的只读清单
  {库名}_作答模板_v{版本}.md   带填写标记的模板，填好后用 import_answers.py 导入

填写标记：
  [候选] 采用某个候选时，在标记后写候选字母，例如 [候选] B
  [预期方案] 候选都不符合时，在标记后写自己的方案
  [裁定理由] 可选，说明为什么这样选
  [补充要求] 可选，补充候选里没覆盖的细节
"""
import argparse
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_locator import discover_databases, resolve_db, to_rel, write_text  # noqa: E402

MARK_CANDIDATE = "[候选]"
MARK_CUSTOM = "[预期方案]"
MARK_BASIS = "[裁定理由]"
MARK_EXTRA = "[补充要求]"
VERSION = re.compile(r"_v(\d+(?:\.\d+)?)\.sqlite$")


def default_db():
    items = discover_databases()
    if not items:
        raise SystemExit("工作区内没有找到决策库，请用 --db 指定")
    return items[0]


def output_paths(db_path, out_dir):
    stem = os.path.splitext(os.path.basename(db_path))[0]
    m = VERSION.search(os.path.basename(db_path))
    version = m.group(1) if m else "1"
    base = re.sub(r"_v\d+(?:\.\d+)?$", "", stem)
    folder = out_dir or os.path.dirname(db_path)
    return (os.path.join(folder, "%s_候选清单_v%s.md" % (base, version)),
            os.path.join(folder, "%s_作答模板_v%s.md" % (base, version)))


def load(cur):
    gaps = []
    for r in cur.execute(
            "SELECT gap_id, title, level, status, priority_round, owner, source_ref,"
            " impact_scope, close_condition FROM gaps ORDER BY gap_id"):
        gaps.append({"gap_id": r[0], "title": r[1], "level": r[2], "status": r[3],
                     "priority": r[4], "owner": r[5], "source": r[6], "impact": r[7],
                     "close": r[8]})
    options = {}
    for r in cur.execute(
            "SELECT gap_id, option_label, summary_title, detail, tradeoff, is_recommended,"
            " is_custom, is_selected FROM solution_options ORDER BY gap_id, seq"):
        options.setdefault(r[0], []).append({
            "label": r[1], "title": r[2], "detail": r[3], "tradeoff": r[4],
            "recommended": r[5], "custom": r[6], "selected": r[7]})
    return gaps, options


def plain_title(option):
    title = option["title"]
    prefix = "候选 %s：" % option["label"]
    return title[len(prefix):] if title.startswith(prefix) else title


def write_catalog(gaps, options, db_rel, path):
    total = sum(1 for rows in options.values() for o in rows if not o["custom"])
    lines = [
        "# 缺口候选清单", "",
        "| 项目 | 内容 |", "| --- | --- |",
        "| 文档定位 | 决策库内全部缺口与候选方案的只读清单，用于横向比对 |",
        "| 数据来源 | `%s` |" % db_rel,
        "| 状态 | 只读清单，裁定请写入数据库或作答模板 |", "",
        "共 %d 项缺口，%d 条候选方案；每项缺口另在库中预留一条自定义方案行。"
        % (len(gaps), total), "", "---", "",
    ]
    for g in gaps:
        lines += ["## %s %s" % (g["gap_id"], g["title"]), "",
                  "| 字段 | 内容 |", "| --- | --- |",
                  "| 等级 | %s |" % g["level"],
                  "| 责任方 | %s |" % g["owner"],
                  "| 当前状态 | %s |" % g["status"],
                  "| 优先轮次 | %s |" % (g["priority"] or "未列入本轮问题包"),
                  "| 来源 | %s |" % g["source"],
                  "| 影响范围 | %s |" % g["impact"],
                  "| 关闭条件 | %s |" % g["close"], ""]
        for o in options[g["gap_id"]]:
            if o["custom"]:
                lines += ["### 自定义方案", "",
                          "候选方案均不符合时的填写位置，内容写入数据库 `decisions.answer_text`。", ""]
                continue
            mark = "（推荐）" if o["recommended"] else ""
            lines += ["### 候选 %s：%s%s" % (o["label"], plain_title(o), mark), "",
                      o["detail"], "", "代价与影响：%s" % o["tradeoff"], ""]
        lines += ["---", ""]
    write_text(path, "\n".join(lines))
    return path


def write_template(gaps, options, db_rel, path):
    lines = [
        "# 缺口作答模板", "",
        "| 项目 | 内容 |", "| --- | --- |",
        "| 文档定位 | 供逐项填写裁定结果；填好后运行 `import_answers.py --db \"%s\"` 导入 |" % db_rel,
        "| 采用候选 | 在 `%s` 后写候选字母，例如 `%s B`" % (MARK_CANDIDATE, MARK_CANDIDATE),
        "| 自定义方案 | 候选都不符合时，在 `%s` 后写自己的方案" % MARK_CUSTOM,
        "| 可选补充 | `%s` 说明理由，`%s` 补充候选未覆盖的细节" % (MARK_BASIS, MARK_EXTRA),
        "| 留空含义 | 未填写的项视为尚未裁定，导入时跳过 |",
        "| 状态 | 待填写 |", "", "---", "",
    ]
    for g in gaps:
        lines += ["## %s %s" % (g["gap_id"], g["title"]), "",
                  "- 等级：%s；责任方：%s；优先轮次：%s"
                  % (g["level"], g["owner"], g["priority"] or "未列入本轮问题包"), ""]
        for o in options[g["gap_id"]]:
            if o["custom"]:
                continue
            mark = "（推荐）" if o["recommended"] else ""
            lines += ["- **候选 %s：%s**%s" % (o["label"], plain_title(o), mark),
                      "  - 方案：%s" % o["detail"],
                      "  - 代价：%s" % o["tradeoff"]]
        lines += ["", "%s " % MARK_CANDIDATE, "", "%s " % MARK_CUSTOM, "",
                  "%s " % MARK_BASIS, "", "%s " % MARK_EXTRA, "", "---", ""]
    write_text(path, "\n".join(lines))
    return path


def main():
    parser = argparse.ArgumentParser(description="从决策库导出候选清单与作答模板")
    parser.add_argument("--db", help="决策库路径，缺省时自动选取")
    parser.add_argument("--out-dir", help="输出目录，缺省为库所在目录")
    args = parser.parse_args()

    db_path = resolve_db(args.db or default_db())
    db_rel = to_rel(db_path)
    catalog_path, template_path = output_paths(db_path, args.out_dir)

    conn = sqlite3.connect("file:%s?mode=ro" % db_path.replace("\\", "/"), uri=True)
    cur = conn.cursor()
    gaps, options = load(cur)
    conn.close()

    write_catalog(gaps, options, db_rel, catalog_path)
    write_template(gaps, options, db_rel, template_path)
    print("库      :", db_rel)
    print("缺口数  :", len(gaps))
    print("候选清单:", os.path.basename(catalog_path), os.path.getsize(catalog_path), "字节")
    print("作答模板:", os.path.basename(template_path), os.path.getsize(template_path), "字节")


if __name__ == "__main__":
    main()
