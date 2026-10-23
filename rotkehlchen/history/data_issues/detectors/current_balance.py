import logging
import time
from collections import defaultdict, deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, cast

from web3.exceptions import BadFunctionCallOutput

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.evm.tokens import get_rpc_first_chunk_size_call_order
from rotkehlchen.chain.structures import EvmTokenDetectionData
from rotkehlchen.concurrency import checkpoint
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH, A_ETH2
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import BlockchainQueryError, RemoteError, RequestTooLargeError
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.data_issues.types import CurrentBalanceMismatchIssuePayload
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    EVM_LOCATIONS,
    ChainID,
    EventMetricKey,
    Location,
    TimestampMS,
    TokenKind,
)
from rotkehlchen.utils.misc import get_chunks, ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.chain.evm.manager import EvmManager
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE, ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

DEFAULT_DETECTION_TIME_BUDGET: Final = 300  # seconds

type ObservedBalanceReader = Callable[
    [Location, ChecksumEvmAddress, Sequence[str]],
    dict[str, FVal],
]
"""Reads the live balances of the given asset identifiers held by an address on a chain.

May raise RemoteError if the chain can't be queried. Assets that can't be queried, such as
NFTs, are left out of the result.
"""


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


def _query_token_balances(
        evm_manager: EvmManager,
        address: ChecksumEvmAddress,
        tokens: Sequence[EvmToken],
) -> dict[str, FVal]:
    """Latest balances of the tokens, halving the chunks the node refuses as too large.

    Tokens missing from the node's answer have a zero balance.

    May raise:
    - RemoteError if a single token can't be queried
    """
    chunk_size, call_order = get_rpc_first_chunk_size_call_order(
        evm_inquirer=evm_manager.node_inquirer,
    )
    balances: dict[str, FVal] = {token.identifier: ZERO for token in tokens}
    pending = deque(get_chunks([EvmTokenDetectionData(
        identifier=token.identifier,
        address=token.evm_address,
        decimals=cast('int', token.decimals),  # filtered by the caller
    ) for token in tokens], n=chunk_size))
    while len(pending) != 0:
        chunk = pending.popleft()
        try:
            result = evm_manager.tokens.get_token_balances(
                address=address,
                tokens=chunk,
                call_order=call_order,
            )
        except RequestTooLargeError:
            if len(chunk) == 1:
                raise

            pending.extendleft(reversed(list(get_chunks(chunk, n=len(chunk) // 2))))
            continue

        balances.update({token.identifier: balance for token, balance in result.items()})

    return balances


def make_evm_observed_balance_reader(chains_aggregator: ChainsAggregator) -> ObservedBalanceReader:
    """Reader of the latest wallet balances straight from the chain's nodes.

    It deliberately bypasses ChainsAggregator.query_balances so that the balances cache that
    feeds the dashboard is untouched and no protocol position is folded into the wallet.
    """
    def read(
            location: Location,
            address: ChecksumEvmAddress,
            assets: Sequence[str],
    ) -> dict[str, FVal]:
        evm_manager = chains_aggregator.get_evm_manager(cast(
            'EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE',
            ChainID(location.to_chain_id()),
        ))
        inquirer = evm_manager.node_inquirer
        observed: dict[str, FVal] = {}
        tokens: list[EvmToken] = []
        for identifier in assets:
            if identifier == inquirer.native_token.identifier:
                observed[identifier] = inquirer.get_multi_balance([address])[address]
                continue

            try:
                token = EvmToken(identifier)
            except (UnknownAsset, WrongAssetType):
                continue

            if token.token_kind == TokenKind.ERC20 and token.decimals is not None:
                tokens.append(token)  # NFTs have no fungible balance to compare

        if len(tokens) != 0:
            observed.update(_query_token_balances(
                evm_manager=evm_manager,
                address=address,
                tokens=tokens,
            ))

        return observed

    return read


class CurrentBalanceMismatchDetector:
    """Compare the balances derived from events to the live chain balances.

    Meant to run in its own task after a successful historical balance processing pass, never
    inline with it. It only reads the live balances and writes data issues. Locating the events
    that cause a divergence is left to the archive node search of the issue.
    """

    def __init__(
            self,
            database: DBHandler,
            observed_balance_reader: ObservedBalanceReader,
            time_budget: int = DEFAULT_DETECTION_TIME_BUDGET,
            tolerance: FVal | None = None,
    ) -> None:
        self.database = database
        self.observed_balance_reader = observed_balance_reader
        self.time_budget = time_budget
        self.tolerance = (
            CachedSettings().get_settings().asset_movement_amount_tolerance
            if tolerance is None else tolerance
        )
        self.issues_manager = DataIssuesManager(database)

    def run(self, from_ts: TimestampMS | None = None) -> int:
        """Check the wallet buckets and return how many of them were compared.

        Buckets are grouped per address so each one costs a single chain query. Buckets of
        an address that can't be queried, or that are left when the time budget runs out, are
        skipped and neither opened nor resolved, since nothing was observed for them.
        """
        with self.database.conn.read_ctx() as cursor:
            ignored_assets = self.database.get_ignored_asset_ids(cursor)

        by_address: defaultdict[tuple[str, str], dict[str, WalletBalance]] = defaultdict(dict)
        for (location, address, asset), derived in get_derived_wallet_balances(
            database=self.database,
            from_ts=from_ts,
        ).items():
            if asset not in ignored_assets:
                by_address[location, address][asset] = derived

        started, compared = time.monotonic(), 0
        for (location, address), assets in by_address.items():
            if time.monotonic() - started > self.time_budget:
                log.debug('Current balance detection ran out of its time budget')
                break

            checkpoint()
            try:
                observed = self.observed_balance_reader(
                    Location.deserialize_from_db(location),
                    cast('ChecksumEvmAddress', address),
                    list(assets),
                )
            except (RemoteError, BlockchainQueryError, BadFunctionCallOutput) as e:
                log.error('Failed to read the live balances of %s: %s', address, e)
                continue

            queried_at = ts_now()
            for asset, derived in assets.items():
                if (observed_balance := observed.get(asset)) is not None:
                    self._compare(
                        location=location,
                        address=address,
                        asset=asset,
                        derived=derived,
                        observed_balance=observed_balance,
                        queried_at=queried_at,
                    )
                    compared += 1

        return compared

    def _compare(
            self,
            location: str,
            address: str,
            asset: str,
            derived: WalletBalance,
            observed_balance: FVal,
            queried_at: int,
    ) -> None:
        if abs(delta := observed_balance - derived.balance) <= self.tolerance:
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
            ts_end=queried_at * 1000,
        )


def run_current_balance_detection(
        database: DBHandler,
        chains_aggregator: ChainsAggregator,
        from_ts: TimestampMS | None = None,
        time_budget: int = DEFAULT_DETECTION_TIME_BUDGET,
) -> int:
    """Task entrypoint. Returns the number of wallet buckets that were compared.

    Only a full run (no from_ts) restarts the daily cooldown, so partial runs after each
    processing pass don't postpone the daily full comparison.
    """
    try:
        return CurrentBalanceMismatchDetector(
            database=database,
            observed_balance_reader=make_evm_observed_balance_reader(chains_aggregator),
            time_budget=time_budget,
        ).run(from_ts=from_ts)
    finally:  # a crash must not leave the periodic task due again on the very next tick
        if from_ts is None:
            with database.user_write() as write_cursor:
                database.set_static_cache(
                    write_cursor=write_cursor,
                    name=DBCacheStatic.LAST_CURRENT_BALANCE_DETECTION_TS,
                    value=ts_now(),
                )
