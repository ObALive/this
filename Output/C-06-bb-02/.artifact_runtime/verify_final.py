# -*- coding: utf-8 -*-
"""第二轮最终校验：系统清单、配置表、陈旧引用、数据库、文档落点存在性。"""
import io
import json
import os
import re
import sqlite3

DESIGN = r"D:\myspace\Git\mygame\Dsh\Design"
OUTPUT = r"D:\myspace\Git\mygame\Dsh\Output"
DB = os.path.join(OUTPUT, "C-06-bb-01", "C-06-bb-01_战斗系统缺口决策库_v1.sqlite")


def rel_exists(path):
    return os.path.isfile(os.path.join(DESIGN, path.replace("/", os.sep)))


def main():
    r = {}

    # 1. 06 域系统清单与文档存在性
    roster = [
        ("10", "10-战斗总览/10_战斗总览设计_v3.md"),
        ("20", "20-时间轴与行动顺序/20_时间轴与行动顺序设计_v3.md"),
        ("30", "30-战场与战棋规则/30_战场与战棋规则设计_v3.md"),
        ("40", "40-技能系统/40_技能系统设计_v3.md"),
        ("50", "50-行动槽与连携/50_行动槽与连携设计_v3.md"),
        ("60", "60-装备系统/60_装备系统设计_v5.md"),
        ("70", "70-遗物系统/70_遗物系统设计_v4.md"),
        ("75", "75-元效果系统/75_元效果系统设计_v1.md"),
        ("80", "80-技能与库存联动/80_技能与库存联动设计_v4.md"),
        ("85", "85-战斗行为系统/85_战斗行为系统设计_v1.md"),
        ("90", "90-敌人与AI/90_敌人与AI设计_v3.md"),
        ("A0", "A0-战斗目标与结果/A0_战斗目标与结果设计_v3.md"),
    ]
    r["系统文档存在性"] = {no: rel_exists("06-战斗/" + p) for no, p in roster}

    tables = [
        "05-运营与经济/05-物品系统/05_物品操作总表_v1.csv",
        "05-运营与经济/05-物品系统/05_商人原型配置表_v1.csv",
        "02-时间与事件/30-事件系统/30_事件片段类型表_v1.csv",
        "06-战斗/10-战斗总览/10_角色属性表_v1.csv",
        "06-战斗/75-元效果系统/75_元效果表_v2.csv",
        "06-战斗/85-战斗行为系统/85_战斗行为表_v2.csv",
    ]
    csv_check = {}
    for rel in tables:
        p = os.path.join(DESIGN, rel.replace("/", os.sep))
        lines = [l for l in io.open(p, encoding="utf-8").read().splitlines() if l.strip()]
        widths = {len(l.split(",")) for l in lines}
        csv_check[rel.split("/")[-1]] = {"rows": len(lines), "cols": sorted(widths),
                                        "ok": len(widths) == 1}
    r["配置表"] = csv_check

    # 2. 索引 v3 中引用的文档是否都存在
    idx = io.open(os.path.join(DESIGN, "06-战斗", "06_战斗索引_v3.md"),
                  encoding="utf-8").read()
    refs = re.findall(r"`(06-战斗/[^`]+\.(?:md|csv))`", idx)
    missing = [x for x in sorted(set(refs)) if not rel_exists(x)]
    r["索引引用缺失"] = missing or "无"

    # 3. 陈旧引用（现行文档，排除历史版本与记录类文档）
    stale_tokens = [
        "10-战斗总览/10_战斗行为表_v1.csv",
        "70-遗物系统/70_元效果表_v1.csv",
        "06_战斗索引_v2.md",
    ]
    hist = re.compile(r"_v\d+(\.\d+)?\.(md|csv)$")
    hits = []
    for root, dirs, files in os.walk(DESIGN):
        dirs[:] = [d for d in dirs if d != "归档"]
        for name in files:
            if not name.endswith((".md", ".csv")):
                continue
            rel = os.path.relpath(os.path.join(root, name), DESIGN)
            if hist.search(name) or name == "README.md" or "03_设计决策记录" in name:
                continue
            t = io.open(os.path.join(root, name), encoding="utf-8").read()
            for s in stale_tokens:
                if s in t:
                    hits.append({"file": rel.replace("\\", "/"), "ref": s})
    r["陈旧引用"] = hits or "无"

    # 4. 数据库
    conn = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
    cur = conn.cursor()
    r["数据库"] = {
        "归档": cur.execute("SELECT COUNT(*) FROM gaps_archived").fetchone()[0],
        "待裁定": cur.execute("SELECT COUNT(*) FROM gaps").fetchone()[0],
        "候选": cur.execute(
            "SELECT COUNT(*) FROM solution_options WHERE is_custom=0").fetchone()[0],
        "问题编号": [x[0] for x in cur.execute("SELECT gap_id FROM gaps ORDER BY gap_id")],
    }
    conn.close()

    # 5. 任务输出文档
    r["输出文档"] = {
        name: os.path.isfile(os.path.join(OUTPUT, "C-06-bb-01", name))
        for name in ("C-06-bb-02_回答归档_v2.md", "C-06-bb-02_新问题清单_v2.md",
                     "C-06-bb-01_战斗系统缺口决策库_v1.sqlite")
    }

    print(json.dumps(r, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
