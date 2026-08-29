# Synapsys Python SDK example

A vanilla Python application using the published
[`basamento-synapsys`](https://pypi.org/project/basamento-synapsys/) package. It
registers 24 remotely controlled processes—twelve Endless and twelve Progressive—and
prints execution-scoped output from every process so Synapsys Core's log ingestion can
be exercised.

The business logic in `business.py` does not import Synapsys. `processes.py` is the
thin wiring layer that decorates ordinary Python functions. This separation is the
same adoption pattern used by the Node.js and Spring Boot examples.

Nothing runs automatically. Every process starts idle and only executes after a
start command from Synapsys Core.

## Requirements

- Python 3.9 or later
- A reachable Synapsys Core instance
- A worker token created in Core

## Setup

Create a virtual environment and install the example:

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

On Linux or macOS:

```bash
source .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env
```

Set `SYNAPSYS_CORE_TOKEN` in `.env`. The example already points at the provided
sandbox Core URL; `.env` is ignored by Git and must never be committed.

Then start the application:

```bash
python -m synapsys_python_example
```

Equivalent installed command:

```bash
synapsys-python-example
```

Open <http://127.0.0.1:3004> for a small local status page and
<http://127.0.0.1:3004/json> for the same state as JSON. Sign in to the sandbox Core,
find the `python-sdk-example` worker, and start or stop processes there.

## Process catalogue

### Endless processes

| Process | Demonstrates |
| --- | --- |
| `invoice-poller` | Canonical cooperative polling loop. |
| `payment-reconciler` | Shared ordinary business service. |
| `feed-subscriber` | A long blocking wait interrupted immediately by `StopSignal`. |
| `cache-warmer` | Resource cleanup through `on_stop`. |
| `session-reaper` | A 30-second wait that still stops promptly. |
| `metrics-publisher` | One captured log line per second. |
| `dead-letter-retrier` | Catches expected failures, logs to stderr, and remains running. |
| `legacy-nightly-sync` | Existing function registered explicitly by reference. |
| `queue-consumer` | Blocking standard-library queue consumption. |
| `temperature-monitor` | Small, well-behaved control process. |
| `slow-stopper` | Non-interruptible work that remains `stopping` until a safe point. |
| `crashing-watchdog` | Deliberate failure; every third invocation stays healthy. |

### Progressive processes

| Process | Demonstrates |
| --- | --- |
| `monthly-report` | Normal run-to-completion behavior. |
| `bulk-import` | Cooperative cancellation between imported rows. |
| `flaky-importer` | Deliberate failure; every third invocation succeeds. |
| `checksum-cruncher` | CPU-bound work with cancellation between rounds. |
| `data-migration` | Long multi-step batch suitable for mid-run stopping. |
| `pdf-renderer` | Mixed blocking I/O and CPU work. |
| `search-index-rebuild` | A second concurrent CPU-bound workload. |
| `email-blast` | Sixty small cancellable operations. |
| `archive-compactor` | Progressive `on_stop`, called only when stopped mid-run. |
| `tax-calculator` | Reuse of shared calculation logic. |
| `payroll-exporter` | Deliberate unexpected exception and captured traceback. |
| `uncancellable-batch` | No `StopSignal`; remains `stopping` until it returns. |

The deliberate failures are part of the example. Start them to verify that stderr
and tracebacks reach Core and that the process state becomes `failed` without taking
down the worker.

## Logging behavior

`process_log()` writes complete lines to stdout for informational events and stderr
for error events. The SDK tees those streams to the terminal and attaches output to
the exact Core run. Messages printed outside a managed process are intentionally not
sent as execution logs.

Useful checks:

- Start `metrics-publisher` and watch a continuous stream of log entries in Core.
- Start `dead-letter-retrier`; handled errors appear but the process stays running.
- Start `payroll-exporter`; the error and traceback appear and its state becomes
  `failed`.
- Run multiple processes simultaneously and verify each log line stays attached to
  its own execution.

Do not print passwords, tokens, personal information, or other secrets inside a
managed process: captured console output is transmitted to Core.

## Running without Core

The SDK can be disabled completely while still constructing the application:

```powershell
$env:SYNAPSYS_ENABLED = "false"
python -m synapsys_python_example
```

With the SDK disabled there are no heartbeats, network requests, or console capture.
The local status page still shows all 24 registered processes.

## Tests

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy
```

The test suite runs with Synapsys disabled and never needs Core credentials.

## Layout

```text
src/synapsys_python_example/app.py            lifecycle and entry point
src/synapsys_python_example/business.py       reusable business logic
src/synapsys_python_example/processes.py      24 process declarations
src/synapsys_python_example/logging_utils.py  captured process output
src/synapsys_python_example/status_server.py  local HTML and JSON status
src/synapsys_python_example/env.py             optional dependency-free .env loader
tests/test_example.py                          registration and status tests
```

## License

Apache License 2.0.

