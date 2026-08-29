"""Tiny standard-library status page for observing the example worker locally."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, cast

from basamento_synapsys import Synapsys

from .business import ExampleServices


def _payload(worker: Synapsys, services: ExampleServices) -> dict[str, object]:
    processes = [
        {
            "name": process.name,
            "type": process.type,
            "currentState": process.current_state,
            "ackToken": process.ack_token,
            "runId": process.run_id,
        }
        for process in worker.processes
    ]
    return {
        "worker": worker.config.get("worker_name"),
        "registered": len(processes),
        "running": sum(item["currentState"] == "running" for item in processes),
        "failed": sum(item["currentState"] == "failed" for item in processes),
        "processes": processes,
        "business": services.snapshot(),
    }


def _handler(worker: Synapsys, services: ExampleServices) -> type[BaseHTTPRequestHandler]:
    class StatusHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path not in {"/", "/json"}:
                self.send_error(404)
                return
            payload = _payload(worker, services)
            if self.path == "/json":
                body = json.dumps(payload, indent=2).encode("utf-8")
                content_type = "application/json; charset=utf-8"
            else:
                processes = cast(list[dict[str, Any]], payload["processes"])
                rows = "".join(
                    "<tr>"
                    f"<td>{item['name']}</td><td>{item['type']}</td>"
                    f"<td>{item['currentState']}</td><td>{item['ackToken']}</td>"
                    f"<td>{item['runId']}</td>"
                    "</tr>"
                    for item in processes
                )
                html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="2">
<title>Synapsys Python example</title>
<style>body{{font:14px system-ui;margin:2rem}}table{{border-collapse:collapse}}
td,th{{padding:.4rem .7rem;border:1px solid #ccc}}code{{background:#eee;padding:.15rem}}</style>
</head><body><h1>Synapsys Python example</h1>
<p><strong>{payload["registered"]}</strong> registered; <strong>{payload["running"]}</strong>
running; <strong>{payload["failed"]}</strong> failed. JSON is available at <code>/json</code>.</p>
<table><thead><tr><th>Name</th><th>Type</th><th>State</th><th>Ack token</th><th>Run ID</th>
</tr></thead><tbody>{rows}</tbody></table></body></html>"""
                body = html.encode("utf-8")
                content_type = "text/html; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *args: Any) -> None:
            return

    return StatusHandler


def start_status_server(
    worker: Synapsys, services: ExampleServices, port: int
) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", port), _handler(worker, services))
    thread = threading.Thread(
        target=server.serve_forever,
        name="example-status-server",
        daemon=True,
    )
    thread.start()
    return server
