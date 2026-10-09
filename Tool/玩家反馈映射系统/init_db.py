"""从反馈依赖清单 v2 建立初始 SQLite 库。现有库一律不覆盖。"""

from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path

from database import DEFAULT_DB, SCHEMA, SOURCE_MD, create_topic


# 架构设计案 §2.2、§2.3 的模块归属；跨模块主题按参与模块登记。
CODE_OWNERS = {
    1: "M08", 2: "M08", 3: "M01, M02, M08, M10", 4: "M01",
    5: "M06, M08", 6: "M06, M08", 7: "M05, M08",
    8: "M03, M08", 9: "M02, M08, M10", 10: "M02, M03, M04, M08",
    11: "M02, M08", 12: "M02, M10", 13: "M02, M08",
    14: "M02, M04, M08, M09", 15: "M02, M04, M08",
    16: "M02, M04, M08, M09", 17: "M01, M02, M08, M10",
    18: "M04, M08", 19: "M04, M08, M09", 20: "M04, M08",
    21: "M04, M08", 22: "M04, M08", 23: "M04, M08, M09",
    24: "M04, M05, M08", 25: "M05, M08", 26: "M05, M08",
    27: "M05, M08, M09", 28: "M04, M05, M08", 29: "M04, M05, M08",
    30: "M05, M08", 31: "M04, M05, M08", 32: "M02, M05, M08, M10",
    33: "M05, M08", 34: "M05, M08", 35: "M05, M07, M08",
    36: "M04, M05, M08", 37: "M04, M05, M08", 38: "M05, M08, M10",
    39: "M01, M06, M08, M10", 40: "M01, M08", 41: "M01, M08",
    42: "M01, M08", 43: "M01, M08",
}


def read_topics(source: Path) -> list[dict]:
    text = source.read_text(encoding="utf-8-sig")
    items = []
    for line in text.splitlines():
        if not re.match(r"^\| FB-\d+ \|", line):
            continue
        cells = [cell.strip().replace("**", "") for cell in line.strip().strip("|").split("|")]
        if len(cells) != 5:
            raise ValueError(f"反馈主题行不是 5 列：{line}")
        topic_id, behavior, feedback, _old_coordinate, source_ref = cells
        items.append({
            "topic_id": topic_id,
            "player_behavior": behavior,
            "feedback_topic": feedback,
            "code_owner": CODE_OWNERS[int(topic_id.split("-")[1])],
            "source_ref": source_ref,
            "sort_order": len(items) + 1,
        })
    ids = [item["topic_id"] for item in items]
    if len(items) != 43 or len(ids) != len(set(ids)) or len(CODE_OWNERS) != len(items):
        raise ValueError("来源清单的 43 个主题或代码归属对照不完整")
    return items


def build(path: Path = DEFAULT_DB, source: Path = SOURCE_MD) -> int:
    path = Path(path).resolve()
    if path.exists():
        raise FileExistsError(f"目标库已存在，未覆盖：{path}")
    if not source.is_file():
        raise FileNotFoundError(f"来源清单不存在：{source}")
    topics = read_topics(source)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        con = sqlite3.connect(path)
        con.row_factory = sqlite3.Row
        con.executescript(SCHEMA)
        for topic in topics:
            create_topic(con, topic)
        result = con.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok" or con.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError(f"数据库完整性检查未通过：{result}")
        con.close()
    except Exception:
        try:
            con.close()
        finally:
            path.unlink(missing_ok=True)
        raise
    return len(topics)


def main() -> None:
    parser = argparse.ArgumentParser(description="从反馈依赖清单 v2 建立数据库")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="目标 SQLite 路径")
    parser.add_argument("--source", type=Path, default=SOURCE_MD, help="来源 Markdown 路径")
    args = parser.parse_args()
    count = build(args.db, args.source)
    print(f"已建立：{Path(args.db).resolve()}（{count} 个反馈主题，0 条具体映射）")


if __name__ == "__main__":
    main()
