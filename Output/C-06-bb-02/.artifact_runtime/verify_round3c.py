# -*- coding: utf-8 -*-
"""第三轮最终校验（文件名重命名后）。"""
import io
import json
import os
import re
import sqlite3

DESIGN = r"D:\myspace\Git\mygame\Dsh\Design"
DB = r"D:\myspace\Git\mygame\Dsh\Output\C-06-bb-01\C-06-bb-01_战斗系统缺口决策库_v1.sqlite"


def resolve(rel):
    return os.path.join(DESIGN, *[p for p in rel.split("/") if p])


CSVS = [
    "05-运营与经济/05-物品系统/05_物品操作总表_v1.csv",
    "05-运营与经济/05-物品系统/05_商人原型配置表_v1.csv",
    "02-时间与事件/30-事件系统/30_事件片段类型表_v1.csv",
    "06-战斗/10-战斗总览/10_角色属性表_v1.csv",
    "06-战斗/75-元效果系统/75_元效果表_v2.csv",
    "06-战斗/85-战斗行为系统/85_战斗行为表_v2.csv",
    "06-战斗/80-技能与库存联动/80_投掷组件表_v1.csv",
]

DOCS = {
    "05-运营与经济/05_运营与经济索引_v2.2.md": ("v2.2", False),
    "05-运营与经济/05-物品系统/05_物品系统设计_v1.md": ("v4", True),
    "09-数值与配置/10-数值模型/10_数值模型设计_v1.md": ("v1.7", True),
    "06-战斗/06_战斗索引_v3.1.md": ("v3.1", False),
    "06-战斗/10-战斗总览/10_战斗总览设计_v4.md": ("v4", True),
    "06-战斗/20-时间轴与行动顺序/20_时间轴与行动顺序设计_v3.md": ("v3", True),
    "06-战斗/30-战场与战棋规则/30_战场与战棋规则设计_v3.md": ("v3", True),
    "06-战斗/40-技能系统/40_技能系统设计_v4.md": ("v4", True),
    "06-战斗/50-行动槽与连携/50_行动槽与连携设计_v3.md": ("v3", True),
    "06-战斗/60-装备系统/60_装备系统设计_v6.md": ("v6", True),
    "06-战斗/70-遗物系统/70_遗物系统设计_v4.md": ("v5", True),
    "06-战斗/75-元效果系统/75_元效果系统设计_v1.md": ("v1", True),
    "06-战斗/80-技能与库存联动/80_技能与库存联动设计_v5.md": ("v5", True),
    "06-战斗/85-战斗行为系统/85_战斗行为系统设计_v1.md": ("v1.1", True),
    "06-战斗/90-敌人与AI/90_敌人与AI设计_v4.md": ("v4", True),
    "06-战斗/A0-战斗目标与结果/A0_战斗目标与结果设计_v3.md": ("v3", True),
    "00-总览/00_系统全景图_v1.md": ("v1.16", True),
    "00-总览/01_设计原则与跨系统交互逻辑_v1.md": ("v1.15", True),
    "00-总览/02_术语表_v1.md": ("v1.16", True),
    "00-总览/03_设计决策记录_v1.md": ("v1.11", True),
}


def main():
    out = {"配置表": {}, "版本": {}}
    for rel in CSVS:
        lines = [l for l in io.open(resolve(rel), encoding="utf-8").read().splitlines()
                 if l.strip()]
        widths = sorted({len(l.split(",")) for l in lines})
        out["配置表"][rel.split("/")[-1]] = {"行": len(lines), "列": widths,
                                            "ok": len(widths) == 1}
    for rel, (expect, has_head) in DOCS.items():
        t = io.open(resolve(rel), encoding="utf-8").read()
        head = re.search(r"^\| 版本 \| (v[\d.]+) \|", t, re.M)
        rows = re.findall(r"^\| (v[\d.]+) \| \d{4}-\d{2}-\d{2} \|", t, re.M)
        last = rows[-1] if rows else "?"
        hv = head.group(1) if head else "-"
        ok = (last == expect) and (not has_head or hv == expect)
        out["版本"][rel.split("/")[-1]] = {"head": hv, "last": last, "ok": ok}

    # 引用完整性：全库现行文档是否都指向存在的文件
    missing = []
    pattern = re.compile(r"`([^`]*?(?:06-战斗|05-运营与经济)/[^`]+?\.(?:md|csv))`")
    for root, dirs, files in os.walk(DESIGN):
        dirs[:] = [d for d in dirs if d != "归档"]
        for name in files:
            if not name.endswith((".md", ".csv")):
                continue
            p = os.path.join(root, name)
            t = io.open(p, encoding="utf-8").read()
            for ref in set(pattern.findall(t)):
                target = resolve(ref)
                if not os.path.isfile(target):
                    missing.append({"出处": os.path.relpath(p, DESIGN), "引用": ref})
    out["引用缺失"] = missing or "无"

    conn = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
    cur = conn.cursor()
    out["待裁定"] = [r[0] for r in cur.execute("SELECT gap_id FROM gaps ORDER BY gap_id")]
    out["归档总数"] = cur.execute("SELECT COUNT(*) FROM gaps_archived").fetchone()[0]
    out["候选"] = cur.execute(
        "SELECT COUNT(*) FROM solution_options WHERE is_custom=0").fetchone()[0]
    conn.close()
    out["版本不一致"] = [k for k, v in out["版本"].items() if not v["ok"]] or "无"
    out["配置表异常"] = [k for k, v in out["配置表"].items() if not v["ok"]] or "无"
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
