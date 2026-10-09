import logging
from collections import Counter, defaultdict
from typing import TYPE_CHECKING, Final

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.api.websockets.typedefs import UserMessageRecord
from rotkehlchen.chain.evm.constants import ZERO_32_BYTES_HEX
from rotkehlchen.chain.evm.manager import EvmManager
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HistoryMappingState
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.ranges import DBQueryRanges
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.hyperliquid import HyperliquidAPI
from rotkehlchen.history.events.utils import create_group_identifier_from_unique_id
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location
from rotkehlchen.user_messages import NetworkFailure

from .accountant import HyperliquidAccountingAggregator
from .decoding.decoder import HyperliquidTransactionDecoder
from .tokens import HyperliquidTokens
from .transactions import HyperliquidTransactions

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.premium.premium import Premium
    from rotkehlchen.types import ChecksumEvmAddress, Timestamp

    from .node_inquirer import HyperliquidInquirer


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
HYPERLIQUID_CORE_HISTORY_RANGE_PREFIX: Final = 'hyperliquid_core_history'
HYPERLIQUID_EVM_TOKEN_PREFIX: Final = 'eip155:999/erc20:'
STHYPE_IDENTIFIER: Final = 'eip155:999/erc20:0xfFaa4a3D97fE9107Cef8a3F48c069F577Ff76cC1'
WSTHYPE_IDENTIFIER: Final = 'eip155:999/erc20:0x94e8396e0869c9F2200760aF0621aFd240E1CF38'


class HyperliquidManager(EvmManager):
    def __init__(
            self, node_inquirer: HyperliquidInquirer, premium: Premium | None = None,
    ) -> None:
        super().__init__(
            node_inquirer=node_inquirer,
            transactions=(
                transactions := HyperliquidTransactions(
                    evm_inquirer=node_inquirer,
                    database=node_inquirer.database,
                )
            ),
            tokens=HyperliquidTokens(
                database=node_inquirer.database,
                evm_inquirer=node_inquirer,
                token_exceptions=set(),
            ),
            transactions_decoder=HyperliquidTransactionDecoder(
                database=node_inquirer.database,
                hyperliquid_inquirer=node_inquirer,
                transactions=transactions,
                premium=premium,
            ),
            accounting_aggregator=HyperliquidAccountingAggregator(
                node_inquirer=node_inquirer,
                msg_aggregator=transactions.msg_aggregator,
            ),
        )
        self.node_inquirer: HyperliquidInquirer

    def query_balances(
            self,
            addresses: Sequence[ChecksumEvmAddress],
    ) -> defaultdict[ChecksumEvmAddress, BalanceSheet]:
        """Query EVM on-chain balances plus Hyperliquid core spot/perp balances."""
        balances = defaultdict(BalanceSheet, super().query_balances(addresses))
        for address in addresses:
            if (
                (assets := balances[address].assets) and
                (wsthype := next((asset for asset in assets if asset.identifier == WSTHYPE_IDENTIFIER), None)) is not None and  # noqa: E501
                (sthype := next((asset for asset in assets if asset.identifier == STHYPE_IDENTIFIER), None)) is not None  # noqa: E501
            ):
                log.debug(
                    f'Skipping {sthype} balance for {address} since it represents the same '
                    f'Valantis staked HYPE position as {wsthype}',
                )
                del assets[sthype]

        api = HyperliquidAPI()
        main_currency = CachedSettings().main_currency
        for address in addresses:
            try:
                proprietary_balances = api.query_balances(address=address)
            except RemoteError as e:
                log.error(f'Failed to query Hyperliquid core balances for {address}: {e}')
                continue

            for asset, amount in proprietary_balances.items():
                try:
                    price = Inquirer.find_price(
                        from_asset=asset,
                        to_asset=main_currency,
                    )
                except RemoteError:
                    price = ZERO_PRICE

                if (
                    asset.identifier.startswith(HYPERLIQUID_EVM_TOKEN_PREFIX) and
                    asset in balances[address].assets
                ):
                    log.debug(
                        f'Skipping Hyperliquid core balance for {asset} at {address} '
                        'since it is already present in HyperEVM balances',
                    )
                    continue

                balances[address].assets[asset][DEFAULT_BALANCE_LABEL] += Balance(
                    amount=amount,
                    value=amount * price,
                )

        return balances

    def _query_legacy_funding_events(self) -> Counter[tuple[int, str | None]]:
        """Count the customized funding events under the zero hash by (timestamp, address).

        This exists only as a side effect of the faulty funding identification, which gave every
        payment the group of the zero hash. Migration 29 removes that event, but has to keep
        it when the user customized it, and it can't be moved to its correct group since it has
        no coin. Querying the history again would insert that payment a second time under its
        own group identifier, so it is looked up here once, which is a single query that
        returns nothing for most users, instead of once per event.
        """
        with self.node_inquirer.database.conn.read_ctx() as cursor:
            return Counter(cursor.execute(
                'SELECT E.timestamp, E.location_label FROM history_events E INNER JOIN '
                'history_events_mappings M ON M.parent_identifier=E.identifier AND '
                'M.name=? AND M.value=? WHERE E.group_identifier=? AND E.location=?',
                (
                    HISTORY_MAPPING_KEY_STATE,
                    HistoryMappingState.CUSTOMIZED.serialize_for_db(),
                    create_group_identifier_from_unique_id(
                        location=Location.HYPERLIQUID,
                        unique_id=ZERO_32_BYTES_HEX,
                    ),
                    Location.HYPERLIQUID.serialize_for_db(),
                ),
            ))

    @staticmethod
    def _drop_legacy_funding_events(
            events: list[HistoryBaseEntry],
            legacy_funding: Counter[tuple[int, str | None]],
    ) -> list[HistoryBaseEntry]:
        """Drop the funding payments that are already saved as a customized legacy event.

        The legacy event has no coin, and the original payment can't be recovered from the
        fields the user may have edited, so it is recognized by its timestamp and address.
        If the user edited either of them the original identity is lost, so the refetched
        payment is saved next to the edited event. That is the safe fallback: matching on
        other fields such as the amount could drop a different payment, which can't be
        undone, while a duplicate can be deleted by the user. It can only happen for the
        single payment the faulty identification ever saved. Each legacy event is consumed
        by its first match and other payments made at the same time are still saved.
        """
        kept: list[HistoryBaseEntry] = []
        for event in events:
            if (
                event.notes == 'Hyperliquid funding payment' and
                legacy_funding[key := (event.timestamp, event.location_label)] > 0
            ):
                legacy_funding[key] -= 1
            else:
                kept.append(event)

        return kept

    def _save_history_batches(
            self,
            history_db: DBHistoryEvents,
            batches: Iterator[list[HistoryBaseEntry]],
    ) -> int:
        """Save each batch of events as soon as it is queried and return how many were new.

        Each batch is written in its own transaction, so the batches saved before a failure
        are kept. Querying them again later is harmless since duplicate events are ignored.
        The assets of the events were resolved from the global DB, so they are added to the
        user DB first to make sure the insertion can't fail on the foreign key.

        May raise:
        - RemoteError
        """
        inserted = 0
        legacy_funding = self._query_legacy_funding_events()
        for batch in batches:
            events = self._drop_legacy_funding_events(batch, legacy_funding) if legacy_funding.total() != 0 else batch  # noqa: E501

            with self.node_inquirer.database.user_write() as write_cursor:
                self.node_inquirer.database.add_asset_identifiers(
                    write_cursor=write_cursor,
                    asset_identifiers=list({event.asset.identifier for event in events}),
                )
                inserted += history_db.add_history_events(
                    write_cursor=write_cursor,
                    history=events,
                )

        return inserted

    def query_proprietary_history(
            self,
            addresses: Sequence[ChecksumEvmAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> None:
        """Query and persist Hyperliquid core history for the given addresses.

        A range is only marked as queried once all of its history has been queried, so a
        range that failed midway is queried again in a future sync.
        """
        api = HyperliquidAPI()
        ranges = DBQueryRanges(self.node_inquirer.database)
        history_db = DBHistoryEvents(self.node_inquirer.database)

        for address in addresses:
            location_string = f'{HYPERLIQUID_CORE_HISTORY_RANGE_PREFIX}_{address}'
            with self.node_inquirer.database.conn.read_ctx() as cursor:
                ranges_to_query = ranges.get_location_query_ranges(
                    cursor=cursor,
                    location_string=location_string,
                    start_ts=from_timestamp,
                    end_ts=to_timestamp,
                )

            for range_start, range_end in ranges_to_query:
                try:
                    self._save_history_batches(
                        history_db=history_db,
                        batches=api.iter_history_event_batches(
                            address=address,
                            start_ts=range_start,
                            end_ts=range_end,
                        ),
                    )
                except RemoteError as e:
                    log.error(
                        f'Failed to query hyperliquid history for {address} '
                        f'from {range_start} to {range_end} due to {e}',
                    )
                    self.transactions.msg_aggregator.add_error(
                        f'Failed to query Hyperliquid history for {address}. '
                        'Will retry in a future sync.',
                        classification=NetworkFailure(
                            record=UserMessageRecord.TRANSACTION,
                            error=str(e),
                        ),
                        subject=Location.HYPERLIQUID,
                    )
                    continue

                with self.node_inquirer.database.user_write() as write_cursor:
                    ranges.update_used_query_range(
                        write_cursor=write_cursor,
                        location_string=location_string,
                        queried_ranges=[(range_start, range_end)],
                    )

    def refetch_proprietary_history(
            self,
            address: ChecksumEvmAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> int:
        """Force refetch Hyperliquid core history without checking/updating query ranges.

        Events queried before a failure are kept.

        May raise:
        - RemoteError
        """
        return self._save_history_batches(
            history_db=DBHistoryEvents(self.node_inquirer.database),
            batches=HyperliquidAPI().iter_history_event_batches(
                address=address,
                start_ts=start_ts,
                end_ts=end_ts,
            ),
        )

    def query_transactions(
            self,
            addresses: list[ChecksumEvmAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> None:
        """Query EVM transactions and Hyperliquid core history for the addresses.

        The core history is queried even if the EVM transactions could not all be.
        """
        try:
            super().query_transactions(
                addresses=addresses,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
            )
        finally:
            self.query_proprietary_history(
                addresses=addresses,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
            )
