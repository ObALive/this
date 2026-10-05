# -*- coding: utf-8 -*-
"""第三轮收尾校验：现行文档的引用完整性、版本一致性、配置表与数据库状态。"""
import io
import json
import os
import re
import sqlite3

DESIGN = r"D:\myspace\Git\mygame\Dsh\Design"
DB = r"D:\myspace\Git\mygame\Dsh\Output\C-06-bb-01\C-06-bb-01_战斗系统缺口决策库_v1.sqlite"
HIST = re.compile(r"_v[1-9](\.[0-9]+)?\.(md|csv)$")
REF = re.compile(r"`([^`]*?(?:06-战斗|05-运营与经济)/[^`]+?\.(?:md|csv))`")
EXEMPT_FILES = {"README.md", "03_设计决策记录_v1.md"}


def resolve(rel):
    return os.path.join(DESIGN, *[p for p in rel.split("/") if p])


def main():
    out = {"引用缺失": [], "版本不一致": [], "配置表异常": []}

    for root, dirs, files in os.walk(DESIGN):
        dirs[:] = [d for d in dirs if d != "归档"]
        for name in files:
            if not name.endswith((".md", ".csv")) or HIST.search(name):
                continue
            if name in EXEMPT_FILES:
                continue
            p = os.path.join(root, name)
            rel = os.path.relpath(p, DESIGN)
            t = io.open(p, encoding="utf-8").read()
            for ref in set(REF.findall(t)):
                if not os.path.isfile(resolve(ref)):
                    out["引用缺失"].append({"出处": rel, "引用": ref})

    docs = {
        "06-战斗/06_战斗索引_v3.1.md": "v3.1",
        "06-战斗/10-战斗总览/10_战斗总览设计_v4.md": "v4",
        "06-战斗/40-技能系统/40_技能系统设计_v4.md": "v4",
        "06-战斗/60-装备系统/60_装备系统设计_v6.md": "v6",
        "06-战斗/80-技能与库存联动/80_技能与库存联动设计_v5.md": "v5",
        "06-战斗/90-敌人与AI/90_敌人与AI设计_v4.md": "v4",
        "00-总览/02_术语表_v1.md": "v1.16.1",
        "05-运营与经济/05-物品系统/05_物品系统设计_v1.md": "v4",
    }
    for rel, expect in docs.items():
        t = io.open(resolve(rel), encoding="utf-8").read()
        head = re.search(r"^\| 版本 \| (v[\d.]+) \|", t, re.M)
        rows = re.findall(r"^\| (v[\d.]+) \| \d{4}-\d{2}-\d{2} \|", t, re.M)
        last = rows[-1] if rows else "?"
        hv = head.group(1) if head else "-"
        if last != expect or (hv != "-" and hv != expect):
            out["版本不一致"].append({"文件": rel, "head": hv, "last": last,
                                     "expect": expect})

    for rel in ("05-运营与经济/05-物品系统/05_物品操作总表_v1.csv",
                "06-战斗/80-技能与库存联动/80_投掷组件表_v1.csv",
                "06-战斗/85-战斗行为系统/85_战斗行为表_v2.csv",
                "06-战斗/75-元效果系统/75_元效果表_v2.csv",
                "06-战斗/10-战斗总览/10_角色属性表_v1.csv"):
        lines = [l for l in io.open(resolve(rel), encoding="utf-8").read().splitlines()
                 if l.strip()]
        widths = sorted({len(l.split(",")) for l in lines})
        if len(widths) != 1:
            out["配置表异常"].append({"文件": rel, "列": widths})

    conn = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
    cur = conn.cursor()
    out["归档总数"] = cur.execute("SELECT COUNT(*) FROM gaps_archived").fetchone()[0]
    out["待裁定"] = [r[0] for r in cur.execute("SELECT gap_id FROM gaps ORDER BY gap_id")]
    out["候选"] = cur.execute(
        "SELECT COUNT(*) FROM solution_options WHERE is_custom=0").fetchone()[0]
    conn.close()

    for key in ("引用缺失", "版本不一致", "配置表异常"):
        if not out[key]:
            out[key] = "无"
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
