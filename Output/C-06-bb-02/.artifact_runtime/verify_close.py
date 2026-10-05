# -*- coding: utf-8 -*-
"""C-06-bb-02 战斗域收口最终校验。"""
import io
import json
import os
import re
import sqlite3

DESIGN = r"D:\myspace\Git\mygame\Dsh\Design"
COMBAT = os.path.join(DESIGN, "06-战斗")
OUTPUT = r"D:\myspace\Git\mygame\Dsh\Output"
DB = os.path.join(OUTPUT, "C-06-bb-01", "C-06-bb-01_战斗系统缺口决策库_v1.sqlite")
HIST = re.compile(r"_v[1-9](\.[0-9]+)?\.(md|csv)$")
REF = re.compile(r"`([^`]*?(?:06-战斗|05-运营与经济|02-时间与事件|09-数值与配置)/[^`]+?\.(?:md|csv))`")
EXEMPT = {"README.md", "03_设计决策记录_v1.md"}


def resolve(rel):
    return os.path.join(DESIGN, *[p for p in rel.split("/") if p])


def main():
    out = {}

    # 1. 06 域占位清理与子系统覆盖
    placeholders, files = [], []
    for root, dirs, fs in os.walk(COMBAT):
        for name in fs:
            p = os.path.join(root, name)
            rel = os.path.relpath(p, COMBAT)
            files.append(rel)
            if name.endswith(".md"):
                t = io.open(p, encoding="utf-8").read()
                if re.search(r"^\| 状态 \| 占位 \|", t, re.M):
                    placeholders.append(rel)
    out["06域文件数"] = len(files)
    out["残留占位文档"] = placeholders or "无"

    # 2. 现行子系统文档清单
    current = [f for f in files if not HIST.search(os.path.basename(f))
               and os.path.basename(f) not in ("06_战斗索引_v1.md", "06_战斗索引_v2.md")]
    out["现行文档"] = sorted(current)

    # 3. 引用完整性
    missing = []
    for root, dirs, fs in os.walk(DESIGN):
        dirs[:] = [d for d in dirs if d != "归档"]
        for name in fs:
            if not name.endswith((".md", ".csv")) or HIST.search(name) or name in EXEMPT:
                continue
            p = os.path.join(root, name)
            t = io.open(p, encoding="utf-8").read()
            for ref in set(REF.findall(t)):
                if not os.path.isfile(resolve(ref)):
                    missing.append({"出处": os.path.relpath(p, DESIGN), "引用": ref})
    out["引用缺失"] = missing or "无"

    # 4. 版本一致性（重点文档）
    docs = {
        "05-运营与经济/05_运营与经济索引_v2.3.md": "v2.4",
        "05-运营与经济/05-物品系统/05_物品系统设计_v1.md": "v6",
        "05-运营与经济/10-金钱与货物/10_金钱与货物设计_v2.md": "v4",
        "06-战斗/60-装备系统/60_装备系统设计_v7.md": "v7",
        "06-战斗/80-技能与库存联动/80_技能与库存联动设计_v6.md": "v6",
        "02-时间与事件/30-事件系统/30-10-触发条件/30-10_触发条件设计_v2.md": "v2.5",
        "00-总览/00_系统全景图_v1.md": "v1.18",
        "00-总览/01_设计原则与跨系统交互逻辑_v1.md": "v1.17",
        "00-总览/02_术语表_v1.md": "v1.18",
        "00-总览/03_设计决策记录_v1.md": "v1.13",
    }
    bad = []
    for rel, expect in docs.items():
        p = resolve(rel)
        if not os.path.isfile(p):
            bad.append({"文件": rel, "原因": "文件不存在"})
            continue
        t = io.open(p, encoding="utf-8").read()
        head = re.search(r"^\| 版本 \| (v[\d.]+) \|", t, re.M)
        rows = re.findall(r"^\| (v[\d.]+) \| \d{4}-\d{2}-\d{2} \|", t, re.M)
        last = rows[-1] if rows else "?"
        hv = head.group(1) if head else "-"
        if last != expect or (hv != "-" and hv != expect):
            bad.append({"文件": rel, "head": hv, "last": last, "expect": expect})
    out["版本不一致"] = bad or "无"

    # 5. 配置表列数
    tables = []
    for root, dirs, fs in os.walk(DESIGN):
        dirs[:] = [d for d in dirs if d != "归档"]
        for name in fs:
            if name.endswith(".csv"):
                p = os.path.join(root, name)
                lines = [l for l in io.open(p, encoding="utf-8").read().splitlines() if l.strip()]
                widths = sorted({len(l.split(",")) for l in lines})
                tables.append({"表": os.path.relpath(p, DESIGN), "行": len(lines),
                               "列": widths, "ok": len(widths) == 1})
    out["配置表"] = tables
    out["配置表异常"] = [t["表"] for t in tables if not t["ok"]] or "无"

    # 6. 数据库
    conn = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
    cur = conn.cursor()
    out["数据库"] = {
        "归档": cur.execute("SELECT COUNT(*) FROM gaps_archived").fetchone()[0],
        "主表待裁定": cur.execute(
            "SELECT COUNT(*) FROM decisions WHERE status='待裁定'").fetchone()[0],
    }
    conn.close()

    # 7. 任务输出
    out["输出文档"] = sorted(
        f for f in os.listdir(os.path.join(OUTPUT, "C-06-bb-01")) if f.endswith(".md"))
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
