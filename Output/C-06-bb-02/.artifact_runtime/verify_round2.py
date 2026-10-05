# -*- coding: utf-8 -*-
"""第二轮校验：配置表列数、版本一致性、陈旧引用、数据库状态。"""
import io
import json
import os
import re
import sqlite3

DESIGN = r"D:\myspace\Git\mygame\Dsh\Design"
DB = r"D:\myspace\Git\mygame\Dsh\Output\C-06-bb-01\C-06-bb-01_战斗系统缺口决策库_v1.sqlite"

CSV_FILES = [
    "05-运营与经济/05-物品系统/05_物品操作总表_v1.csv",
    "05-运营与经济/05-物品系统/05_商人原型配置表_v1.csv",
    "02-时间与事件/30-事件系统/30_事件片段类型表_v1.csv",
    "06-战斗/10-战斗总览/10_角色属性表_v1.csv",
    "06-战斗/85-战斗行为系统/85_战斗行为表_v2.csv",
    "06-战斗/75-元效果系统/75_元效果表_v2.csv",
]

DOCS = {
    "06-战斗/06_战斗索引_v3.md": ("v3", False),
    "06-战斗/10-战斗总览/10_战斗总览设计_v3.md": ("v3", True),
    "06-战斗/20-时间轴与行动顺序/20_时间轴与行动顺序设计_v3.md": ("v3", True),
    "06-战斗/30-战场与战棋规则/30_战场与战棋规则设计_v3.md": ("v3", True),
    "06-战斗/40-技能系统/40_技能系统设计_v3.md": ("v3", True),
    "06-战斗/50-行动槽与连携/50_行动槽与连携设计_v3.md": ("v3", True),
    "06-战斗/60-装备系统/60_装备系统设计_v5.md": ("v5", True),
    "06-战斗/70-遗物系统/70_遗物系统设计_v4.md": ("v5", True),
    "06-战斗/75-元效果系统/75_元效果系统设计_v1.md": ("v1", True),
    "06-战斗/80-技能与库存联动/80_技能与库存联动设计_v4.md": ("v4", True),
    "06-战斗/85-战斗行为系统/85_战斗行为系统设计_v1.md": ("v1", True),
    "06-战斗/90-敌人与AI/90_敌人与AI设计_v3.md": ("v3", True),
    "06-战斗/A0-战斗目标与结果/A0_战斗目标与结果设计_v3.md": ("v3", True),
    "01-通用系统/50-存档与持久化/50_存档与持久化设计_v2.md": ("v4.1", True),
    "09-数值与配置/10-数值模型/10_数值模型设计_v1.md": ("v1.6", True),
    "00-总览/00_系统全景图_v1.md": ("v1.15", True),
    "00-总览/01_设计原则与跨系统交互逻辑_v1.md": ("v1.14", True),
    "00-总览/02_术语表_v1.md": ("v1.15", True),
    "00-总览/03_设计决策记录_v1.md": ("v1.9", True),
}

STALE = [
    "06_战斗索引_v2.md",
    "10-战斗总览/10_战斗行为表_v1.csv",
    "70-遗物系统/70_元效果表_v1.csv",
    "10_战斗总览设计_v2.md",
    "20_时间轴与行动顺序设计_v2.md",
    "30_战场与战棋规则设计_v2.md",
    "40_技能系统设计_v2.md",
    "50_行动槽与连携设计_v2.md",
    "60_装备系统设计_v4.md",
    "70_遗物系统设计_v3.md",
    "80-技能与库存联动设计_v2.md",
    "90_敌人与AI设计_v2.md",
    "A0_战斗目标与结果设计_v2.md",
]

HISTORICAL = re.compile(r"_v\d+(\.\d+)?\.(md|csv)$")
KEEP = re.compile(r"^(06_战斗索引_v1|06_战斗索引_v2|README)\.md$")


def main():
    r = {}
    # CSV
    csv_report = {}
    for rel in CSV_FILES:
        path = os.path.join(DESIGN, rel.replace("/", os.sep))
        lines = [l for l in io.open(path, encoding="utf-8").read().splitlines() if l.strip()]
        widths = {len(l.split(",")) for l in lines}
        csv_report[rel.split("/")[-1]] = {"rows": len(lines), "cols": sorted(widths),
                                         "ok": len(widths) == 1}
    r["csv"] = csv_report

    # 版本
    ver = {}
    for rel, (expect, has_head) in DOCS.items():
        path = os.path.join(DESIGN, rel.replace("/", os.sep))
        if not os.path.isfile(path):
            ver[rel.split("/")[-1]] = "缺失"
            continue
        t = io.open(path, encoding="utf-8").read()
        head = re.search(r"^\| 版本 \| (v[\d.]+) \|", t, re.M)
        rows = re.findall(r"^\| (v[\d.]+) \| \d{4}-\d{2}-\d{2} \|", t, re.M)
        last = rows[-1] if rows else "?"
        ok = last == expect and (not has_head or (head and head.group(1) == expect))
        ver[rel.split("/")[-1]] = {"head": head.group(1) if head else "-", "last": last,
                                   "expect": expect, "ok": bool(ok)}
    r["versions"] = ver

    # 陈旧引用（现行文档）
    hits = []
    for root, dirs, files in os.walk(DESIGN):
        dirs[:] = [d for d in dirs if d != "归档"]
        for name in files:
            if not name.endswith((".md", ".csv")):
                continue
            rel = os.path.relpath(os.path.join(root, name), DESIGN)
            base = os.path.basename(rel)
            if HISTORICAL.search(base) and not KEEP.match(base):
                continue
            if rel in ("00-总览\\03_设计决策记录_v1.md",) or base == "README.md":
                continue
            t = io.open(os.path.join(root, name), encoding="utf-8").read()
            for s in STALE:
                if s in t:
                    hits.append({"file": rel, "ref": s})
    r["stale"] = hits or "无"

    # 数据库
    conn = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
    cur = conn.cursor()
    r["db"] = {
        "archived": cur.execute("SELECT COUNT(*) FROM gaps_archived").fetchone()[0],
        "open": cur.execute("SELECT COUNT(*) FROM gaps").fetchone()[0],
        "decided_open": cur.execute(
            "SELECT COUNT(*) FROM decisions WHERE status <> '待裁定'").fetchone()[0],
    }
    conn.close()
    print(json.dumps(r, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
