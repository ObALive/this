# -*- coding: utf-8 -*-
"""缺口决策库填写器：本地 HTTP 服务。

用法：
    python decision_server.py                       # 默认端口 8777，自动打开浏览器
    python decision_server.py --port 8900 --no-browser
    python decision_server.py --db Dsh/Output/<任务>/<库文件>.sqlite

功能：
    GET  /api/databases          列出工作区内全部决策库与裁定进度
    GET  /api/questions          返回选中库的全部缺口、候选与裁定状态
    POST /api/decision           写入一项裁定
    POST /api/clear              清空一项裁定
    GET  /api/export             把当前裁定导出为 Markdown 便于复核
    GET  /                       返回单页前端

安全：仅监听本机回环地址；库路径限制在工作区之内。
位置约定：本文件与 index.html、app.css、app.js 同处 `Dsh/Tool/缺口决策系统/填写器/`，
工作区根目录由共用模块从工具目录向上定位。
"""
import argparse
import json
import os
import sqlite3
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "建库工具"))
from db_locator import WORKSPACE, discover_databases, resolve_db, to_rel  # noqa: E402

WEB_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PORT = 8777
STATUS_PENDING = "待裁定"
STATUS_CHOSEN = "已选候选"
STATUS_CUSTOM = "自定义方案"


def describe_database(path):
    """读出一个决策库的自述信息；结构不符时返回 None。"""
    if not os.path.isfile(path):
        return None
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % path.replace("\\", "/"), uri=True)
        cur = conn.cursor()
        tables = {r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"gaps", "solution_options", "decisions"} <= tables:
            conn.close()
            return None
        total = cur.execute("SELECT COUNT(*) FROM gaps").fetchone()[0]
        decided = cur.execute(
            "SELECT COUNT(*) FROM decisions WHERE status <> ?", (STATUS_PENDING,)).fetchone()[0]
        title = None
        if "meta" in tables:
            row = cur.execute("SELECT value FROM meta WHERE key='title'").fetchone()
            title = row[0] if row else None
        conn.close()
    except sqlite3.Error:
        return None
    name = os.path.splitext(os.path.basename(path))[0]
    return {
        "path": to_rel(path),
        "name": name,
        "title": title or name,
        "gaps": total,
        "decided": decided,
        "pending": total - decided,
    }


def list_databases():
    records = []
    for rel in discover_databases():
        try:
            record = describe_database(resolve_db(rel))
        except ValueError:
            continue
        if record:
            records.append(record)
    return records


def load_questions(db_path):
    conn = sqlite3.connect("file:%s?mode=ro" % db_path.replace("\\", "/"), uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    gaps = []
    for row in cur.execute(
            "SELECT gap_id, title, level, status, source_ref, impact_scope,"
            " close_condition, owner, priority_round FROM gaps ORDER BY gap_id"):
        gaps.append({
            "gap_id": row["gap_id"], "title": row["title"], "level": row["level"],
            "gap_status": row["status"], "source_ref": row["source_ref"],
            "impact_scope": row["impact_scope"], "close_condition": row["close_condition"],
            "owner": row["owner"], "priority_round": row["priority_round"] or "",
            "options": [],
        })
    index = {g["gap_id"]: g for g in gaps}
    for row in cur.execute(
            "SELECT option_id, gap_id, seq, option_label, summary_title, detail, tradeoff,"
            " is_recommended, is_selected, is_custom FROM solution_options"
            " ORDER BY gap_id, seq"):
        gap = index.get(row["gap_id"])
        if gap is None:
            continue
        gap["options"].append({
            "option_id": row["option_id"], "label": row["option_label"], "seq": row["seq"],
            "title": row["summary_title"], "detail": row["detail"],
            "tradeoff": row["tradeoff"], "recommended": bool(row["is_recommended"]),
            "selected": bool(row["is_selected"]), "custom": bool(row["is_custom"]),
        })
    decisions = {}
    for row in cur.execute(
            "SELECT gap_id, chosen_option_id, answer_text, decision_basis, extra_requirement,"
            " status, filled_at, needs_followup FROM decisions"):
        decisions[row["gap_id"]] = {
            "chosen_option_id": row["chosen_option_id"] or "",
            "answer_text": row["answer_text"] or "",
            "decision_basis": row["decision_basis"] or "",
            "extra_requirement": row["extra_requirement"] or "",
            "status": row["status"] or STATUS_PENDING,
            "filled_at": row["filled_at"] or "",
            "needs_followup": bool(row["needs_followup"]),
        }
    conn.close()
    empty = {"chosen_option_id": "", "answer_text": "", "decision_basis": "",
             "extra_requirement": "", "status": STATUS_PENDING, "filled_at": "",
             "needs_followup": False}
    for gap in gaps:
        gap["decision"] = decisions.get(gap["gap_id"], dict(empty))
    return gaps


def save_decision(db_path, payload):
    gap_id = (payload.get("gap_id") or "").strip()
    if not gap_id:
        raise ValueError("缺少 gap_id")
    option_id = (payload.get("chosen_option_id") or "").strip() or None
    answer_text = (payload.get("answer_text") or "").strip() or None
    basis = (payload.get("decision_basis") or "").strip() or None
    extra = (payload.get("extra_requirement") or "").strip() or None

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    if cur.execute("SELECT 1 FROM gaps WHERE gap_id=?", (gap_id,)).fetchone() is None:
        conn.close()
        raise ValueError("缺口不存在：%s" % gap_id)
    if option_id:
        row = cur.execute("SELECT gap_id FROM solution_options WHERE option_id=?",
                          (option_id,)).fetchone()
        if row is None or row[0] != gap_id:
            conn.close()
            raise ValueError("候选不属于该缺口：%s" % option_id)

    if answer_text:
        status = STATUS_CUSTOM
    elif option_id:
        status = STATUS_CHOSEN
    else:
        status = STATUS_PENDING
    followup = 1 if (option_id and answer_text) else 0
    cur.execute(
        "UPDATE decisions SET chosen_option_id=?, answer_text=?, decision_basis=?,"
        " extra_requirement=?, status=?, filled_at=datetime('now','localtime'),"
        " needs_followup=? WHERE gap_id=?",
        (option_id, answer_text, basis, extra, status, followup, gap_id))
    cur.execute("UPDATE solution_options SET is_selected=0 WHERE gap_id=?", (gap_id,))
    if option_id and status == STATUS_CHOSEN:
        cur.execute("UPDATE solution_options SET is_selected=1 WHERE option_id=?", (option_id,))
    conn.commit()
    conn.close()
    return {"gap_id": gap_id, "status": status, "chosen_option_id": option_id or "",
            "needs_followup": bool(followup)}


def clear_decision(db_path, gap_id):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "UPDATE decisions SET chosen_option_id=NULL, answer_text=NULL, decision_basis=NULL,"
        " extra_requirement=NULL, status=?, filled_at=NULL, needs_followup=0 WHERE gap_id=?",
        (STATUS_PENDING, gap_id))
    cur.execute("UPDATE solution_options SET is_selected=0 WHERE gap_id=?", (gap_id,))
    conn.commit()
    conn.close()
    return {"gap_id": gap_id, "status": STATUS_PENDING}


def export_markdown(db_path, rel_path):
    gaps = load_questions(db_path)
    decided = [g for g in gaps if g["decision"]["status"] != STATUS_PENDING]
    label_of = {o["option_id"]: o["label"] for g in gaps for o in g["options"]}
    lines = [
        "# 裁定结果（%s）" % os.path.basename(rel_path), "",
        "| 项目 | 内容 |", "| --- | --- |",
        "| 数据来源 | `%s` |" % rel_path,
        "| 缺口总数 | %d |" % len(gaps),
        "| 已裁定 | %d |" % len(decided),
        "| 未裁定 | %d |" % (len(gaps) - len(decided)),
        "| 导出时间 | %s |" % time.strftime("%Y-%m-%d %H:%M:%S"), "",
        "---", "",
    ]
    for gap in gaps:
        d = gap["decision"]
        if d["status"] == STATUS_PENDING:
            continue
        chosen = label_of.get(d["chosen_option_id"], "")
        lines += ["## %s %s" % (gap["gap_id"], gap["title"]), "",
                  "- 裁定结果：%s%s" % (d["status"],
                                       "（候选 %s）" % chosen if chosen else "")]
        if d["answer_text"]:
            lines.append("- 预期方案：%s" % d["answer_text"])
        if d["decision_basis"]:
            lines.append("- 裁定理由：%s" % d["decision_basis"])
        if d["extra_requirement"]:
            lines.append("- 补充要求：%s" % d["extra_requirement"])
        if d["needs_followup"]:
            lines.append("- 备注：同时填了候选与预期方案，需要复核以哪一项为准")
        lines.append("")
    return "\n".join(lines)


class Handler(BaseHTTPRequestHandler):
    server_version = "GapDecisionSheet/1.0"
    state = {"db": None}

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    def _send(self, code, body, content_type="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        raw = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _json_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _current_db(self, query):
        rel = query.get("db", [None])[0] or self.state.get("db")
        if not rel:
            databases = list_databases()
            if not databases:
                raise ValueError("工作区内没有找到决策库")
            rel = databases[0]["path"]
            self.state["db"] = rel
        return rel, resolve_db(rel)

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        try:
            if parsed.path in ("/", "/index.html", "/app.css", "/app.js"):
                return self._serve_static(parsed.path.lstrip("/") or "index.html")
            if parsed.path == "/api/databases":
                return self._send(200, {"databases": list_databases(),
                                        "current": self.state.get("db"),
                                        "workspace": WORKSPACE})
            if parsed.path == "/api/questions":
                rel, path = self._current_db(query)
                self.state["db"] = rel
                return self._send(200, {"db": rel, "questions": load_questions(path)})
            if parsed.path == "/api/export":
                rel, path = self._current_db(query)
                return self._send(200, export_markdown(path, rel),
                                  "text/markdown; charset=utf-8")
            return self._send(404, {"error": "未知路径：%s" % parsed.path})
        except ValueError as exc:
            return self._send(400, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            return self._send(500, {"error": "%s: %s" % (type(exc).__name__, exc)})

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            payload = self._json_body()
            if parsed.path == "/api/select":
                rel = payload.get("db") or ""
                resolve_db(rel)
                self.state["db"] = rel
                return self._send(200, {"db": rel})
            if parsed.path == "/api/decision":
                rel = payload.get("db") or self.state.get("db")
                path = resolve_db(rel)
                self.state["db"] = rel
                return self._send(200, {"ok": True, "decision": save_decision(path, payload)})
            if parsed.path == "/api/clear":
                rel = payload.get("db") or self.state.get("db")
                path = resolve_db(rel)
                gap_id = (payload.get("gap_id") or "").strip()
                if not gap_id:
                    raise ValueError("缺少 gap_id")
                return self._send(200, {"ok": True, "decision": clear_decision(path, gap_id)})
            return self._send(404, {"error": "未知路径：%s" % parsed.path})
        except ValueError as exc:
            return self._send(400, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            return self._send(500, {"error": "%s: %s" % (type(exc).__name__, exc)})

    def _serve_static(self, name):
        path = os.path.join(WEB_DIR, name)
        if not os.path.isfile(path):
            return self._send(404, {"error": "缺少前端文件：%s" % name})
        ctype = {"index.html": "text/html; charset=utf-8",
                 "app.css": "text/css; charset=utf-8",
                 "app.js": "application/javascript; charset=utf-8"}.get(
                     name, "application/octet-stream")
        with open(path, "rb") as fh:
            return self._send(200, fh.read(), ctype)


def main():
    parser = argparse.ArgumentParser(description="缺口决策库填写器")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--db", help="启动时选中的决策库路径")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    databases = list_databases()
    if args.db:
        Handler.state["db"] = to_rel(resolve_db(args.db))
    elif databases:
        Handler.state["db"] = databases[0]["path"]

    httpd = None
    for port in range(args.port, args.port + 12):
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            continue
    if httpd is None:
        print("端口 %d 起的连续 12 个端口都被占用" % args.port)
        raise SystemExit(1)

    url = "http://127.0.0.1:%d/" % httpd.server_address[1]
    print("工作区 :", WORKSPACE)
    print("决策库 :", len(databases), "个")
    for item in databases:
        print("   -", item["path"], "(%d/%d 已裁定)" % (item["decided"], item["gaps"]))
    print("地址   :", url)
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
