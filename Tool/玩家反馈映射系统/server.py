"""只监听本机的反馈映射库浏览与编辑服务。"""

from __future__ import annotations

import argparse
import json
import secrets
import sqlite3
import webbrowser
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse, parse_qs

import database as db


STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
}


class LocalHTTPServer(ThreadingHTTPServer):
    daemon_threads = True


class Handler(BaseHTTPRequestHandler):
    server_version = "FeedbackMap/1.0"

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def _send(self, status: int, value, content_type: str = "application/json; charset=utf-8"):
        if isinstance(value, (dict, list)):
            raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
        elif isinstance(value, str):
            raw = value.encode("utf-8")
        else:
            raw = value
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(raw)

    def _host_ok(self) -> bool:
        host = self.headers.get("Host", "")
        port = self.server.server_address[1]
        return host in {f"127.0.0.1:{port}", f"localhost:{port}"}

    def _write_ok(self) -> bool:
        if self.headers.get("X-Tool-Token") != self.server.edit_token:
            return False
        origin = self.headers.get("Origin")
        port = self.server.server_address[1]
        return origin is None or origin in {
            f"http://127.0.0.1:{port}", f"http://localhost:{port}"
        }

    def _body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError as exc:
            raise ValueError("缺少有效的 Content-Length") from exc
        if length < 0 or length > 1_000_000:
            raise ValueError("请求正文最多 1 MB")
        try:
            result = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("请求正文必须是 UTF-8 JSON") from exc
        if not isinstance(result, dict):
            raise ValueError("请求正文必须是 JSON 对象")
        return result

    def _route(self, method: str):
        if not self._host_ok():
            return self._send(403, {"error": "只接受本机访问"})
        if method != "GET" and not self._write_ok():
            return self._send(403, {"error": "编辑令牌或来源无效"})
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if method == "GET" and path in STATIC:
                name, content_type = STATIC[path]
                return self._send(200, (db.TOOL_DIR / name).read_bytes(), content_type)
            if method == "GET" and path == "/api/config":
                return self._send(200, {"database": str(self.server.db_path),
                                        "edit_token": self.server.edit_token})
            with closing(db.connect(self.server.db_path)) as con:
                if method == "GET" and path == "/api/topics":
                    q = parse_qs(parsed.query).get("q", [""])[0]
                    return self._send(200, {"topics": db.list_topics(con, q[:200])})
                if method == "GET" and path == "/api/export":
                    return self._send(200, db.export_data(con))
                if method == "POST" and path == "/api/topics":
                    return self._send(201, db.create_topic(con, self._body()))
                if path.startswith("/api/topics/"):
                    parts = path.split("/")
                    topic_id = unquote(parts[3]) if len(parts) > 3 else ""
                    if len(parts) == 4:
                        if method == "GET":
                            item = db.get_topic(con, topic_id)
                            return self._send(200, item) if item else self._send(404, {"error": "主题不存在"})
                        if method == "PUT":
                            item = db.update_topic(con, topic_id, self._body())
                            return self._send(200, item) if item else self._send(404, {"error": "主题不存在"})
                        if method == "DELETE":
                            deleted = db.delete_topic(con, topic_id)
                            return self._send(200, {"deleted": True}) if deleted else self._send(404, {"error": "主题不存在"})
                    if len(parts) == 5 and parts[4] == "mappings" and method == "POST":
                        if db.get_topic(con, topic_id) is None:
                            return self._send(404, {"error": "主题不存在"})
                        return self._send(201, db.create_mapping(con, topic_id, self._body()))
                if path.startswith("/api/mappings/"):
                    parts = path.split("/")
                    if len(parts) == 4:
                        try:
                            mapping_id = int(parts[3])
                        except ValueError as exc:
                            raise ValueError("映射编号必须是整数") from exc
                        if method == "PUT":
                            item = db.update_mapping(con, mapping_id, self._body())
                            return self._send(200, item) if item else self._send(404, {"error": "映射不存在"})
                        if method == "DELETE":
                            deleted = db.delete_mapping(con, mapping_id)
                            return self._send(200, {"deleted": True}) if deleted else self._send(404, {"error": "映射不存在"})
            return self._send(404, {"error": "未知路径"})
        except ValueError as exc:
            return self._send(400, {"error": str(exc)})
        except sqlite3.IntegrityError as exc:
            return self._send(409, {"error": f"编号重复或关联约束失败：{exc}"})
        except FileNotFoundError as exc:
            return self._send(404, {"error": str(exc)})
        except Exception as exc:
            self.log_error("unexpected error: %r", exc)
            return self._send(500, {"error": "服务发生内部错误，请查看终端日志"})

    def do_GET(self):
        self._route("GET")

    def do_POST(self):
        self._route("POST")

    def do_PUT(self):
        self._route("PUT")

    def do_DELETE(self):
        self._route("DELETE")


def main() -> None:
    parser = argparse.ArgumentParser(description="玩家反馈映射数据库浏览与编辑器")
    parser.add_argument("--db", type=Path, default=db.DEFAULT_DB, help="工作区内的 SQLite 数据库")
    parser.add_argument("--port", type=int, default=8788, help="本机端口，默认 8788")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()
    db_path = args.db.resolve()
    if not db_path.is_relative_to(db.WORKSPACE):
        parser.error("数据库必须位于当前工作区内")
    if not db_path.is_file():
        parser.error(f"数据库不存在：{db_path}；先运行 init_db.py")
    with db.connect(db_path) as con:
        con.execute("SELECT topic_id FROM topics LIMIT 1")
    server = LocalHTTPServer(("127.0.0.1", args.port), Handler)
    server.db_path = db_path
    server.edit_token = secrets.token_urlsafe(32)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"数据库：{db_path}")
    print(f"地址：{url}")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
