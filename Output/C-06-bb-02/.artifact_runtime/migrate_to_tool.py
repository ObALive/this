# -*- coding: utf-8 -*-
"""把缺口决策系统从任务输出目录迁移到 Dsh/Tool。

迁移原则：
  通用能力迁出到 Dsh/Tool，任何章节都可以直接复用；
  任务数据（某一次的缺口与候选正文）留在任务输出目录，属于过程产出。

用法：python migrate_to_tool.py
"""
import io
import os
import shutil

REPO = r"D:\myspace\Git\mygame"
SRC = os.path.join(REPO, "Dsh", "Output", "C-06-bb-01", ".artifact_runtime")
DST = os.path.join(REPO, "Dsh", "Tool", "缺口决策系统")

# (源相对路径, 目标相对路径)
MOVE = [
    # 建库工具
    ("建库工具/decision_db_template.py", "建库工具/decision_db_template.py"),
    ("建库工具/import_answers.py", "建库工具/import_answers.py"),
    ("建库工具/export_catalog.py", "建库工具/export_catalog.py"),
    ("建库工具/example_build.py", "建库工具/example_build.py"),
    # 填写器
    ("填写器/decision_server.py", "填写器/decision_server.py"),
    ("填写器/index.html", "填写器/index.html"),
    ("填写器/app.css", "填写器/app.css"),
    ("填写器/app.js", "填写器/app.js"),
    # 测试
    ("测试/smoke_test.py", "测试/smoke_test.py"),
    ("测试/smoke_meta.py", "测试/smoke_meta.py"),
    ("测试/dryrun_import.py", "测试/dryrun_import.py"),
]

# 需要随迁移改指路径的文本
DESIGN = os.path.join(REPO, "Dsh", "Design")


def main():
    os.makedirs(DST, exist_ok=True)
    moved = []
    for rel_src, rel_dst in MOVE:
        src = os.path.join(SRC, *rel_src.split("/"))
        dst = os.path.join(DST, *rel_dst.split("/"))
        if not os.path.isfile(src):
            print("缺失，跳过:", rel_src)
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        moved.append(rel_dst)
        print("已迁移:", rel_src, "->", rel_dst)

    # 清理空目录与缓存
    for junk in ("建库工具/__pycache__", "填写器", "建库工具", "测试"):
        p = os.path.join(SRC, *junk.split("/"))
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
            print("已清理空目录:", junk)

    print("\n迁移文件数:", len(moved))


if __name__ == "__main__":
    main()
