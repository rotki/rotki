import bisect
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.concurrency import TaskCancelledError, checkpoint
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL
from rotkehlchen.constants.assets import A_ETH, A_ETH2
from rotkehlchen.db.cache import DBCacheDynamic, DBCacheStatic
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.bucket_checks import (
    BucketBalanceCheck,
    balances_match,
    save_balance_check,
)
from rotkehlchen.history.data_issues.bucket_state import (
    get_bucket_stops,
    make_bucket_key,
    wallet_bucket_assets,
)
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.data_issues.types import CurrentBalanceMismatchIssuePayload
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    EVM_LOCATIONS,
    EventMetricKey,
    Location,
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.utils.misc import ts_now, ts_sec_to_ms

if TYPE_CHECKING:
    from collections.abc import Collection

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
    evm_locations = tuple(location.serialize_for_db() for location in EVM_LOCATIONS)
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


def are_queries_disabled(blockchain: SupportedBlockchain, address: str) -> bool:
    """Whether the balance queries of the address are skipped, on their own or with their chain."""
    return (skipped := CachedSettings().get_settings().disabled_chain_queries.get(
        blockchain,
    )) is not None and (len(skipped) == 0 or address in skipped)


def get_wallet_query_scope(
        database: DBHandler,
) -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    """The (location, address) pairs of the tracked EVM accounts, and of those among them whose
    balance queries are disabled, on their own or because their whole chain is.

    Untracked accounts are out of scope. A tracked account with disabled queries is in scope
    but can't be compared: nothing refreshes its balances. A removed account can keep a wallet
    bucket, since a transfer to it from a tracked account stays in the history, but its derived
    balance no longer covers its own activity.
    """
    location_of_chain = {
        SupportedBlockchain.from_location(location).value: location.serialize_for_db()
        for location in EVM_LOCATIONS
    }
    tracked: set[tuple[str, str]] = set()
    disabled: set[tuple[str, str]] = set()
    with database.conn.read_ctx() as cursor:
        for blockchain, account in cursor.execute(
            'SELECT blockchain, account FROM blockchain_accounts',
        ):
            if (location := location_of_chain.get(blockchain)) is None:
                continue

            tracked.add(wallet := (location, account))
            if are_queries_disabled(SupportedBlockchain(blockchain), account):
                disabled.add(wallet)

    return tracked, disabled


def _serialize_cursor(wallet: tuple[str, str]) -> str:
    """Location and address of the last wallet a full run reached, as stored in the cache."""
    return ':'.join(wallet)


def _deserialize_cursor(value: str) -> tuple[str, str]:
    location, address = value.split(':', maxsplit=1)
    return location, address


def read_cached_wallet_balances(
        cursor: DBCursor,
        blockchain: SupportedBlockchain,
        address: str,
        assets: Collection[str],
) -> dict[str, FVal]:
    """Read from the balances cache what the address holds directly in its wallet.

    That is the wallet label, plus the label of the token's own protocol for a token that carries
    one, since the cache files those tokens (aTokens, LP tokens) under their protocol even when
    the wallet holds them. Any other label is what the address has deposited in a protocol,
    which a protocol bucket accounts for and the wallet bucket doesn't.

    The cache can't tell an asset the address no longer holds from one it doesn't track, so an
    asset without a row is left out of the result and not reported as zero.
    """
    return {
        asset: FVal(amount)
        for asset, label, amount in cursor.execute(
            'SELECT asset, label, amount FROM blockchain_balances_cache '
            'WHERE blockchain = ? AND address = ? AND category = ?',
            (blockchain.serialize(), address, BalanceType.ASSET.serialize_for_db()),
        ) if asset in assets and (
            label == DEFAULT_BALANCE_LABEL or label == _get_token_protocol(asset)
        )
    }


def _get_token_protocol(asset: str) -> str | None:
    try:
        return EvmToken(asset).protocol
    except (UnknownAsset, WrongAssetType):
        return None


class CurrentBalanceMismatchDetector:
    """Compare the balances derived from events to the balances cached from the chains.

    Meant to run in its own task after a successful historical balance processing pass, never
    inline with it. It only reads the cached balances and writes data issues, and it never
    queries a chain, so how current the comparison is depends on the last balance refresh of the
    address. A bucket with an event newer than that refresh is left alone, since the cache can't
    know about it. Locating the events that cause a divergence is left to the archive node
    search of the issue.

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
        self.reached_end_of_scope = False  # False when the time budget cut the last run short

    def run(self, from_ts: TimestampMS | None = None) -> int:
        """Check the wallet buckets and return how many of them were compared.

        Buckets are grouped per address so each one costs a single cache read. Buckets that
        have nothing cached, that have an event newer than the last refresh of their address, or
        that are left when the time budget runs out are skipped and neither opened nor
        resolved, since nothing was observed for them.

        A full run (no from_ts) that runs out of its time budget records where it stopped, and
        the next full run starts from there, so every address is eventually compared.
        """
        with self.database.conn.read_ctx() as cursor:
            ignored_assets = self.database.get_ignored_asset_ids(cursor)
            resume_after = self.database.get_static_cache(
                cursor=cursor,
                name=DBCacheStatic.CURRENT_BALANCE_DETECTION_CURSOR,
            )

        tracked_wallets, disabled_wallets = get_wallet_query_scope(self.database)
        tracked_wallets -= disabled_wallets
        with self.database.conn.read_ctx() as cursor:
            blocked_buckets = set(get_bucket_stops(cursor))
        by_address: defaultdict[tuple[str, str], dict[str, WalletBalance]] = defaultdict(dict)
        for (location, address, asset), derived in get_derived_wallet_balances(
            database=self.database,
            from_ts=from_ts,
            treat_eth2_as_eth=self.treat_eth2_as_eth,
        ).items():
            if (
                asset not in ignored_assets and
                (location, address) in tracked_wallets and
                not any(make_bucket_key(
                    location=location,
                    location_label=address,
                    protocol=None,
                    asset=stopped_asset,
                ) in blocked_buckets for stopped_asset in wallet_bucket_assets(
                    asset=asset,
                    treat_eth2_as_eth=self.treat_eth2_as_eth,
                ))  # its frozen derived balance says nothing about the chain
            ):
                by_address[location, address][asset] = derived

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
            assets = by_address[location, address]
            checkpoint()
            blockchain = SupportedBlockchain.from_location(
                location=Location.deserialize_from_db(location),  # type: ignore[arg-type]  # only EVM locations are tracked
            )
            with self.database.conn.read_ctx() as cursor:  # balances and their time, one snapshot
                queried_at = self.database.get_dynamic_cache(
                    cursor=cursor,
                    name=DBCacheDynamic.LAST_ADDRESS_BALANCES_QUERY_TS,
                    blockchain=blockchain.serialize(),
                    address=address,
                )
                observed = {} if queried_at is None else read_cached_wallet_balances(
                    cursor=cursor,
                    blockchain=blockchain,
                    address=address,
                    assets=assets,
                )
            if queried_at is None:
                continue

            for asset, derived in assets.items():
                if (
                    (observed_balance := observed.get(asset)) is not None and
                    derived.latest_ts <= ts_sec_to_ms(queried_at) and
                    self._compare(
                        location=location,
                        address=address,
                        asset=asset,
                        derived=derived,
                        observed_balance=observed_balance,
                        queried_at=queried_at,
                    )
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
            derived: WalletBalance,
            observed_balance: FVal,
            queried_at: Timestamp,
    ) -> bool:
        """Save the comparison and update its issue in one transaction, and return whether it
        was saved. Nothing is written when what the comparison was based on changed since it
        was read, which is how an account removal, a history reset or a setting change that
        happened meanwhile can't be undone by a run that was already underway.

        The issue helpers open their own write contexts, which join the transaction of this
        thread as savepoints. They share its commit and rollback instead of committing alone.
        """
        with self.database.user_write() as write_cursor:
            if self._is_obsolete(
                write_cursor=write_cursor,
                location=location,
                address=address,
                asset=asset,
                derived=derived,
                queried_at=queried_at,
            ):
                return False

            save_balance_check(write_cursor, BucketBalanceCheck(
                location=location,
                location_label=address,
                asset=asset,
                derived_balance=derived.balance,
                observed_balance=observed_balance,
                latest_event_identifier=derived.latest_event_identifier,
                observed_at=queried_at,
                compared_at=ts_now(),
            ))
            self._update_issue(
                location=location,
                address=address,
                asset=asset,
                derived=derived,
                observed_balance=observed_balance,
                queried_at=queried_at,
            )
        return True

    def _is_obsolete(
            self,
            write_cursor: DBCursor,
            location: str,
            address: str,
            asset: str,
            derived: WalletBalance,
            queried_at: Timestamp,
    ) -> bool:
        """Whether anything the comparison was based on no longer holds, read inside the write
        transaction so that nothing can change between this check and the write."""
        blockchain = SupportedBlockchain.from_location(
            location=Location.deserialize_from_db(location),  # type: ignore[arg-type]  # only EVM locations are tracked
        )
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
            ).fetchone() is not None or
            self.database.get_dynamic_cache(
                cursor=write_cursor,
                name=DBCacheDynamic.LAST_ADDRESS_BALANCES_QUERY_TS,
                blockchain=blockchain.serialize(),
                address=address,
            ) != queried_at
        ):
            return True

        if (stored := write_cursor.execute(
            "SELECT value FROM settings WHERE name = 'treat_eth2_as_eth'",
        ).fetchone()) is not None and (stored[0] == 'True') != self.treat_eth2_as_eth:
            return True

        current = get_derived_wallet_balances(
            database=self.database,
            treat_eth2_as_eth=self.treat_eth2_as_eth,
            only=(location, address, asset),
        ).get((location, address, asset))
        return (
            current is None or
            current.balance != derived.balance or
            current.latest_event_identifier != derived.latest_event_identifier
        )

    def _update_issue(
            self,
            location: str,
            address: str,
            asset: str,
            derived: WalletBalance,
            observed_balance: FVal,
            queried_at: Timestamp,
    ) -> None:
        if balances_match(derived.balance, observed_balance, self.tolerance):
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
                derived_balance=str(derived.balance),
                observed_balance=str(observed_balance),
                delta=str(observed_balance - derived.balance),
                queried_at_ts=queried_at,
                latest_event_identifier=derived.latest_event_identifier,
            ),
            ts_start=derived.latest_ts,
            ts_end=ts_sec_to_ms(queried_at),
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
