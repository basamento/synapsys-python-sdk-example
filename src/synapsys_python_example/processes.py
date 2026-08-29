"""The 24 process declarations that wire business logic to Synapsys."""

from __future__ import annotations

import queue
import time
from typing import Any, cast

from basamento_synapsys import StopSignal, Synapsys

from .business import ExampleServices
from .logging_utils import process_log


def register_processes(synapsys: Synapsys, services: ExampleServices) -> None:
    """Register twelve Endless and twelve Progressive process examples."""

    # ENDLESS: each invocation keeps running until it observes a stop request.

    @synapsys.endless(name="invoice-poller")
    def invoice_poller(stop: StopSignal) -> None:
        process_log("invoice-poller", "started")
        while not stop.requested:
            found = services.poll_invoices()
            process_log("invoice-poller", f"poll complete, {found} invoice(s) ready")
            stop.wait(2.0)
        process_log("invoice-poller", "stop observed")

    @synapsys.endless(name="payment-reconciler")
    def payment_reconciler(stop: StopSignal) -> None:
        process_log("payment-reconciler", "started with the shared payment service")
        while not stop.requested:
            matched = services.reconcile_payments()
            process_log("payment-reconciler", f"reconciled {matched} payment(s)")
            stop.wait(2.5)
        process_log("payment-reconciler", "stopped")

    @synapsys.endless(name="feed-subscriber")
    def feed_subscriber(stop: StopSignal) -> None:
        process_log("feed-subscriber", "subscribed; waiting up to 10s for an event")
        event_number = 0
        while not stop.wait(10.0):
            event_number += 1
            process_log("feed-subscriber", f"received event {event_number}")
        process_log("feed-subscriber", "blocking wait interrupted by stop")

    def close_cache() -> None:
        released = services.close_cache()
        process_log("cache-warmer", f"on_stop released {released} cached entries")

    @synapsys.endless(name="cache-warmer", on_stop=close_cache)
    def cache_warmer(stop: StopSignal) -> None:
        process_log("cache-warmer", "cache resource opened")
        while not stop.requested:
            entries = services.warm_cache()
            process_log("cache-warmer", f"cache now holds {entries} entries")
            stop.wait(2.0)
        process_log("cache-warmer", "body returning after stop")

    @synapsys.endless(name="session-reaper")
    def session_reaper(stop: StopSignal) -> None:
        process_log("session-reaper", "checking for expired sessions")
        while not stop.requested:
            pass_number = services.next_count("session-reaper-passes")
            process_log("session-reaper", f"reaper pass {pass_number} complete; sleeping 30s")
            stop.wait(30.0)
        process_log("session-reaper", "long wait woke immediately for stop")

    @synapsys.endless(name="metrics-publisher")
    def metrics_publisher(stop: StopSignal) -> None:
        process_log("metrics-publisher", "publishing one log line per second")
        while not stop.requested:
            sample = services.next_count("metric-samples")
            process_log("metrics-publisher", f"sample={sample} queue={services.work_queue.qsize()}")
            stop.wait(1.0)
        process_log("metrics-publisher", "publisher stopped")

    @synapsys.endless(name="dead-letter-retrier")
    def dead_letter_retrier(stop: StopSignal) -> None:
        process_log("dead-letter-retrier", "started; handled failures do not fail the process")
        while not stop.requested:
            attempt = services.next_count("dead-letter-attempts")
            try:
                if attempt % 4 == 0:
                    raise ConnectionError("simulated dead-letter store timeout")
                process_log("dead-letter-retrier", f"retry attempt {attempt} succeeded")
            except ConnectionError as error:
                process_log("dead-letter-retrier", f"handled: {error}", error=True)
            stop.wait(1.5)
        process_log("dead-letter-retrier", "stopped cleanly")

    def legacy_nightly_sync(stop: StopSignal) -> None:
        process_log("legacy-nightly-sync", "legacy function registered by reference")
        while not stop.requested:
            total = services.legacy_sync_batch()
            process_log("legacy-nightly-sync", f"legacy records synced={total}")
            stop.wait(4.0)
        process_log("legacy-nightly-sync", "legacy loop stopped")

    synapsys.register_endless(legacy_nightly_sync, name="legacy-nightly-sync")

    @synapsys.endless(name="queue-consumer")
    def queue_consumer(stop: StopSignal) -> None:
        process_log("queue-consumer", "waiting on a standard-library Queue")
        while not stop.requested:
            try:
                message = services.work_queue.get(timeout=1.0)
            except queue.Empty:
                process_log("queue-consumer", "queue empty; still listening")
                continue
            process_log("queue-consumer", f"handled {message}")
            services.work_queue.task_done()
        process_log("queue-consumer", "consumer stopped")

    @synapsys.endless(name="temperature-monitor")
    def temperature_monitor(stop: StopSignal) -> None:
        process_log("temperature-monitor", "sensor monitor started")
        while not stop.requested:
            reading = 18.0 + (services.next_count("temperature-readings") % 17) / 2
            process_log("temperature-monitor", f"temperature={reading:.1f}C")
            stop.wait(3.0)
        process_log("temperature-monitor", "monitor stopped")

    @synapsys.endless(name="slow-stopper")
    def slow_stopper(stop: StopSignal) -> None:
        process_log("slow-stopper", "started; each work chunk is non-interruptible for ~8s")
        chunk = 0
        while not stop.requested:
            chunk += 1
            process_log("slow-stopper", f"chunk {chunk} started")
            time.sleep(8.0)
            process_log("slow-stopper", f"chunk {chunk} finished")
        process_log("slow-stopper", "stop taken at a safe point")

    @synapsys.endless(name="crashing-watchdog")
    def crashing_watchdog(stop: StopSignal) -> None:
        attempt = services.next_count("watchdog-runs")
        process_log("crashing-watchdog", f"run {attempt} started")
        if attempt % 3 != 0:
            process_log("crashing-watchdog", "failing deliberately", error=True)
            raise RuntimeError("simulated watchdog crash; every third run survives")
        while not stop.requested:
            process_log("crashing-watchdog", "healthy on this run")
            stop.wait(2.0)
        process_log("crashing-watchdog", "surviving run stopped")

    # PROGRESSIVE: each invocation runs once and naturally returns to idle.

    @synapsys.progressive(name="monthly-report")
    def monthly_report(stop: StopSignal) -> None:
        process_log("monthly-report", "building five report sections")
        for section in range(1, 6):
            stop.raise_if_requested()
            services.simulate_io(0.5)
            process_log("monthly-report", f"section {section}/5 complete")
        process_log("monthly-report", "report complete")

    @synapsys.progressive(name="bulk-import")
    def bulk_import(stop: StopSignal) -> None:
        process_log("bulk-import", "importing 40 rows; cancellable between rows")
        for row in range(1, 41):
            stop.raise_if_requested()
            services.simulate_io(0.1)
            if row % 5 == 0:
                process_log("bulk-import", f"row {row}/40 imported")
        process_log("bulk-import", "import complete")

    @synapsys.progressive(name="flaky-importer")
    def flaky_importer() -> None:
        attempt = services.next_count("flaky-import-runs")
        process_log("flaky-importer", f"attempt {attempt}; every third attempt succeeds")
        services.simulate_io(0.5)
        if attempt % 3 != 0:
            process_log("flaky-importer", "upstream rejected the import", error=True)
            raise RuntimeError("simulated upstream import failure")
        process_log("flaky-importer", "import succeeded")

    @synapsys.progressive(name="checksum-cruncher")
    def checksum_cruncher(stop: StopSignal) -> None:
        process_log("checksum-cruncher", "starting CPU-bound checksum rounds")
        checksum = 0.0
        for round_number in range(1, 16):
            stop.raise_if_requested()
            checksum += services.burn_cpu(80_000)
            process_log("checksum-cruncher", f"round {round_number}/15 complete")
        process_log("checksum-cruncher", f"checksum={checksum:.3f}")

    @synapsys.progressive(name="data-migration")
    def data_migration(stop: StopSignal) -> None:
        process_log("data-migration", "migrating 20 partitions")
        for partition in range(1, 21):
            stop.raise_if_requested()
            services.simulate_io(0.5)
            process_log("data-migration", f"partition {partition}/20 migrated")
        process_log("data-migration", "migration complete")

    @synapsys.progressive(name="pdf-renderer")
    def pdf_renderer(stop: StopSignal) -> None:
        process_log("pdf-renderer", "rendering eight pages with mixed I/O and CPU work")
        for page in range(1, 9):
            stop.raise_if_requested()
            services.simulate_io(0.15)
            services.burn_cpu(25_000)
            process_log("pdf-renderer", f"page {page}/8 rendered")
        process_log("pdf-renderer", "document ready")

    @synapsys.progressive(name="search-index-rebuild")
    def search_index_rebuild(stop: StopSignal) -> None:
        process_log("search-index-rebuild", "rebuilding ten search shards")
        for shard in range(1, 11):
            stop.raise_if_requested()
            services.burn_cpu(100_000)
            process_log("search-index-rebuild", f"shard {shard}/10 indexed")
        process_log("search-index-rebuild", "index rebuild complete")

    @synapsys.progressive(name="email-blast")
    def email_blast(stop: StopSignal) -> None:
        process_log("email-blast", "sending 60 messages")
        for recipient in range(1, 61):
            stop.raise_if_requested()
            services.simulate_io(0.05)
            if recipient % 10 == 0:
                process_log("email-blast", f"sent {recipient}/60")
        process_log("email-blast", "campaign complete")

    def close_archive_scratch() -> None:
        if services.close_archive_scratch():
            process_log("archive-compactor", "on_stop released scratch space")

    @synapsys.progressive(name="archive-compactor", on_stop=close_archive_scratch)
    def archive_compactor(stop: StopSignal) -> None:
        services.open_archive_scratch()
        process_log("archive-compactor", "scratch opened; compacting 15 segments")
        for segment in range(1, 16):
            stop.raise_if_requested()
            services.simulate_io(0.2)
            process_log("archive-compactor", f"segment {segment}/15 compacted")
        services.close_archive_scratch()
        process_log("archive-compactor", "scratch released normally")

    @synapsys.progressive(name="tax-calculator")
    def tax_calculator(stop: StopSignal) -> None:
        process_log("tax-calculator", "calculating tax for 25 accounts")
        total = 0.0
        for account in range(1, 26):
            stop.raise_if_requested()
            total += services.calculate_tax(account)
            if account % 5 == 0:
                process_log("tax-calculator", f"account {account}/25 calculated")
        process_log("tax-calculator", f"tax total={total:.2f}")

    @synapsys.progressive(name="payroll-exporter")
    def payroll_exporter() -> None:
        process_log("payroll-exporter", "starting export that fails unexpectedly", error=True)
        missing_employee = cast(Any, None)
        # Deliberate unanticipated failure shape, equivalent to a null dereference.
        _ = missing_employee.payroll_id

    @synapsys.progressive(name="uncancellable-batch")
    def uncancellable_batch() -> None:
        process_log("uncancellable-batch", "20 steps with no StopSignal checks")
        for step in range(1, 21):
            services.simulate_io(0.3)
            process_log("uncancellable-batch", f"step {step}/20 complete")
        process_log("uncancellable-batch", "batch returned on its own")
