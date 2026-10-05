# -*- coding: utf-8 -*-
"""战斗域收口检查的现行文档判定与最终结论。"""
import io
import json
import os
import re
import sqlite3

DESIGN = r"D:\myspace\Git\mygame\Dsh\Design"
COMBAT = os.path.join(DESIGN, "06-战斗")
OUTPUT = r"D:\myspace\Git\mygame\Dsh\Output"
DB = os.path.join(OUTPUT, "C-06-bb-01", "C-06-bb-01_战斗系统缺口决策库_v1.sqlite")
VER = re.compile(r"_v(\d+(?:\.\d+)?)\.(md|csv)$")


def version_of(name):
    m = VER.search(name)
    if not m:
        return None
    return tuple(int(x) for x in m.group(1).split("."))


def main():
    # 按“同前缀取最高版本”判定现行文档
    groups = {}
    for root, dirs, files in os.walk(COMBAT):
        for name in files:
            p = os.path.join(root, name)
            m = VER.search(name)
            key_dir = os.path.relpath(root, COMBAT)
            if m:
                prefix = name[:m.start()]
                key = (key_dir, prefix, m.group(2))
                v = version_of(name)
                groups.setdefault(key, []).append((v, name))
            else:
                groups.setdefault((key_dir, name, ""), [(None, name)])

    current, superseded = [], []
    for (key_dir, prefix, ext), items in sorted(groups.items()):
        items.sort(key=lambda x: (x[0] is None, x[0]))
        top = items[-1]
        current.append(os.path.join(key_dir, top[1]) if key_dir != "." else top[1])
        for v, name in items[:-1]:
            superseded.append(os.path.join(key_dir, name) if key_dir != "." else name)

    # 占位检查只针对现行文档
    placeholders = []
    for rel in current:
        p = os.path.join(COMBAT, rel)
        if p.endswith(".md"):
            t = io.open(p, encoding="utf-8").read()
            if re.search(r"^\| 状态 \| 占位 \|", t, re.M):
                placeholders.append(rel)

    conn = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
    cur = conn.cursor()
    archived = cur.execute("SELECT COUNT(*) FROM gaps_archived").fetchone()[0]
    pending = cur.execute(
        "SELECT COUNT(*) FROM decisions WHERE status='待裁定'").fetchone()[0]
    conn.close()

    print(json.dumps({
        "现行文档数": len(current),
        "现行文档": sorted(current),
        "被取代的历史版本数": len(superseded),
        "现行文档中残留占位": placeholders or "无",
        "数据库": {"归档": archived, "主表待裁定": pending},
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
