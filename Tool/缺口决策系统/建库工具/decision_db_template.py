# -*- coding: utf-8 -*-
"""兼容入口：实际模块已更名为 decision_db.py。

保留本文件是为了让早期写下的 `from decision_db_template import ...` 仍然可用；
新代码请直接导入 `decision_db`，或查看 `decision_db.py` 的文档字符串。
"""
from decision_db import (  # noqa: F401
    CUSTOM_SEQ,
    LABELS,
    REQUIRED_TABLES,
    REQUIRED_VIEWS,
    SCHEMA,
    STATUS_CHOSEN,
    STATUS_CUSTOM,
    STATUS_PENDING,
    GapRecord,
    OptionRecord,
    archive_decided,
    build_decision_db,
    ensure_archive_table,
    ensure_meta,
    verify_decision_db,
)

__all__ = [
    "CUSTOM_SEQ", "LABELS", "REQUIRED_TABLES", "REQUIRED_VIEWS", "SCHEMA",
    "STATUS_CHOSEN", "STATUS_CUSTOM", "STATUS_PENDING",
    "GapRecord", "OptionRecord", "archive_decided", "build_decision_db",
    "ensure_archive_table", "ensure_meta", "verify_decision_db",
]
