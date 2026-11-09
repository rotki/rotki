import bisect
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.concurrency import TaskCancelledError, checkpoint
from rotkehlchen.constants.assets import A_ETH, A_ETH2
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.bucket_checks import (
    BucketBalanceCheck,
    DerivedSnapshot,
    balances_match,
    save_balance_check,
)
from rotkehlchen.history.data_issues.bucket_state import wallet_bucket_assets
from rotkehlchen.history.data_issues.eligibility import (
    WalletEvidence,
    are_queries_disabled,
    get_wallet_evidence,
    load_wallet_evidence,
    wallet_evidence_for_bucket,
)
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.data_issues.types import CurrentBalanceMismatchIssuePayload
from rotkehlchen.locations.chains import EVM_LOCATIONS, location_to_chain
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    EventMetricKey,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.utils.misc import ts_now, ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

DEFAULT_DETECTION_TIME_BUDGET: Final = 300  # seconds
FULL_RUN_PENDING: Final = 0  # value of the pending marker that asks for a full comparison


@dataclass
class WalletBalance:
    """The balance derived from event metrics for a wallet bucket."""
    balance: FVal
    latest_event_identifier: int | None
    latest_ts: int

    def to_snapshot(self) -> DerivedSnapshot:
        return DerivedSnapshot(
            balance=self.balance,
            latest_event_identifier=self.latest_event_identifier,
            latest_ts=TimestampMS(self.latest_ts),
        )


def get_derived_wallet_balances(
        database: DBHandler,
        from_ts: TimestampMS | None = None,
        treat_eth2_as_eth: bool | None = None,
        only: tuple[str, str, str] | None = None,
) -> dict[tuple[str, str, str], WalletBalance]:
    """Latest derived balance of each EVM wallet bucket keyed by (location, address, asset).

    When from_ts is given only buckets with a balance row at or after it are returned. When
    only is given (a bucket key as returned here) just that bucket is read, which is how a
    snapshot is revalidated inside a write transaction. A bucket with no balance row is absent,
    never zero.
    """
    if treat_eth2_as_eth is None:
        treat_eth2_as_eth = CachedSettings().get_entry('treat_eth2_as_eth') is True
    evm_locations = tuple(location for location in EVM_LOCATIONS)
    placeholders = ','.join('?' * len(evm_locations))
    only_filter: str = ''
    only_bindings: tuple[str, ...] = ()
    if only is not None:
        only_location, only_address, only_asset = only
        only_assets = wallet_bucket_assets(only_asset, treat_eth2_as_eth)
        only_filter = f'AND location = ? AND location_label = ? AND asset IN ({",".join("?" * len(only_assets))})'  # noqa: E501
        only_bindings = (only_location, only_address, *only_assets)
    balances: dict[tuple[str, str, str], WalletBalance] = {}
    with database.conn.read_ctx() as cursor:
        # bare columns take their value from the row holding MAX(sort_key), see
        # https://www.sqlite.org/lang_select.html#bareagg
        for location, address, row_asset, value, event_identifier, timestamp, _ in cursor.execute(
            'SELECT location, location_label, asset, metric_value, event_identifier, timestamp, '
            'MAX(sort_key) FROM event_metrics WHERE metric_key = ? AND protocol IS NULL '
            f'AND location_label IS NOT NULL AND location IN ({placeholders}) {only_filter} '
            'GROUP BY location, location_label, asset',
            (EventMetricKey.BALANCE.serialize(), *evm_locations, *only_bindings),
        ):
            asset = (
                A_ETH.identifier if treat_eth2_as_eth and row_asset == A_ETH2
                else row_asset
            )

            if (entry := balances.get(key := (location, address, asset))) is None:
                balances[key] = WalletBalance(FVal(value), event_identifier, timestamp)
                continue

            entry.balance += FVal(value)
            if timestamp > entry.latest_ts:
                entry.latest_ts, entry.latest_event_identifier = timestamp, event_identifier

        if from_ts is not None:
            modified = {(row[0], row[1], row[2]) for row in cursor.execute(
                'SELECT DISTINCT location, location_label, asset FROM event_metrics '
                'WHERE metric_key = ? AND protocol IS NULL AND timestamp >= ?',
                (EventMetricKey.BALANCE.serialize(), from_ts),
            )}
            balances = {key: entry for key, entry in balances.items() if key in modified}

    return balances


def _serialize_cursor(wallet: tuple[str, str]) -> str:
    """Location and address of the last wallet a full run reached, as stored in the cache."""
    return ':'.join(wallet)


def _deserialize_cursor(value: str) -> tuple[str, str]:
    location, address = value.split(':', maxsplit=1)
    return location, address


def _is_stopped(
        stopped_buckets: set[tuple[str, str, str, str]],
        location: str,
        address: str,
        asset: str,
        treat_eth2_as_eth: bool,
) -> bool:
    return any(
        (location, address, '', stopped_asset) in stopped_buckets
        for stopped_asset in wallet_bucket_assets(asset=asset, treat_eth2_as_eth=treat_eth2_as_eth)
    )


class CurrentBalanceMismatchDetector:
    """Compare the balances derived from events to the observed balances of the wallet.

    Meant to run in its own task after a successful historical balance processing pass, never
    inline with it. It reads only the database: asset-specific observations written by the
    balance queries, the transaction sync ranges and the decoding state. It never queries a
    chain, so how current the comparison is depends on the last successful query of the asset.
    A bucket whose observation is not usable yet is skipped and keeps its previous timestamps.
    Locating the events that cause a divergence is left to the archive node search of the issue.

    The observation is not a claim about a specific common block: the transaction sync and the
    balance query happen at different moments, so a transaction mined between them can produce
    a false mismatch for one cycle. It is deliberately not escalated; the next match resolves
    the issue automatically, like any other later comparison.

    A full run enumerates the union of derived wallet buckets and observed wallet holdings, so a
    token held with no history at all is discovered. A scoped run only checks the buckets a
    processing pass touched; discovery is the full run's job.

    Mismatch issue policy: every non-ignored eligible mismatch reports an issue. There is no
    fiat value threshold, so a bucket without a price can never be hidden by that; ignored
    assets are the only spam filter applied here, and an observed-only holding is not assumed
    to be spam.

    The tolerance is relative, like it is for asset movement matching: two balances match when
    they differ by at most that fraction of the larger one.
    """

    def __init__(
            self,
            database: DBHandler,
            time_budget: int = DEFAULT_DETECTION_TIME_BUDGET,
            tolerance: FVal | None = None,
    ) -> None:
        self.database = database
        self.time_budget = time_budget
        self.tolerance = (
            CachedSettings().get_settings().asset_movement_amount_tolerance
            if tolerance is None else tolerance
        )
        self.issues_manager = DataIssuesManager(database)
        self.treat_eth2_as_eth = CachedSettings().get_entry('treat_eth2_as_eth') is True
        self.swapped_assets: frozenset[str] = frozenset()
        self.reached_end_of_scope = False  # False when the time budget cut the last run short

    def run(self, from_ts: TimestampMS | None = None) -> int:
        """Check the wallet buckets and return how many of them were compared.

        Buckets are grouped per address so each one costs a single eligibility read. Buckets
        without a usable observation (missing coverage, unsynced history, pending decoding, an
        observation older than the latest derived event, a disabled or rebasing bucket) are
        skipped and neither opened nor resolved, since nothing was observed for them.

        A full run (no from_ts) that runs out of its time budget records where it stopped, and
        the next full run starts from there, so every address is eventually compared.
        """
        with self.database.conn.read_ctx() as cursor:
            ignored_assets = self.database.get_ignored_asset_ids(cursor)
            resume_after = self.database.get_static_cache(
                cursor=cursor,
                name=DBCacheStatic.CURRENT_BALANCE_DETECTION_CURSOR,
            )

        context = load_wallet_evidence(self.database)
        self.swapped_assets = context.swapped_assets
        derived = get_derived_wallet_balances(
            database=self.database,
            from_ts=from_ts,
            treat_eth2_as_eth=self.treat_eth2_as_eth,
        )
        # A bucket is a candidate with its derived snapshot, None when only an observation
        # exists. A stopped bucket says nothing about the chain through its frozen balance.
        candidates: dict[tuple[str, str, str], DerivedSnapshot | None] = {}
        for (location, address, asset), balance in derived.items():
            if (
                asset in ignored_assets or
                (location, address) not in context.tracked or
                (location, address) in context.disabled or
                _is_stopped(
                    stopped_buckets=context.stopped_buckets,
                    location=location,
                    address=address,
                    asset=asset,
                    treat_eth2_as_eth=self.treat_eth2_as_eth,
                )
            ):
                continue

            candidates[location, address, asset] = balance.to_snapshot()

        if from_ts is None:  # a full run discovers the observed-only holdings
            for location, address, raw_asset in context.observations:
                asset = (
                    A_ETH.identifier
                    if self.treat_eth2_as_eth and raw_asset == A_ETH2
                    else raw_asset
                )
                if (
                    asset in ignored_assets or
                    (location, address) not in context.tracked or
                    (location, address) in context.disabled or
                    _is_stopped(
                        stopped_buckets=context.stopped_buckets,
                        location=location,
                        address=address,
                        asset=asset,
                        treat_eth2_as_eth=self.treat_eth2_as_eth,
                    )
                ):
                    continue

                candidates.setdefault((location, address, asset), None)

        by_address: defaultdict[tuple[str, str], dict[str, DerivedSnapshot | None]] = defaultdict(dict)  # noqa: E501
        for (location, address, asset), snapshot in candidates.items():
            by_address[location, address][asset] = snapshot

        wallets = sorted(by_address)
        # Rotate rather than truncate: a run that stops early must not starve the wallets
        # that sort before the cursor.
        if from_ts is None and resume_after is not None:
            start = bisect.bisect_right(wallets, _deserialize_cursor(resume_after))
            wallets = wallets[start:] + wallets[:start]

        started, compared, last_reached = time.monotonic(), 0, None
        for location, address in wallets:
            if time.monotonic() - started > self.time_budget:
                log.debug('Current balance detection ran out of its time budget')
                if from_ts is None and last_reached is not None:
                    self._save_cursor(_serialize_cursor(last_reached))
                break

            last_reached = (location, address)
            checkpoint()
            with self.database.conn.read_ctx() as cursor:
                for asset, snapshot in by_address[location, address].items():
                    evidence = wallet_evidence_for_bucket(
                        context=context,
                        cursor=cursor,
                        location=location,
                        address=address,
                        asset=asset,
                        derived=snapshot,
                    )
                    if (
                        evidence.unsupported or
                        evidence.pending_reasons or
                        evidence.derived_snapshot is None or
                        evidence.amount is None or
                        evidence.observed_at is None
                    ):  # not comparable, so no comparison is opened, resolved or refreshed
                        continue

                    if self._compare(
                        location=location,
                        address=address,
                        asset=asset,
                        evidence=evidence,
                    ):
                        compared += 1

        else:  # every wallet was reached, so the next full run starts from the beginning
            self.reached_end_of_scope = True
            if from_ts is None:
                self._save_cursor(None)

        return compared

    def _save_cursor(self, value: str | None) -> None:
        with self.database.user_write() as write_cursor:
            if value is None:
                write_cursor.execute(
                    'DELETE FROM key_value_cache WHERE name = ?',
                    (DBCacheStatic.CURRENT_BALANCE_DETECTION_CURSOR.value,),
                )
            else:
                self.database.set_static_cache(
                    write_cursor=write_cursor,
                    name=DBCacheStatic.CURRENT_BALANCE_DETECTION_CURSOR,
                    value=value,
                )

    def _compare(
            self,
            location: str,
            address: str,
            asset: str,
            evidence: WalletEvidence,
    ) -> bool:
        """Save the comparison and update its issue in one transaction, and return whether it
        was saved. Nothing is written when what the comparison was based on changed since it
        was read, which is how an account removal, a history reset or a setting change that
        happened meanwhile can't be undone by a run that was already underway.

        The issue helpers open their own write contexts, which join the transaction of this
        thread as savepoints. They share its commit and rollback instead of committing alone.
        """
        if (
            evidence.derived_snapshot is None or
            evidence.amount is None or
            evidence.observed_at is None
        ):
            return False

        with self.database.user_write() as write_cursor:
            if self._is_obsolete(
                write_cursor=write_cursor,
                location=location,
                address=address,
                asset=asset,
                evidence=evidence,
            ):
                return False

            save_balance_check(write_cursor, BucketBalanceCheck(
                location=location,
                location_label=address,
                asset=asset,
                derived_balance=evidence.derived_snapshot.balance,
                observed_balance=evidence.amount,
                latest_event_identifier=evidence.derived_snapshot.latest_event_identifier,
                observed_at=evidence.observed_at,
                compared_at=ts_now(),
                observation_id=evidence.observation_id,
            ))
            self._update_issue(
                location=location,
                address=address,
                asset=asset,
                evidence=evidence,
            )
        return True

    def _is_obsolete(
            self,
            write_cursor: DBCursor,
            location: str,
            address: str,
            asset: str,
            evidence: WalletEvidence,
    ) -> bool:
        """Whether anything the comparison was based on no longer holds, read inside the write
        transaction so that nothing can change between this check and the write.

        The eligibility facts are recomputed here with the same shared reader the run used, so
        the write cannot resurrect a comparison after the bucket became ineligible.
        """
        blockchain = location_to_chain(location)
        stopped_assets = wallet_bucket_assets(asset, self.treat_eth2_as_eth)
        if (
            write_cursor.execute(
                'SELECT 1 FROM blockchain_accounts WHERE blockchain = ? AND account = ?',
                (blockchain.value, address),
            ).fetchone() is None or
            are_queries_disabled(blockchain, address) or
            write_cursor.execute(
                'SELECT 1 FROM bucket_processing_stops WHERE location = ? AND '
                f"location_label = ? AND protocol = '' AND asset IN ({','.join('?' * len(stopped_assets))})",  # noqa: E501
                (location, address, *stopped_assets),
            ).fetchone() is not None or
            write_cursor.execute(
                'SELECT 1 FROM key_value_cache WHERE name = ?',
                (DBCacheStatic.STALE_BALANCES_FROM_TS.value,),
            ).fetchone() is not None
        ):
            return True

        if (stored := write_cursor.execute(
            "SELECT value FROM settings WHERE name = 'treat_eth2_as_eth'",
        ).fetchone()) is not None and (stored[0] == 'True') != self.treat_eth2_as_eth:
            return True

        derived = evidence.derived_snapshot
        if derived is None:
            return True

        # A history-free zero is not a metric. Verify the status again instead of looking for a
        # row that legitimately doesn't exist; a normal derived snapshot is re-read and must
        # still be the same.
        fresh = get_wallet_evidence(
            database=self.database,
            location=location,
            address=address,
            asset=asset,
            derived=None if derived.is_history_free else derived,
            swapped_assets=self.swapped_assets,
        )
        if derived.is_history_free:
            if fresh.verified_history_free is False or fresh.derived_snapshot is None:
                return True
        else:
            current = get_derived_wallet_balances(
                database=self.database,
                treat_eth2_as_eth=self.treat_eth2_as_eth,
                only=(location, address, asset),
            ).get((location, address, asset))
            if (
                current is None or
                current.balance != derived.balance or
                current.latest_event_identifier != derived.latest_event_identifier
            ):
                return True

        return (
            len(fresh.unsupported) != 0 or
            len(fresh.pending_reasons) != 0 or
            fresh.amount != evidence.amount or
            fresh.observed_at != evidence.observed_at or
            fresh.observation_id != evidence.observation_id
        )

    def _update_issue(
            self,
            location: str,
            address: str,
            asset: str,
            evidence: WalletEvidence,
    ) -> None:
        if (
            evidence.derived_snapshot is None or
            evidence.amount is None or
            evidence.observed_at is None
        ):
            return

        if balances_match(evidence.derived_snapshot.balance, evidence.amount, self.tolerance):
            self.issues_manager.resolve_current_balance_mismatch(
                location=location,
                location_label=address,
                asset=asset,
            )
            return

        self.issues_manager.report_current_balance_mismatch(
            location=location,
            location_label=address,
            asset=asset,
            payload=CurrentBalanceMismatchIssuePayload(
                derived_balance=str(evidence.derived_snapshot.balance),
                observed_balance=str(evidence.amount),
                delta=str(evidence.amount - evidence.derived_snapshot.balance),
                queried_at_ts=evidence.observed_at,
                latest_event_identifier=evidence.derived_snapshot.latest_event_identifier,
            ),
            ts_start=(
                evidence.derived_snapshot.latest_ts
                if evidence.derived_snapshot.latest_ts is not None else
                ts_sec_to_ms(evidence.observed_at)
            ),
            ts_end=ts_sec_to_ms(evidence.observed_at),
        )


def _set_pending_detection(database: DBHandler, from_ts: int | None) -> None:
    """Set the marker of the processing passes the detection has not covered, None clears it."""
    with database.user_write() as write_cursor:
        if from_ts is None:
            write_cursor.execute(
                'DELETE FROM key_value_cache WHERE name = ?',
                (DBCacheStatic.PENDING_DETECTION_FROM_TS.value,),
            )
        else:
            database.set_static_cache(
                write_cursor=write_cursor,
                name=DBCacheStatic.PENDING_DETECTION_FROM_TS,
                value=Timestamp(from_ts),
            )


def run_current_balance_detection(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
        from_ts: TimestampMS | None = None,
        time_budget: int = DEFAULT_DETECTION_TIME_BUDGET,
) -> int:
    """Task entrypoint. Returns the number of wallet buckets that were compared.

    Only a full run (no from_ts) restarts the daily cooldown, so partial runs after each
    processing pass don't postpone the daily full comparison. Every run, even a failed or
    cancelled one, ends with a CURRENT_BALANCE_DETECTION_COMPLETED message, since it may have
    opened or resolved issues before stopping.

    The pending marker left by the processing passes is settled by how the run ends:
    - cancelled: kept, since the work that preempted the run folds its own pass into it;
    - crashed: cleared, so a failure that repeats doesn't respawn the task on every tick and the
      daily full run retries it;
    - a scoped run that ran out of its time budget: turned into a full run request, since a
      scoped run has no cursor to resume from and would start over at the same wallets;
    - otherwise cleared. A full run that ran out of budget resumes from its cursor.
    """
    detector: CurrentBalanceMismatchDetector | None = None
    cancelled, compared = False, None
    try:
        detector = CurrentBalanceMismatchDetector(database=database, time_budget=time_budget)
        compared = detector.run(from_ts=from_ts)
    except TaskCancelledError:
        cancelled = True
        raise
    else:
        return compared
    finally:
        try:  # a crash must not leave the periodic task due again on the very next tick
            if from_ts is None:
                with database.user_write() as write_cursor:
                    database.set_static_cache(
                        write_cursor=write_cursor,
                        name=DBCacheStatic.LAST_CURRENT_BALANCE_DETECTION_TS,
                        value=ts_now(),
                    )
        finally:  # a cancelled task can't write, but its issues may still have changed
            try:
                if cancelled is False:
                    _set_pending_detection(
                        database=database,
                        from_ts=FULL_RUN_PENDING if (
                            compared is not None and
                            from_ts is not None and
                            detector is not None and
                            detector.reached_end_of_scope is False
                        ) else None,
                    )
            finally:
                msg_aggregator.add_message(
                    message_type=WSMessageType.CURRENT_BALANCE_DETECTION_COMPLETED,
                    data={},
                )
