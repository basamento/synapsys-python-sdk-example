import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import urlopen

from synapsys_python_example import build_application
from synapsys_python_example.env import load_env
from synapsys_python_example.status_server import start_status_server

ENDLESS_NAMES = {
    "invoice-poller",
    "payment-reconciler",
    "feed-subscriber",
    "cache-warmer",
    "session-reaper",
    "metrics-publisher",
    "dead-letter-retrier",
    "legacy-nightly-sync",
    "queue-consumer",
    "temperature-monitor",
    "slow-stopper",
    "crashing-watchdog",
}

PROGRESSIVE_NAMES = {
    "monthly-report",
    "bulk-import",
    "flaky-importer",
    "checksum-cruncher",
    "data-migration",
    "pdf-renderer",
    "search-index-rebuild",
    "email-blast",
    "archive-compactor",
    "tax-calculator",
    "payroll-exporter",
    "uncancellable-batch",
}


def test_registers_twelve_processes_of_each_type() -> None:
    application = build_application(enabled=False)
    endless = {
        process.name for process in application.worker.processes if process.type == "endless"
    }
    progressive = {
        process.name for process in application.worker.processes if process.type == "progressive"
    }

    assert endless == ENDLESS_NAMES
    assert progressive == PROGRESSIVE_NAMES
    assert len(application.worker.processes) == 24


def test_status_endpoint_reports_all_processes() -> None:
    application = build_application(enabled=False)
    server = start_status_server(application.worker, application.services, 0)
    try:
        with urlopen(f"http://127.0.0.1:{server.server_port}/json", timeout=2) as response:
            payload = json.load(response)
    finally:
        server.shutdown()
        server.server_close()

    assert payload["registered"] == 24
    assert payload["running"] == 0
    assert payload["failed"] == 0


def test_env_file_does_not_override_exported_values(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("EXAMPLE_ONE=file\nEXAMPLE_TWO='quoted value'\n", encoding="utf-8")
    monkeypatch.setenv("EXAMPLE_ONE", "shell")
    monkeypatch.delenv("EXAMPLE_TWO", raising=False)

    load_env(env_file)

    assert os.environ["EXAMPLE_ONE"] == "shell"
    assert os.environ["EXAMPLE_TWO"] == "quoted value"


class LoggingCoreHandler(BaseHTTPRequestHandler):
    payloads = []
    received_logs = threading.Event()

    def do_GET(self) -> None:
        self.send_response(200 if self.path == "/api/health" else 404)
        self.end_headers()

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length))
        self.payloads.append(payload)
        if payload.get("logs"):
            self.received_logs.set()
        response = {
            "processes": [
                {
                    "name": "tax-calculator",
                    "desiredState": "running",
                    "desiredToken": 1,
                    "runId": 424_242,
                }
            ]
        }
        body = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *args) -> None:
        return


def test_process_output_is_sent_to_core(monkeypatch) -> None:
    LoggingCoreHandler.payloads = []
    LoggingCoreHandler.received_logs.clear()
    core = ThreadingHTTPServer(("127.0.0.1", 0), LoggingCoreHandler)
    core_thread = threading.Thread(target=core.serve_forever, daemon=True)
    core_thread.start()
    monkeypatch.setenv("SYNAPSYS_CORE_URL", f"http://127.0.0.1:{core.server_port}")
    monkeypatch.setenv("SYNAPSYS_CORE_TOKEN", "example-test-token")
    monkeypatch.setenv("SYNAPSYS_HEARTBEAT_INTERVAL", "1s")
    application = build_application()

    application.worker.start()
    try:
        assert LoggingCoreHandler.received_logs.wait(3)
    finally:
        application.worker.stop()
        core.shutdown()
        core.server_close()
        core_thread.join(2)

    logs = [entry for payload in LoggingCoreHandler.payloads for entry in payload["logs"]]
    assert logs
    assert {entry["processName"] for entry in logs} == {"tax-calculator"}
    assert {entry["runId"] for entry in logs} == {424_242}
    assert any("calculating tax" in entry["message"] for entry in logs)
