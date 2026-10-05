# -*- coding: utf-8 -*-
"""缺口决策系统的共用路径解析。

工具迁移到 `Dsh/Tool/缺口决策系统/` 之后，不再假设自己位于某个任务目录之下，
改为从工具目录向上定位工作区根目录，并据此解析库文件与前端资源。

定位规则：
  从本文件所在目录逐级向上查找，遇到同时包含 `Dsh` 与 `.git` 的目录即认定为工作区根目录；
  找不到时回退到向上四级的目录，并在日志中说明，便于人工排查。
"""
import glob
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# 默认扫描范围：工作区 Dsh/Output 下所有任务目录，以及工具自带的示例目录
SCAN_PATTERNS = [
    "Dsh/Output/**/*决策库*.sqlite",
    "Dsh/Tool/缺口决策系统/示例/*.sqlite",
]

# 库文件命名约定
DB_SUFFIX = ".sqlite"
DB_KEYWORD = "决策库"


def find_workspace(start=HERE):
    """向上查找工作区根目录。"""
    cur = os.path.abspath(start)
    for _ in range(8):
        if os.path.isdir(os.path.join(cur, "Dsh")) and os.path.isdir(os.path.join(cur, ".git")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))


WORKSPACE = find_workspace()


def to_abs(rel_path):
    """把工作区相对路径（正斜杠或反斜杠）转成绝对路径。"""
    parts = [p for p in str(rel_path).replace("\\", "/").split("/") if p]
    return os.path.join(WORKSPACE, *parts)


def to_rel(abs_path):
    """把绝对路径转成工作区相对路径，统一使用正斜杠。"""
    return os.path.relpath(abs_path, WORKSPACE).replace("\\", "/")


def discover_databases():
    """扫描工作区内的全部决策库，返回排序后的相对路径清单。"""
    found = []
    for pattern in SCAN_PATTERNS:
        found.extend(glob.glob(os.path.join(WORKSPACE, *pattern.split("/")), recursive=True))
    return sorted({to_rel(p) for p in found if os.path.isfile(p)})


def resolve_db(rel_or_abs):
    """把库路径参数解析为绝对路径，越界或不存在时抛出异常。"""
    if not rel_or_abs:
        raise ValueError("未指定决策库路径")
    candidate = os.path.abspath(rel_or_abs)
    if not os.path.isabs(str(rel_or_abs)):
        candidate = to_abs(rel_or_abs)
    if not candidate.startswith(WORKSPACE + os.sep):
        raise ValueError("决策库路径越出工作区：%s" % rel_or_abs)
    if not os.path.isfile(candidate):
        raise ValueError("决策库不存在：%s" % rel_or_abs)
    return candidate


def read_text(path):
    return io.open(path, encoding="utf-8").read()


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)


if __name__ == "__main__":
    print("工具目录 :", HERE)
    print("工作区   :", WORKSPACE)
    print("发现决策库:")
    for item in discover_databases():
        print("   ", item)
