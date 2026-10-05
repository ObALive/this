# -*- coding: utf-8 -*-
"""迁移后功能自测：库定位、建库、导出、导入、归档、填写器接口。

在临时目录建一个包含 2 项缺口与 3 条候选的测试库，走完整个工作流后清理。
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.abspath(os.path.join(HERE, ".."))
BUILD = os.path.join(TOOL, "建库工具")
REVIEW = os.path.join(TOOL, "审阅工具")
SERVER = os.path.join(TOOL, "填写器", "decision_server.py")

sys.path.insert(0, BUILD)
from db_locator import WORKSPACE, discover_databases, resolve_db, to_rel  # noqa: E402


def run(args):
    out = subprocess.run([sys.executable] + args, capture_output=True, text=True,
                         encoding="utf-8", cwd=BUILD)
    return out.returncode, (out.stdout or "").strip(), (out.stderr or "").strip()


def build_fixture(tmp_dir):
    """在临时目录建一个测试库，作为工作区内的库被发现。"""
    data = {
        "meta": {"title": "自测用决策库", "chapter": "TEST-01", "domain": "自测域",
                 "analysis_doc": "临时演示，不进入设计库"},
        "db_path": to_rel(os.path.join(tmp_dir, "TEST-01_自测缺口决策库_v1.sqlite")),
        "gaps": [
            {"gap_id": "TEST-GAP-001", "title": "自测缺口一：用于验证候选与裁定流程",
             "level": "B0", "source_ref": "自测", "impact_scope": "自测系统",
             "close_condition": "完成自测", "owner": "主策划",
             "options": [
                 {"label": "A", "title": "候选 A：方案一", "detail": "方案一正文。",
                  "tradeoff": "代价一。", "recommended": True},
                 {"label": "B", "title": "候选 B：方案二", "detail": "方案二正文。",
                  "tradeoff": "代价二。"},
                 {"label": "C", "title": "候选 C：方案三", "detail": "方案三正文。",
                  "tradeoff": "代价三。"}]},
            {"gap_id": "TEST-GAP-002", "title": "自测缺口二：用于验证自定义方案",
             "level": "B1", "source_ref": "自测", "impact_scope": "自测系统",
             "close_condition": "完成自测", "owner": "主策划",
             "options": [
                 {"label": "A", "title": "候选 A：方案甲", "detail": "方案甲正文。",
                  "tradeoff": "代价甲。"},
                 {"label": "B", "title": "候选 B：方案乙", "detail": "方案乙正文。",
                  "tradeoff": "代价乙。"}]},
        ],
    }
    data_path = os.path.join(tmp_dir, "fixture.json")
    open(data_path, "w", encoding="utf-8", newline="\n").write(
        json.dumps(data, ensure_ascii=False, indent=1))
    return data_path, data["db_path"]


def fill_template(template_path, out_path):
    """在模板里填一个候选答案与一个自定义方案。"""
    lines = open(template_path, encoding="utf-8").read().split("\n")
    hit_candidate = hit_custom = hit_second = False
    for i, line in enumerate(lines):
        s = line.strip()
        if not hit_candidate and s == "[候选]":
            lines[i] = "[候选] B"
            hit_candidate = True
            continue
        if s.startswith("## TEST-GAP-002"):
            hit_second = True
            continue
        if hit_second and not hit_custom and s == "[预期方案]":
            lines[i] = "[预期方案] 自测自定义方案正文"
            hit_custom = True
            break
    open(out_path, "w", encoding="utf-8", newline="\n").write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8791)
    args = parser.parse_args()
    result = {}

    result["工作区"] = WORKSPACE
    result["工作区已有决策库"] = discover_databases()

    tmp_dir = tempfile.mkdtemp(prefix="gapdb_", dir=WORKSPACE)
    try:
        data_path, db_rel = build_fixture(tmp_dir)
        db_abs = os.path.join(WORKSPACE, *db_rel.split("/"))

        code, out, err = run([os.path.join(BUILD, "build_decision_db.py"),
                              "--data", data_path])
        result["1 建库"] = {"exit": code, "输出": out[-420:], "错误": err[:200]}

        code, out, err = run([os.path.join(BUILD, "decision_db.py"),
                              "--check", db_abs])
        result["2 模板校验"] = {"exit": code,
                            "通过项": json.loads(out).get("gaps") if code == 0 and out else out[:200]}

        code, out, err = run([os.path.join(BUILD, "export_catalog.py"), "--db", db_rel])
        result["3 导出清单与模板"] = {"exit": code, "输出": out, "错误": err[:200]}

        catalog = os.path.join(tmp_dir, "TEST-01_自测缺口决策库_候选清单_v1.md")
        template = os.path.join(tmp_dir, "TEST-01_自测缺口决策库_作答模板_v1.md")
        result["3 产物存在"] = {"候选清单": os.path.isfile(catalog),
                            "作答模板": os.path.isfile(template)}

        filled = os.path.join(tmp_dir, "filled.md")
        fill_template(template, filled)
        code, out, err = run([os.path.join(REVIEW, "import_answers.py"),
                              "--db", db_rel, "--answers", filled])
        result["4 导入裁定"] = {"exit": code, "输出": out, "错误": err[:200]}

        code, out, err = run([os.path.join(REVIEW, "dump_decisions.py"), "--db", db_rel])
        result["5 读取裁定"] = {"exit": code, "输出": out[:500], "错误": err[:200]}

        code, out, err = run([os.path.join(REVIEW, "dump_decisions.py"), "--db", db_rel,
                              "--markdown", "--out",
                              os.path.join(tmp_dir, "conclusion.md")])
        result["6 导出结论"] = {"exit": code, "输出": out, "错误": err[:200]}

        code, out, err = run([os.path.join(REVIEW, "archive_decided.py"),
                              "--db", db_rel, "--by", "smoke_tool"])
        result["7 归档"] = {"exit": code, "输出": out, "错误": err[:200]}

        code, out, err = run([os.path.join(BUILD, "decision_db.py"),
                              "--check", db_abs])
        after = json.loads(out) if code == 0 and out else {}
        result["8 归档后状态"] = {"主表": after.get("gaps"), "归档表":
                              subprocess.run(
                                  [sys.executable, "-c",
                                   "import sqlite3,sys;c=sqlite3.connect(sys.argv[1]);"
                                   "print(c.execute('SELECT COUNT(*) FROM gaps_archived')"
                                   ".fetchone()[0])", db_abs],
                                  capture_output=True, text=True, encoding="utf-8").stdout.strip()}

        proc = subprocess.Popen([sys.executable, SERVER, "--port", str(args.port),
                                 "--no-browser"], stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, encoding="utf-8")
        try:
            time.sleep(2.5)
            with urllib.request.urlopen("http://127.0.0.1:%d/api/databases" % args.port,
                                        timeout=8) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            result["9 填写器"] = {"发现库数": len(payload.get("databases", [])),
                              "当前库": payload.get("current"),
                              "工作区": payload.get("workspace")}
        except Exception as exc:  # noqa: BLE001
            result["9 填写器"] = {"错误": "%s: %s" % (type(exc).__name__, exc)}
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        result["清理"] = not os.path.exists(tmp_dir)

    print(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
