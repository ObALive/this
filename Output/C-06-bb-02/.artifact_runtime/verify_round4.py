# -*- coding: utf-8 -*-
"""第四轮收尾校验。"""
import io
import json
import os
import re
import sqlite3

DESIGN = r"D:\myspace\Git\mygame\Dsh\Design"
DB = r"D:\myspace\Git\mygame\Dsh\Output\C-06-bb-01\C-06-bb-01_战斗系统缺口决策库_v1.sqlite"
HIST = re.compile(r"_v[1-9](\.[0-9]+)?\.(md|csv)$")
REF = re.compile(r"`([^`]*?(?:06-战斗|05-运营与经济|02-时间与事件|09-数值与配置)/[^`]+?\.(?:md|csv))`")
EXEMPT = {"README.md", "03_设计决策记录_v1.md"}


def resolve(rel):
    return os.path.join(DESIGN, *[p for p in rel.split("/") if p])


def main():
    out = {"引用缺失": [], "版本不一致": [], "配置表异常": []}

    for root, dirs, files in os.walk(DESIGN):
        dirs[:] = [d for d in dirs if d != "归档"]
        for name in files:
            if not name.endswith((".md", ".csv")) or HIST.search(name):
                continue
            if name in EXEMPT:
                continue
            p = os.path.join(root, name)
            rel = os.path.relpath(p, DESIGN)
            t = io.open(p, encoding="utf-8").read()
            for ref in set(REF.findall(t)):
                if not os.path.isfile(resolve(ref)):
                    out["引用缺失"].append({"出处": rel, "引用": ref})

    docs = {
        "05-运营与经济/05_运营与经济索引_v2.3.md": "v2.3",
        "05-运营与经济/05-物品系统/05_物品系统设计_v1.md": "v5",
        "05-运营与经济/05-物品系统/05_物品词条表_v1.csv": None,
        "06-战斗/60-装备系统/60_装备系统设计_v7.md": "v7",
        "06-战斗/80-技能与库存联动/80_技能与库存联动设计_v6.md": "v6",
        "02-时间与事件/30-事件系统/30-10-触发条件/30-10_触发条件设计_v2.md": "v2.5",
        "00-总览/00_系统全景图_v1.md": "v1.17",
        "00-总览/01_设计原则与跨系统交互逻辑_v1.md": "v1.16",
        "00-总览/02_术语表_v1.md": "v1.17",
        "00-总览/03_设计决策记录_v1.md": "v1.12",
        "09-数值与配置/10-数值模型/10_数值模型设计_v1.md": "v1.8",
    }
    for rel, expect in docs.items():
        if expect is None:
            continue
        t = io.open(resolve(rel), encoding="utf-8").read()
        head = re.search(r"^\| 版本 \| (v[\d.]+) \|", t, re.M)
        rows = re.findall(r"^\| (v[\d.]+) \| \d{4}-\d{2}-\d{2} \|", t, re.M)
        last = rows[-1] if rows else "?"
        hv = head.group(1) if head else "-"
        if last != expect or (hv != "-" and hv != expect):
            out["版本不一致"].append({"文件": rel, "head": hv, "last": last, "expect": expect})

    for rel in ("05-运营与经济/05-物品系统/05_物品词条表_v1.csv",
                "05-运营与经济/05-物品系统/05_物品操作总表_v1.csv",
                "05-运营与经济/05-物品系统/05_商人原型配置表_v1.csv",
                "06-战斗/80-技能与库存联动/80_投掷组件表_v1.csv"):
        lines = [l for l in io.open(resolve(rel), encoding="utf-8").read().splitlines()
                 if l.strip()]
        widths = sorted({len(l.split(",")) for l in lines})
        if len(widths) != 1:
            out["配置表异常"].append({"文件": rel, "列": widths})

    conn = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
    cur = conn.cursor()
    out["归档总数"] = cur.execute("SELECT COUNT(*) FROM gaps_archived").fetchone()[0]
    out["待裁定"] = [r[0] for r in cur.execute("SELECT gap_id FROM gaps ORDER BY gap_id")]
    conn.close()

    for k in ("引用缺失", "版本不一致", "配置表异常"):
        if not out[k]:
            out[k] = "无"
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
