"""Anonymous, per-unlock summaries of outbound EVM indexer requests."""

import logging
import threading
import time
import traceback
from collections import Counter, deque
from typing import TYPE_CHECKING, Final
from uuid import uuid4

from rotkehlchen.concurrency import Task
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.sigil import create_sigil_events_batch, submit_sigil_batch
from rotkehlchen.utils.misc import is_production

if TYPE_CHECKING:
    from rotkehlchen.sigil import SigilBatchEntry
    from rotkehlchen.types import ChainID

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

INDEXER_ANALYTICS_INTERVAL: Final = 2 * 60 * 60
INDEXER_ANALYTICS_RETRY_DELAY: Final = 5 * 60
INDEXER_ANALYTICS_MAX_ATTEMPTS: Final = 3
INDEXER_ANALYTICS_TIMEOUT: Final = 5
INDEXER_ANALYTICS_CLOSE_TIMEOUT: Final = 3
IndexerRequestKey = tuple[str, int, str]


class IndexerStats:
    """Count indexer HTTP calls; upload deltas without holding up queries."""

    def __init__(self) -> None:
        self.session_id = uuid4().hex
        self._lock = threading.Lock()
        self._upload_lock = threading.Lock()
        self._counts: Counter[IndexerRequestKey] = Counter()
        self._pending: deque[list[SigilBatchEntry]] = deque()
        self._window_start = time.monotonic()
        self._window = 0
        self._next_retry = 0.0
        self._failed_attempts = 0
        self._worker: Task | None = None
        self._close_worker: Task | None = None
        self._close_deadline: float | None = None
        self._closed = False

    @staticmethod
    def _has_consent() -> bool:
        return is_production() and CachedSettings().get_entry('submit_usage_analytics') is True

    @staticmethod
    def _log_upload_failure(task: Task) -> None:
        if task.exc_info is not None:
            log.error(
                '%s failed',
                task.task_name,
                traceback=''.join(traceback.format_exception(*task.exc_info)),
            )

    def _clear(self) -> None:
        """Called with _lock held."""
        self._counts.clear()
        self._pending.clear()
        self._window_start = time.monotonic()
        self._next_retry = 0.0
        self._failed_attempts = 0

    def discard(self) -> None:
        """Drop unsent data without waiting for an upload already underway."""
        with self._lock:
            self._clear()

    def record(self, indexer: str, chain_id: ChainID, endpoint: str) -> None:
        if self._has_consent() is False:
            return

        with self._lock:
            # Opt-out may have cleared the counters after the fast-path check above.
            if self._closed is False and self._has_consent():
                self._counts[indexer, chain_id.serialize(), endpoint] += 1

    def _queue_window(self, final: bool) -> None:
        """Called with _lock held. Advance the clock without queuing empty windows."""
        now = time.monotonic()
        if len(self._counts) == 0:
            self._window_start = now
            return

        self._window += 1
        by_indexer: dict[str, dict[str, dict[str, int]]] = {}
        for (indexer, chain_id, endpoint), count in sorted(self._counts.items()):
            by_indexer.setdefault(indexer, {}).setdefault(str(chain_id), {})[endpoint] = count
        seconds = now - self._window_start
        self._pending.append(create_sigil_events_batch([(
            'indexer_requests',
            '/backend/indexers',
            {
                'session_id': self.session_id,
                'window': self._window,
                'requests': sum(self._counts.values()),
                'seconds': round(seconds),
                'final': final,
                'by_indexer': by_indexer,
            },
        )]))
        self._counts.clear()
        self._window_start = now

    def _send_pending(self, deadline: float | None = None) -> None:
        wait_seconds = -1 if deadline is None else max(0.0, deadline - time.monotonic())
        if self._upload_lock.acquire(timeout=wait_seconds) is False:
            if deadline is not None:
                log.debug('Indexer analytics close upload timed out waiting for an active upload')
            return

        try:
            while self._has_consent():
                with self._lock:
                    if (
                        self._closed and
                        deadline is None and
                        (deadline := self._close_deadline) is None
                    ):
                        return
                    if len(self._pending) == 0:
                        return
                    batch = self._pending[0]

                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    return
                timeout = INDEXER_ANALYTICS_TIMEOUT if remaining is None else min(
                    INDEXER_ANALYTICS_TIMEOUT, remaining,
                )
                try:
                    submitted = submit_sigil_batch(batch=batch, timeout=timeout)
                except Exception:  # pylint: disable=broad-except
                    log.exception('Failed to submit indexer usage analytics')
                    submitted = False
                if submitted is False:
                    with self._lock:
                        if self._pending and self._pending[0] is batch:
                            self._failed_attempts += 1
                            if self._failed_attempts >= INDEXER_ANALYTICS_MAX_ATTEMPTS:
                                self._pending.popleft()
                                self._failed_attempts = 0
                                self._next_retry = 0.0
                                log.debug('Dropping indexer analytics after repeated failures')
                                continue
                            self._next_retry = time.monotonic() + INDEXER_ANALYTICS_RETRY_DELAY
                    log.debug('Could not submit indexer usage analytics; will retry later')
                    return

                with self._lock:
                    if self._pending and self._pending[0] is batch:
                        self._pending.popleft()
                        self._failed_attempts = 0
                        self._next_retry = 0.0

            with self._lock:
                self._clear()
        finally:
            self._upload_lock.release()

    def maybe_flush(self) -> None:
        """Called from the backend main loop; network I/O runs in a worker thread."""
        if self._has_consent() is False:
            return

        with self._lock:
            if self._closed:
                return
            now = time.monotonic()
            if now - self._window_start >= INDEXER_ANALYTICS_INTERVAL:
                self._queue_window(final=False)
            if (
                len(self._pending) == 0 or
                now < self._next_retry or
                (self._worker is not None and self._worker.dead is False)
            ):
                return

            worker = Task(name='indexer analytics upload', target=self._send_pending)
            worker.add_done_callback(self._log_upload_failure)
            self._worker = worker.start()

    def start_close(self) -> None:
        """Start the final upload while the user's consent is still available."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            if self._has_consent() is False:
                self._clear()
                return
            self._queue_window(final=True)
            if len(self._pending) == 0:
                return
            self._close_deadline = time.monotonic() + INDEXER_ANALYTICS_CLOSE_TIMEOUT
            worker = Task(
                name='indexer analytics close upload',
                target=self._send_pending,
                args=(self._close_deadline,),
            )
            worker.add_done_callback(self._log_upload_failure)
            try:
                self._close_worker = worker.start()
            except RuntimeError:
                log.exception('Failed to start indexer analytics close upload')

    def wait_for_close(self) -> None:
        """Wait only for the time left after concurrent logout cleanup."""
        if self._close_worker is not None and self._close_deadline is not None:
            self._close_worker.join(timeout=max(0, self._close_deadline - time.monotonic()))

    def close(self) -> None:
        self.start_close()
        self.wait_for_close()
