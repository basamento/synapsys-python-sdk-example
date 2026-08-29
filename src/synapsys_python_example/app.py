"""Application entry point and Synapsys lifecycle integration."""

from __future__ import annotations

import os
import signal
import threading
from dataclasses import dataclass
from types import FrameType

from basamento_synapsys import Synapsys

from .business import ExampleServices
from .env import load_env
from .logging_utils import app_log
from .processes import register_processes
from .status_server import start_status_server


@dataclass(frozen=True)
class ExampleApplication:
    worker: Synapsys
    services: ExampleServices


def build_application(*, enabled: bool | None = None) -> ExampleApplication:
    """Create the worker and register every process without starting networking."""
    options: dict[str, object] = {
        "worker_name": os.environ.get("SYNAPSYS_WORKER_NAME", "python-sdk-user-1"),
        "heartbeat_interval": os.environ.get("SYNAPSYS_HEARTBEAT_INTERVAL", "5s"),
    }
    if enabled is not None:
        options["enabled"] = enabled
    worker = Synapsys(**options)
    services = ExampleServices()
    register_processes(worker, services)
    return ExampleApplication(worker=worker, services=services)


def _port() -> int:
    raw = os.environ.get("EXAMPLE_PORT", "3004")
    try:
        port = int(raw)
    except ValueError as error:
        raise ValueError(f"EXAMPLE_PORT must be an integer, got {raw!r}") from error
    if not 0 <= port <= 65_535:
        raise ValueError(f"EXAMPLE_PORT must be between 0 and 65535, got {port}")
    return port


def main() -> None:
    load_env()
    application = build_application()
    worker = application.worker
    shutdown_requested = threading.Event()

    def request_shutdown(signum: int, _frame: FrameType | None) -> None:
        app_log(f"received signal {signum}; shutting down")
        shutdown_requested.set()

    signal.signal(signal.SIGINT, request_shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, request_shutdown)

    server = None
    try:
        worker.start()
        server = start_status_server(worker, application.services, _port())
        actual_port = int(server.server_address[1])
        app_log(f"registered {len(worker.processes)} processes; all idle until Core starts them")
        app_log(f"local status: http://127.0.0.1:{actual_port}")
        while not shutdown_requested.wait(1.0):
            pass
    except KeyboardInterrupt:
        app_log("keyboard interrupt received; shutting down")
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        worker.stop()
        app_log("example stopped")


if __name__ == "__main__":
    main()
