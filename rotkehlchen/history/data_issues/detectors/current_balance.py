import bisect
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.concurrency import checkpoint
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL
from rotkehlchen.constants.assets import A_ETH, A_ETH2
from rotkehlchen.db.cache import DBCacheDynamic, DBCacheStatic
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.fval import FVal
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
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

DEFAULT_DETECTION_TIME_BUDGET: Final = 300  # seconds


@dataclass
class WalletBalance:
    """The balance derived from event metrics for a wallet bucket."""
    balance: FVal
    latest_event_identifier: int | None
    latest_ts: int


def get_derived_wallet_balances(
        database: DBHandler,
        from_ts: TimestampMS | None = None,
) -> dict[tuple[str, str, str], WalletBalance]:
    """Latest derived balance of each EVM wallet bucket keyed by (location, address, asset).

    When from_ts is given only buckets with a balance row at or after it are returned.
    """
    treat_eth2_as_eth = CachedSettings().get_entry('treat_eth2_as_eth') is True
    evm_locations = tuple(location.serialize_for_db() for location in EVM_LOCATIONS)
    placeholders = ','.join('?' * len(evm_locations))
    balances: dict[tuple[str, str, str], WalletBalance] = {}
    with database.conn.read_ctx() as cursor:
        # bare columns take their value from the row holding MAX(sort_key), see
        # https://www.sqlite.org/lang_select.html#bareagg
        for location, address, row_asset, value, event_identifier, timestamp, _ in cursor.execute(
            'SELECT location, location_label, asset, metric_value, event_identifier, timestamp, '
            'MAX(sort_key) FROM event_metrics WHERE metric_key = ? AND protocol IS NULL '
            f'AND location_label IS NOT NULL AND location IN ({placeholders}) '
            'GROUP BY location, location_label, asset',
            (EventMetricKey.BALANCE.serialize(), *evm_locations),
        ):
            asset = (
                A_ETH.identifier if treat_eth2_as_eth and row_asset == A_ETH2.identifier
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


def get_tracked_wallets(database: DBHandler) -> set[tuple[str, str]]:
    """The (location, address) pairs of the EVM accounts that are tracked now and not skipped.

    An account skipped through the disabled chain queries setting, on its own or because its
    whole chain is, is left out: nothing refreshes its balances, so there is nothing to compare.

    A removed account can keep a wallet bucket, since a transfer to it from a tracked account
    stays in the history, but its derived balance no longer covers its own activity.
    """
    disabled_queries = CachedSettings().get_settings().disabled_chain_queries
    location_of_chain = {
        SupportedBlockchain.from_location(location).value: location.serialize_for_db()
        for location in EVM_LOCATIONS
    }
    with database.conn.read_ctx() as cursor:
        return {
            (location, account)
            for blockchain, account in cursor.execute(
                'SELECT blockchain, account FROM blockchain_accounts',
            )
            if (location := location_of_chain.get(blockchain)) is not None and not (
                (skipped := disabled_queries.get(SupportedBlockchain(blockchain))) is not None
                and (len(skipped) == 0 or account in skipped)
            )
        }


def _serialize_cursor(wallet: tuple[str, str]) -> str:
    """Location and address of the last wallet a full run reached, as stored in the cache."""
    return ':'.join(wallet)


def _deserialize_cursor(value: str) -> tuple[str, str]:
    location, address = value.split(':', maxsplit=1)
    return location, address


def read_cached_wallet_balances(
        database: DBHandler,
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
    with database.conn.read_ctx() as cursor:
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
    chain. A bucket with an event newer than that refresh is left alone, since the cache can't
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

    def run(self, from_ts: TimestampMS | None = None) -> int:
        """Check the wallet buckets and return how many of them were compared.

        Buckets are grouped per address so each one costs a single cache read. Buckets that
        have nothing cached, that have an event newer than the last refresh of their chain, or
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
            refreshed_at = {
                blockchain: refresh_ts
                for blockchain in (
                    SupportedBlockchain.from_location(location) for location in EVM_LOCATIONS
                )
                if (refresh_ts := self.database.get_dynamic_cache(
                    cursor=cursor,
                    name=DBCacheDynamic.LAST_BLOCKCHAIN_BALANCES_QUERY_TS,
                    blockchain=blockchain.serialize(),
                )) is not None
            }

        tracked_wallets = get_tracked_wallets(self.database)
        by_address: defaultdict[tuple[str, str], dict[str, WalletBalance]] = defaultdict(dict)
        for (location, address, asset), derived in get_derived_wallet_balances(
            database=self.database,
            from_ts=from_ts,
        ).items():
            if asset not in ignored_assets and (location, address) in tracked_wallets:
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
            if (queried_at := refreshed_at.get(blockchain := SupportedBlockchain.from_location(
                location=Location.deserialize_from_db(location),  # type: ignore[arg-type]  # only EVM locations are tracked
            ))) is None:
                continue

            observed = read_cached_wallet_balances(
                database=self.database,
                blockchain=blockchain,
                address=address,
                assets=assets,
            )
            for asset, derived in assets.items():
                if (
                    (observed_balance := observed.get(asset)) is not None and
                    derived.latest_ts <= ts_sec_to_ms(queried_at)
                ):
                    self._compare(
                        location=location,
                        address=address,
                        asset=asset,
                        derived=derived,
                        observed_balance=observed_balance,
                        queried_at=queried_at,
                    )
                    compared += 1

        else:  # every wallet was reached, so the next full run starts from the beginning
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
    ) -> None:
        if abs(delta := observed_balance - derived.balance) <= self.tolerance * max(
            abs(observed_balance),
            abs(derived.balance),
        ):
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
                delta=str(delta),
                queried_at_ts=queried_at,
                latest_event_identifier=derived.latest_event_identifier,
            ),
            ts_start=derived.latest_ts,
            ts_end=ts_sec_to_ms(queried_at),
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
    """
    try:
        return CurrentBalanceMismatchDetector(
            database=database,
            time_budget=time_budget,
        ).run(from_ts=from_ts)
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
            msg_aggregator.add_message(
                message_type=WSMessageType.CURRENT_BALANCE_DETECTION_COMPLETED,
                data={},
            )
