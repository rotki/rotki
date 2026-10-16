from __future__ import annotations

from threading import Lock
from typing import TYPE_CHECKING, Final

from rotkehlchen.constants.timing import DAY_IN_SECONDS

if TYPE_CHECKING:
    from rotkehlchen.types import EVMTxHash, SupportedBlockchain, Timestamp

# Safety net: even if some invalidation site is ever missed, re-scan a chain that was
# marked clean once this many seconds have passed. Event-based invalidation
# (mark_*_dirty) keeps the common "new transactions arrived" case responsive; this only
# bounds the worst-case latency so a pending queue can never get permanently stuck.
PENDING_TX_RESCAN_AFTER: Final = 300
# How long to leave transactions with an unresolved L1 fee out of the periodic decoding
# after one of them failed to resolve, so an indexer outage is not retried on every tick.
UNRESOLVED_L1_FEE_RETRY_AFTER: Final = 600
# How long to leave a transaction out of the periodic decoding after it was deferred since a
# token query failed to reach the nodes, so an outage is not retried on every tick.
TOKEN_QUERY_DEFERRAL_RETRY_AFTER: Final = 600
# How long after its first deferral a transaction is decoded even if token queries fail
TOKEN_QUERY_DEFERRAL_MAX_DURATION: Final = DAY_IN_SECONDS


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
        # chain -> timestamp of the last failure to resolve an L1 fee while decoding
        self.l1_fee_failure_ts: dict[SupportedBlockchain, Timestamp] = {}
        # chain -> number of runs that probed a transaction with an unresolved L1 fee
        self.l1_fee_probes: dict[SupportedBlockchain, int] = {}
        # chain -> tx hash -> timestamps of the first and the last time the transaction was
        # left undecoded because a token query failed to reach the nodes
        self.token_query_deferrals: dict[SupportedBlockchain, dict[EVMTxHash, tuple[Timestamp, Timestamp]]] = {}  # noqa: E501
        self._token_query_deferrals_lock = Lock()

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

    def mark_l1_fee_unresolved(self, blockchain: SupportedBlockchain, now: Timestamp) -> None:
        """Signal that an L1 fee of `blockchain` could not be resolved while decoding."""
        self.l1_fee_failure_ts[blockchain] = now

    def should_defer_unresolved_l1_fees(
            self,
            blockchain: SupportedBlockchain,
            now: Timestamp,
    ) -> bool:
        """Whether the periodic decoding should skip the transactions of `blockchain` whose
        L1 fee is unresolved, since a lookup failed recently. They are retried once the
        delay passes. State is in memory, so a restart only brings the retry forward."""
        return now - self.l1_fee_failure_ts.get(blockchain, 0) <= UNRESOLVED_L1_FEE_RETRY_AFTER

    def next_l1_fee_probe_index(self, blockchain: SupportedBlockchain, count: int) -> int:
        """Pick which of `count` transactions with an unresolved L1 fee to probe, in round
        robin across runs, so one whose fee can never be resolved does not keep failing the
        probe and deferring the retries of the others."""
        probes = self.l1_fee_probes.get(blockchain, 0)
        self.l1_fee_probes[blockchain] = probes + 1
        return probes % count

    def defer_for_token_query(
            self,
            blockchain: SupportedBlockchain,
            tx_hash: EVMTxHash,
            now: Timestamp,
    ) -> None:
        """Signal that `tx_hash` was left undecoded since a token query failed"""
        with self._token_query_deferrals_lock:
            deferrals = self.token_query_deferrals.setdefault(blockchain, {})
            first_ts, _ = deferrals.get(tx_hash, (now, now))
            deferrals[tx_hash] = (first_ts, now)

    def clear_token_query_deferral(self, blockchain: SupportedBlockchain, tx_hash: EVMTxHash) -> None:  # noqa: E501
        """Signal that `tx_hash` was decoded"""
        with self._token_query_deferrals_lock:
            self.token_query_deferrals.get(blockchain, {}).pop(tx_hash, None)

    def get_token_query_deferred_hashes(
            self,
            blockchain: SupportedBlockchain,
            now: Timestamp | None = None,
    ) -> list[EVMTxHash]:
        """Return the deferred transactions of `blockchain`. If `now` is given only the ones
        that the periodic decoding should still skip, since they were deferred recently."""
        with self._token_query_deferrals_lock:
            return [
                tx_hash for tx_hash, (_, last_ts) in self.token_query_deferrals.get(blockchain, {}).items()  # noqa: E501
                if now is None or now - last_ts <= TOKEN_QUERY_DEFERRAL_RETRY_AFTER
            ]

    def is_token_query_deferral_expired(
            self,
            blockchain: SupportedBlockchain,
            tx_hash: EVMTxHash,
            now: Timestamp,
    ) -> bool:
        """Whether `tx_hash` was first deferred long enough ago to be decoded even if token
        queries fail. State is in memory, so a restart only delays it."""
        with self._token_query_deferrals_lock:
            if (deferral := self.token_query_deferrals.get(blockchain, {}).get(tx_hash)) is None:
                return False

        return now - deferral[0] > TOKEN_QUERY_DEFERRAL_MAX_DURATION
