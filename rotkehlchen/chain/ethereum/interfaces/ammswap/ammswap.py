"""
Implements an interface for ethereum modules that are AMM with support for subgraphs
implementing functionalities similar to the Uniswap one.

This interface is used at the moment in:

- Uniswap Module
- Sushiswap Module
"""
import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Optional

from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import (
    AggregatedAmount,
    AssetToPrice,
    LiquidityPool,
    LiquidityPoolEventsBalance,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_WETH
from rotkehlchen.constants.misc import ZERO_PRICE
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EvmTokenKind, Timestamp
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


UNISWAP_TRADES_PREFIX = 'uniswap_trades'
SUSHISWAP_TRADES_PREFIX = 'sushiswap_trades'


class AMMSwapPlatform:
    """AMM Module interace"""
    def __init__(
            self,
            counterparties: list[str],
            ethereum_inquirer: 'EthereumInquirer',
            database: 'DBHandler',
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.counterparties = counterparties
        self.ethereum = ethereum_inquirer
        self.database = database
        self.premium = premium
        self.msg_aggregator = msg_aggregator
        self.data_directory = database.user_data_dir.parent

    @staticmethod
    def _get_known_asset_price(
            known_assets: set[EvmToken],
            unknown_assets: set[EvmToken],
    ) -> AssetToPrice:
        """Get the tokens prices via Inquirer

        Given an asset, if `find_usd_price()` returns zero, it will be added
        into `unknown_assets`.
        """
        asset_price: AssetToPrice = {}

        for known_asset in known_assets:
            asset_usd_price = Inquirer().find_usd_price(known_asset)

            if asset_usd_price != ZERO_PRICE:
                asset_price[known_asset.evm_address] = asset_usd_price
            else:
                unknown_assets.add(known_asset)

        return asset_price

    def _calculate_events_balances(
            self,
            events: list[EvmEvent],
            balances: list[LiquidityPool],
    ) -> list[LiquidityPoolEventsBalance]:
        """Given an address, its LP events and the current LPs participating in
        (`balances`), process each event (grouped by pool) aggregating the
        token0, token1 and USD amounts for calculating the profit/loss in the
        pool. Finally return a list of <LiquidityPoolEventsBalance>, where each
        contains the profit/loss and events per pool.

        If `balances` is empty that means either the address does not have
        balances in the protocol or the endpoint has been called with a
        specific time range.
        """
        events_balances: list[LiquidityPoolEventsBalance] = []
        pool_balance: dict[ChecksumEvmAddress, LiquidityPool] = (
            {pool.address: pool for pool in balances}
        )
        pool_aggregated_amount: dict[EvmToken, AggregatedAmount] = {}
        # Populate `pool_aggregated_amount` dict, being the keys the pools'
        # addresses and the values the aggregated amounts from their events
        for event in events:
            if event.extra_data is None or (pool_address := event.extra_data.get('pool_address')) is None:  # noqa: E501
                continue

            pool_token = EvmToken(evm_address_to_identifier(address=pool_address, chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20))  # noqa: E501

            if pool_token not in pool_aggregated_amount:
                pool_aggregated_amount[pool_token] = AggregatedAmount()

            underlying0 = EvmToken(evm_address_to_identifier(address=pool_token.underlying_tokens[0].address, chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20))  # noqa: E501
            if pool_token.underlying_tokens[0] != A_WETH:
                asset_list = (underlying0,)
            else:
                asset_list = (A_ETH, A_WETH)

            event_asset_is_token_0 = event.asset in asset_list

            if event.event_subtype == HistoryEventSubType.DEPOSIT_ASSET:
                if event_asset_is_token_0 is True:
                    pool_aggregated_amount[pool_token].profit_loss0 -= event.balance.amount
                else:
                    pool_aggregated_amount[pool_token].profit_loss1 -= event.balance.amount
                pool_aggregated_amount[pool_token].usd_profit_loss -= event.balance.usd_value
            else:  # event_type == HistoryEventSubType.REMOVE_ASSET
                if event_asset_is_token_0 is True:
                    pool_aggregated_amount[pool_token].profit_loss0 += event.balance.amount
                else:
                    pool_aggregated_amount[pool_token].profit_loss1 += event.balance.amount
                pool_aggregated_amount[pool_token].usd_profit_loss += event.balance.usd_value

        # Instantiate `LiquidityPoolEventsBalance` per pool using
        # `pool_aggregated_amount`. If `pool_balance` exists (all events case),
        # factorise in the current pool balances in the totals.
        for pool, aggregated_amount in pool_aggregated_amount.items():
            profit_loss0 = aggregated_amount.profit_loss0
            profit_loss1 = aggregated_amount.profit_loss1
            usd_profit_loss = aggregated_amount.usd_profit_loss

            # Add current pool balances by looking up the pool
            if pool in pool_balance:
                token0 = pool_balance[pool].assets[0].token
                token1 = pool_balance[pool].assets[1].token
                profit_loss0 += pool_balance[pool].assets[0].user_balance.amount
                profit_loss1 += pool_balance[pool].assets[1].user_balance.amount
                usd_profit_loss += pool_balance[pool].user_balance.usd_value
            else:
                # NB: get `token0` and `token1` from any pool event
                token0 = EvmToken(evm_address_to_identifier(address=pool.underlying_tokens[0].address, chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20))  # noqa: E501
                token1 = EvmToken(evm_address_to_identifier(address=pool.underlying_tokens[1].address, chain_id=ChainID.ETHEREUM, token_type=EvmTokenKind.ERC20))  # noqa: E501

            events_balance = LiquidityPoolEventsBalance(
                pool_address=pool.evm_address,
                token0=token0,
                token1=token1,
                profit_loss0=profit_loss0,
                profit_loss1=profit_loss1,
                usd_profit_loss=usd_profit_loss,
            )
            events_balances.append(events_balance)

        return events_balances

    def get_stats_for_addresses(
            self,
            addresses: Optional[list[ChecksumEvmAddress]],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ):
        db = DBHistoryEvents(self.database)
        stats = {}
        for address in addresses:
            filter = EvmEventFilterQuery.make(
                counterparties=self.counterparties,
                location_labels=[address],
                from_ts=from_timestamp,
                to_ts=to_timestamp,
                event_subtypes=[
                    HistoryEventSubType.DEPOSIT_ASSET,
                    HistoryEventSubType.REMOVE_ASSET,
                ],
            )
            with self.database.conn.read_ctx() as cursor:
                events = db.get_history_events(
                    cursor=cursor,
                    filter_query=filter,
                    has_premium=self.premium is not None,
                    group_by_event_ids=False,
                )
            stats[address] = self._calculate_events_balances(
                events=events,
                balances=[],
            )
        return stats

    def get_lp_addresses(
            self,
            addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, list[Asset]]:
        """Query the LP tokens where the provided users have ever deposited"""
        db_filter = EvmEventFilterQuery.make(
            counterparties=self.counterparties,
            location_labels=addresses,
            event_subtypes=[
                HistoryEventSubType.RECEIVE_WRAPPED,
            ],
        )
        query, bindings = db_filter.prepare()
        address_to_pools = defaultdict(list)
        with self.database.conn.read_ctx() as cursor:
            cursor.execute('select location_label, asset from history_events JOIN evm_events_info ON history_events.identifier = evm_events_info.identifier ' + query, bindings)  # noqa: E501
            for address, lp_token in cursor:
                address_to_pools[string_to_evm_address(address)].append(Asset(lp_token))

        return address_to_pools
