"""项目网络图绘制与编辑工具的本机服务。

只监听 127.0.0.1：静态页面 + 网络图 JSON API。
启动： python3 Tool/项目网络图/server.py
"""

from __future__ import annotations

import argparse
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import model as M
import store

STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
    "/graph.js": ("graph.js", "application/javascript; charset=utf-8"),
    "/使用说明.md": ("使用说明.md", "text/plain; charset=utf-8"),
}

LOCK = threading.Lock()
STATE: dict = {"model": None}


def get_model() -> M.Model:
    if STATE["model"] is None:
        STATE["model"] = store.load_or_seed()
    return STATE["model"]


class Handler(BaseHTTPRequestHandler):
    server_version = "ProjectNetwork/1.0"
    protocol_version = "HTTP/1.1"

    # -- 基础 ---------------------------------------------------------------
    def log_message(self, fmt, *args):  # noqa: A003
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def _send(self, status: int, value, content_type: str = "application/json; charset=utf-8") -> None:
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
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(raw)

    def _json_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"请求体不是合法 JSON：{exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("请求体必须是 JSON 对象")
        return data

    def _view(self, log: list[str] | None = None, extra: dict | None = None) -> dict:
        model = get_model()
        payload = {"ok": True, "model": M.serialize(model), "log": log or []}
        if extra:
            payload.update(extra)
        return payload

    # -- 路由 ---------------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            if path in STATIC:
                name, ctype = STATIC[path]
                target = store.TOOL_DIR / name
                if not target.exists():
                    self._send(404, "文件不存在", "text/plain; charset=utf-8")
                    return
                self._send(200, target.read_bytes(), ctype)
                return
            if path == "/api/state":
                with LOCK:
                    self._send(200, self._view(extra={"config": store.info()}))
                return
            if path == "/api/markdown":
                with LOCK:
                    self._send(200, M.to_markdown(get_model()), "text/plain; charset=utf-8")
                return
            self._send(404, {"ok": False, "error": f"未知路径 {path}"})
        except Exception as exc:  # noqa: BLE001
            self._send(400, {"ok": False, "error": str(exc)})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            body = self._json_body()
            with LOCK:
                if path == "/api/op":
                    model = get_model()
                    op = body.get("op", "")
                    result = M.apply_op(model, op, body.get("args", {}))
                    store.save(model, reason=f"操作 {op}" if op else "操作")
                    self._send(200, self._view(log=result.get("log"), extra={k: v for k, v in result.items() if k != "log"}))
                    return
                if path in ("/api/import", "/api/reset"):
                    if path == "/api/import":
                        model = store.import_from(body.get("path"), body.get("text"))
                        reason = "导入任务书"
                    else:
                        model = store.import_from(body.get("path") or store.DEFAULT_SOURCE)
                        reason = "重置网络图"
                    current = get_model()
                    if current.nodes and not model.nodes:
                        if not body.get("allow_empty"):
                            # 现行任务书可能只剩背景说明；不要因为一次误点把库里的网络图清空
                            self._send(
                                400,
                                {
                                    "ok": False,
                                    "error": (
                                        "该来源没有解析到任何编号条目，导入会清空现有网络图"
                                        f"（当前 {len(current.sections)} 条路线 / {len(current.nodes)} 个条目）。"
                                    ),
                                    "need_confirm": "empty_import",
                                },
                            )
                            return
                        # 确认清空：先把当前非空模型存一份快照，保证还能恢复
                        store.snapshot_current(current, reason=f"{reason}前的存档")
                    STATE["model"] = model
                    store.save(model, reason=reason, force_snapshot=True)
                    self._send(200, self._view(extra={"warnings": model.meta.get("warnings", [])}))
                    return
                if path == "/api/export":
                    model = get_model()
                    target, text = store.export_markdown(model, body.get("path"))
                    store.save(model, reason="导出 Markdown", backup=False)
                    self._send(
                        200,
                        self._view(
                            extra={
                                "path": store.relative_to_workspace(target),
                                "markdown": text,
                            }
                        ),
                    )
                    return
                self._send(404, {"ok": False, "error": f"未知接口 {path}"})
        except ValueError as exc:
            self._send(400, {"ok": False, "error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            self._send(500, {"ok": False, "error": f"{type(exc).__name__}: {exc}"})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="项目网络图绘制与编辑工具")
    parser.add_argument("--port", type=int, default=8791, help="监听端口（默认 8791）")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args(argv)

    store.ensure_dirs()
    model = get_model()
    view = M.serialize(model)
    print(f"工作区：{store.WORKSPACE}", flush=True)
    print(f"数据文件：{store.DB_FILE}", flush=True)
    print(
        f"当前网络图：{view['stats']['sections']} 条开发路线 / {view['stats']['nodes']} 个条目 / {view['stats']['edges']} 条依赖边",
        flush=True,
    )
    if view["stats"]["errors"]:
        print(f"校验：{view['stats']['errors']} 个阻塞问题需要处理", flush=True)

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.daemon_threads = True
    url = f"http://{args.host}:{args.port}/"
    print(f"访问地址：{url}（Ctrl+C 停止）", flush=True)
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
