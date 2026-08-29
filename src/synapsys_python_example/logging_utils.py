"""Small console logger whose output is captured per Synapsys execution."""

from __future__ import annotations

import sys
from datetime import datetime


def process_log(process_name: str, message: str, *, error: bool = False) -> None:
    """Write a complete line to stdout or stderr for SDK console capture."""
    timestamp = datetime.now().astimezone().strftime("%H:%M:%S.%f")[:-3]
    stream = sys.stderr if error else sys.stdout
    print(f"{timestamp}  {process_name:<22}  {message}", file=stream, flush=True)


def app_log(message: str) -> None:
    """Write application lifecycle output, which is not attached to a process run."""
    timestamp = datetime.now().astimezone().strftime("%H:%M:%S.%f")[:-3]
    print(f"{timestamp}  application             {message}", flush=True)
