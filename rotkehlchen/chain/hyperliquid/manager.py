import logging
from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.chain.evm.manager import EvmManager
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.ranges import DBQueryRanges
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.hyperliquid import HyperliquidAPI
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Price, Timestamp

from .accountant import HyperliquidAccountingAggregator
from .decoding.decoder import HyperliquidTransactionDecoder
from .tokens import HyperliquidTokens
from .transactions import HyperliquidTransactions

if TYPE_CHECKING:
    from rotkehlchen.premium.premium import Premium

    from .node_inquirer import HyperliquidInquirer


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class HyperliquidManager(EvmManager):
    def __init__(
            self, node_inquirer: 'HyperliquidInquirer', premium: 'Premium | None' = None,
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

        api = HyperliquidAPI()
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
                        to_asset=CachedSettings().main_currency,
                    )
                except RemoteError:
                    price = Price(ZERO)

                balances[address].assets[asset][DEFAULT_BALANCE_LABEL] += Balance(
                    amount=amount,
                    value=amount * price,
                )

        return balances

    def query_proprietary_history(
            self,
            addresses: Sequence[ChecksumEvmAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> None:
        """Query and persist Hyperliquid core history for the given addresses."""
        api = HyperliquidAPI()
        ranges = DBQueryRanges(self.node_inquirer.database)
        history_db = DBHistoryEvents(self.node_inquirer.database)

        for address in addresses:
            with self.node_inquirer.database.conn.read_ctx() as cursor:
                ranges_to_query = ranges.get_location_query_ranges(
                    cursor=cursor,
                    location_string=f'hyperliquid_{address}',
                    start_ts=from_timestamp,
                    end_ts=to_timestamp,
                )

            for range_start, range_end in ranges_to_query:
                try:
                    events = api.query_history_events(
                        address=address,
                        start_ts=range_start,
                        end_ts=range_end,
                    )
                except RemoteError as e:
                    log.error(
                        f'Failed to query hyperliquid history for {address} '
                        f'from {range_start} to {range_end} due to {e}',
                    )
                    self.transactions.msg_aggregator.add_error(
                        f'Failed to query Hyperliquid history for {address}. '
                        'Will retry in a future sync.',
                    )
                    continue

                with self.node_inquirer.database.user_write() as write_cursor:
                    history_db.add_history_events(write_cursor=write_cursor, history=events)
                    ranges.update_used_query_range(
                        write_cursor=write_cursor,
                        location_string=f'hyperliquid_{address}',
                        queried_ranges=[(range_start, range_end)],
                    )

    def query_transactions(
            self,
            addresses: list[ChecksumEvmAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> None:
        """Query EVM transactions and Hyperliquid core history for the addresses."""
        super().query_transactions(
            addresses=addresses,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )
        self.query_proprietary_history(
            addresses=addresses,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )
