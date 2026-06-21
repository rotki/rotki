from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from rotkehlchen.types import SupportedBlockchain, Timestamp

# Safety net: even if some invalidation site is ever missed, re-scan a chain that was
# marked clean once this many seconds have passed. Event-based invalidation
# (mark_*_dirty) keeps the common "new transactions arrived" case responsive; this only
# bounds the worst-case latency so a pending queue can never get permanently stuck.
PENDING_TX_RESCAN_AFTER: Final = 300


class PendingTransactionsTracker:
    """In-memory, per-chain signal of whether transactions may be pending receipt
    fetching or decoding.

    The periodic task scheduler probes the DB every few seconds to decide whether to
    schedule receipt fetching / transaction decoding. Those probes are full-table scans
    (there is no chain_id index on evm_transactions), so re-running them on every tick of
    an already synced wallet is pure waste. This tracker lets a probe skip the scan for a
    chain that was found empty on a recent scan and has not been touched since.

    Semantics: a chain whose last clean scan is recent (and that has not been invalidated
    since) is skipped. Inserts/deletes that can create pending work invalidate the chain so
    the next tick scans it again. State starts empty, so every chain is scanned until
    proven clean (conservative - never skips work that may exist).

    Lives on the (per-user) DBHandler so both the DB write paths that create work and the
    scheduler that drains it share a single instance without the DB layer depending on the
    task manager.
    """

    def __init__(self) -> None:
        # chain -> timestamp of the most recent scan that found no pending work
        self.receipts_clean_ts: dict[SupportedBlockchain, Timestamp] = {}
        self.decoding_clean_ts: dict[SupportedBlockchain, Timestamp] = {}

    def should_scan_receipts(self, blockchain: SupportedBlockchain, now: Timestamp) -> bool:
        return now - self.receipts_clean_ts.get(blockchain, 0) > PENDING_TX_RESCAN_AFTER

    def should_scan_decoding(self, blockchain: SupportedBlockchain, now: Timestamp) -> bool:
        return now - self.decoding_clean_ts.get(blockchain, 0) > PENDING_TX_RESCAN_AFTER

    def mark_receipts_clean(self, blockchain: SupportedBlockchain, now: Timestamp) -> None:
        self.receipts_clean_ts[blockchain] = now

    def mark_decoding_clean(self, blockchain: SupportedBlockchain, now: Timestamp) -> None:
        self.decoding_clean_ts[blockchain] = now

    def mark_receipts_dirty(self, blockchain: SupportedBlockchain) -> None:
        """Signal that `blockchain` may now have transactions missing their receipt."""
        self.receipts_clean_ts.pop(blockchain, None)

    def mark_decoding_dirty(self, blockchain: SupportedBlockchain) -> None:
        """Signal that `blockchain` may now have transactions pending decoding."""
        self.decoding_clean_ts.pop(blockchain, None)
