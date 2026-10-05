# -*- coding: utf-8 -*-
"""C-06-bb-02 校验：配置表列数、版本一致性、陈旧引用与数据库状态。"""
import io
import json
import os
import re
import sqlite3

DESIGN = r"D:\myspace\Git\mygame\Dsh\Design"
OUTPUT = r"D:\myspace\Git\mygame\Dsh\Output"
DB = os.path.join(OUTPUT, "C-06-bb-01", "C-06-bb-01_战斗系统缺口决策库_v1.sqlite")

CSV_FILES = [
    "05-运营与经济/05-物品系统/05_物品操作总表_v1.csv",
    "05-运营与经济/05-物品系统/05_商人原型配置表_v1.csv",
    "02-时间与事件/30-事件系统/30_事件片段类型表_v1.csv",
    "06-战斗/10-战斗总览/10_战斗行为表_v1.csv",
    "06-战斗/70-遗物系统/70_元效果表_v1.csv",
]

# 文档版本应与变更记录最新行一致；索引类文档头部表无版本字段，只校验变更记录
DOCS = {
    "06-战斗/10-战斗总览/10_战斗总览设计_v2.md": ("v2", True),
    "06-战斗/20-时间轴与行动顺序/20_时间轴与行动顺序设计_v2.md": ("v2", True),
    "06-战斗/30-战场与战棋规则/30_战场与战棋规则设计_v2.md": ("v2", True),
    "06-战斗/40-技能系统/40_技能系统设计_v2.md": ("v2", True),
    "06-战斗/50-行动槽与连携/50_行动槽与连携设计_v2.md": ("v2", True),
    "06-战斗/60-装备系统/60_装备系统设计_v4.md": ("v4", True),
    "06-战斗/70-遗物系统/70_遗物系统设计_v3.md": ("v4", True),
    "06-战斗/80-技能与库存联动/80_技能与库存联动设计_v2.md": ("v3", True),
    "06-战斗/90-敌人与AI/90_敌人与AI设计_v2.md": ("v2", True),
    "06-战斗/A0-战斗目标与结果/A0_战斗目标与结果设计_v2.md": ("v2", True),
    "06-战斗/06_战斗索引_v2.md": ("v2", False),
    "05-运营与经济/05_运营与经济索引_v2.md": ("v2", False),
    "05-运营与经济/05-物品系统/05_物品系统设计_v1.md": ("v3", True),
    "02-时间与事件/30-事件系统/30_事件系统设计_v2.md": ("v4", True),
    "01-通用系统/50-存档与持久化/50_存档与持久化设计_v2.md": ("v4", True),
    "09-数值与配置/10-数值模型/10_数值模型设计_v1.md": ("v1.5", True),
}

# 陈旧引用检查：只扫描现行文档，历史版本文件与决策台账的历史记录不算
STALE = [
    "05-运营与经济/50-情报与解谜",
    "06-战斗/10-战斗总览/10_战斗总览设计_v1.md",
    "06-战斗/20-时间轴与行动顺序/20_时间轴与行动顺序设计_v1.md",
    "06-战斗/30-战场与战棋规则/30_战场与战棋规则设计_v1.md",
    "06-战斗/40-技能系统/40_技能系统设计_v1.md",
    "06-战斗/50-行动槽与连携/50_行动槽与连携设计_v1.md",
    "06-战斗/60-装备系统/60_装备系统设计_v2.md",
    "06-战斗/70-遗物系统/70_遗物系统设计_v2.md",
    "06-战斗/80-技能与库存联动/80_技能与库存联动设计_v1.md",
    "06-战斗/90-敌人与AI/90_敌人与AI设计_v1.md",
    "06-战斗/A0-战斗目标与结果/A0_战斗目标与结果设计_v1.md",
    "06_战斗索引_v1.md",
    "05_运营与经济索引_v1.md",
]

# 自身名称含 v1 的历史文档，不参与陈旧引用扫描
HISTORICAL = ("_v1.md",)

# 记录历史、允许保留旧路径的文件
EXEMPT = {"00-总览\\03_设计决策记录_v1.md", "README.md"}


def read(path):
    return io.open(path, encoding="utf-8").read()


def main():
    report = {}

    # 1. CSV 列数
    csv_report = {}
    for rel in CSV_FILES:
        path = os.path.join(DESIGN, rel.replace("/", os.sep))
        lines = [l for l in read(path).splitlines() if l.strip()]
        widths = {len(l.split(",")) for l in lines}
        csv_report[rel.split("/")[-1]] = {"rows": len(lines), "columns": sorted(widths),
                                          "一致": len(widths) == 1}
    report["csv"] = csv_report

    # 2. 文档版本一致性
    version_report = {}
    for rel, (expect, has_header) in DOCS.items():
        path = os.path.join(DESIGN, rel.replace("/", os.sep))
        if not os.path.isfile(path):
            version_report[rel.split("/")[-1]] = "文件不存在"
            continue
        text = read(path)
        head = re.search(r"^\| 版本 \| (v[\d.]+) \|", text, re.M)
        head_v = head.group(1).strip() if head else "(无版本字段)"
        rows = re.findall(r"^\| (v[\d.]+) \| \d{4}-\d{2}-\d{2} \|", text, re.M)
        last_v = rows[-1] if rows else "?"
        ok = last_v == expect and (not has_header or head_v == expect)
        version_report[rel.split("/")[-1]] = {
            "头部": head_v, "变更记录最新": last_v, "期望": expect, "一致": ok}
    report["versions"] = version_report

    # 3. 陈旧引用扫描
    stale_hits = []
    for root, dirs, files in os.walk(DESIGN):
        dirs[:] = [d for d in dirs if d != "归档"]
        for name in files:
            if not name.endswith((".md", ".csv")) or name.endswith(HISTORICAL):
                continue
            path = os.path.join(root, name)
            rel = os.path.relpath(path, DESIGN)
            if rel in EXEMPT:
                continue
            try:
                text = read(path)
            except UnicodeDecodeError:
                continue
            for token in STALE:
                if token in text:
                    stale_hits.append({"文件": rel, "引用": token})
    report["陈旧引用"] = stale_hits if stale_hits else "无"

    # 4. 数据库状态
    conn = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
    cur = conn.cursor()
    report["数据库"] = {
        "归档行": cur.execute("SELECT COUNT(*) FROM gaps_archived").fetchone()[0],
        "未澄清问题": cur.execute("SELECT COUNT(*) FROM gaps").fetchone()[0],
        "候选": cur.execute("SELECT COUNT(*) FROM solution_options WHERE is_custom=0").fetchone()[0],
        "自定义预留": cur.execute("SELECT COUNT(*) FROM solution_options WHERE is_custom=1").fetchone()[0],
        "待裁定": cur.execute("SELECT COUNT(*) FROM decisions WHERE status='待裁定'").fetchone()[0],
        "工单编号": [r[0] for r in cur.execute("SELECT gap_id FROM gaps ORDER BY gap_id")],
    }
    conn.close()

    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
