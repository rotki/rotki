"""
Implements an interface for ethereum modules that are AMM with support for subgraphs
implementing functionalities similar to the Uniswap one.

This interface is used at the moment in:

- Uniswap Module
- Sushiswap Module
"""
import abc
import logging
from collections import defaultdict
from datetime import datetime, time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Set, Tuple

from gevent.lock import Semaphore

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.utils import get_or_create_ethereum_token
from rotkehlchen.chain.ethereum.graph import GRAPH_QUERY_LIMIT, Graph, format_query_indentation
from rotkehlchen.chain.ethereum.trades import AMMSwap, AMMTrade
from rotkehlchen.constants import ZERO
from rotkehlchen.errors import DeserializationError, ModuleInitializationFailure, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.premium.premium import Premium
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount_force_positive,
    deserialize_ethereum_address,
)
from rotkehlchen.typing import (
    AssetAmount,
    ChecksumEthAddress,
    Location,
    Price,
    Timestamp,
    TradeType,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.chain.ethereum.modules.ammswap.typing import (
    AddressEvents,
    AddressEventsBalances,
    AddressToLPBalances,
    AddressTrades,
    AggregatedAmount,
    AssetToPrice,
    DDAddressEvents,
    DDAddressToLPBalances,
    EventType,
    LiquidityPool,
    LiquidityPoolAsset,
    LiquidityPoolEvent,
    LiquidityPoolEventsBalance,
    ProtocolBalance,
)
from rotkehlchen.chain.ethereum.modules.ammswap.utils import SUBGRAPH_REMOTE_ERROR_MSG

from .graph import MINTS_QUERY, BURNS_QUERY

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures import AssetBalance
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler


def add_trades_from_swaps(
        swaps: List[AMMSwap],
        trades: List[AMMTrade],
        both_in: bool,
        quote_assets: Sequence[Tuple[Any, ...]],
        token_amount: AssetAmount,
        token: EthereumToken,
        trade_index: int,
) -> List[AMMTrade]:
    bought_amount = AssetAmount(token_amount / 2) if both_in else token_amount
    for entry in quote_assets:
        quote_asset = entry[0]
        sold_amount = entry[1]
        rate = sold_amount / bought_amount
        trade = AMMTrade(
            trade_type=TradeType.BUY,
            base_asset=token,
            quote_asset=quote_asset,
            amount=bought_amount,
            rate=rate,
            swaps=swaps,
            trade_index=trade_index,
        )
        trades.append(trade)
        trade_index += 1

    return trades


class AMMSwapPlatform(metaclass=abc.ABCMeta):
    """AMM Module interace"""
    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: 'DBHandler',
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum = ethereum_manager
        self.database = database
        self.premium = premium
        self.msg_aggregator = msg_aggregator
        self.data_directory = database.user_data_dir.parent
        self.trades_lock = Semaphore()

    @staticmethod
    def _calculate_events_balances(
            address: ChecksumEthAddress,
            events: List[LiquidityPoolEvent],
            balances: List[LiquidityPool],
    ) -> List[LiquidityPoolEventsBalance]:
        """Given an address, its LP events and the current LPs participating in
        (`balances`), process each event (grouped by pool) aggregating the
        token0, token1 and USD amounts for calculating the profit/loss in the
        pool. Finally return a list of <LiquidityPoolEventsBalance>, where each
        contains the profit/loss and events per pool.

        If `balances` is empty that means either the address does not have
        balances in the protocol or the endpoint has been called with a
        specific time range.
        """
        events_balances: List[LiquidityPoolEventsBalance] = []
        pool_balance: Dict[ChecksumEthAddress, LiquidityPool] = (
            {pool.address: pool for pool in balances}
        )
        pool_aggregated_amount: Dict[ChecksumEthAddress, AggregatedAmount] = {}
        # Populate `pool_aggregated_amount` dict, being the keys the pools'
        # addresses and the values the aggregated amounts from their events
        for event in events:
            pool = event.pool_address

            if pool not in pool_aggregated_amount:
                pool_aggregated_amount[pool] = AggregatedAmount()

            pool_aggregated_amount[pool].events.append(event)

            if event.event_type == EventType.MINT:
                pool_aggregated_amount[pool].profit_loss0 -= event.amount0
                pool_aggregated_amount[pool].profit_loss1 -= event.amount1
                pool_aggregated_amount[pool].usd_profit_loss -= event.usd_price
            else:  # event_type == EventType.BURN
                pool_aggregated_amount[pool].profit_loss0 += event.amount0
                pool_aggregated_amount[pool].profit_loss1 += event.amount1
                pool_aggregated_amount[pool].usd_profit_loss += event.usd_price

        # Instantiate `LiquidityPoolEventsBalance` per pool using
        # `pool_aggregated_amount`. If `pool_balance` exists (all events case),
        # factorise in the current pool balances in the totals.
        for pool, aggregated_amount in pool_aggregated_amount.items():
            profit_loss0 = aggregated_amount.profit_loss0
            profit_loss1 = aggregated_amount.profit_loss1
            usd_profit_loss = aggregated_amount.usd_profit_loss

            # Add current pool balances looking up the pool
            if pool in pool_balance:
                token0 = pool_balance[pool].assets[0].asset
                token1 = pool_balance[pool].assets[1].asset
                profit_loss0 += pool_balance[pool].assets[0].user_balance.amount
                profit_loss1 += pool_balance[pool].assets[1].user_balance.amount
                usd_profit_loss += pool_balance[pool].user_balance.usd_value
            else:
                # NB: get `token0` and `token1` from any pool event
                token0 = aggregated_amount.events[0].token0
                token1 = aggregated_amount.events[0].token1

            events_balance = LiquidityPoolEventsBalance(
                address=address,
                pool_address=pool,
                token0=token0,
                token1=token1,
                events=aggregated_amount.events,
                profit_loss0=profit_loss0,
                profit_loss1=profit_loss1,
                usd_profit_loss=usd_profit_loss,
            )
            events_balances.append(events_balance)

        return events_balances

    @staticmethod
    def _get_known_asset_price(
            known_assets: Set[EthereumToken],
            unknown_assets: Set[EthereumToken],
    ) -> AssetToPrice:
        """Get the tokens prices via Inquirer

        Given an asset, if `find_usd_price()` returns zero, it will be added
        into `unknown_assets`.
        """
        asset_price: AssetToPrice = {}

        for known_asset in known_assets:
            asset_usd_price = Inquirer().find_usd_price(known_asset)

            if asset_usd_price != Price(ZERO):
                asset_price[known_asset.ethereum_address] = asset_usd_price
            else:
                unknown_assets.add(known_asset)

        return asset_price

    @staticmethod
    def _tx_swaps_to_trades(swaps: List[AMMSwap]) -> List[AMMTrade]:
        """
        Turns a list of a transaction's swaps into a list of trades, taking into account
        the first and last swaps only for use with the rest of the rotki accounting.

        TODO: This is not nice, but we are constrained by the 1 token in
        1 token out concept of a trade we have right now. So if in a swap
        we have both tokens in we will create two trades, with the final
        amount being divided between the 2 trades. This is only so that
        the AMM trade can be processed easily in our current trades
        accounting.
        Make issue to process this properly as multitrades when we change
        the trade format
        """
        trades: List[AMMTrade] = []
        both_in = False
        both_out = False
        if swaps[0].amount0_in > ZERO and swaps[0].amount1_in > ZERO:
            both_in = True
        if swaps[-1].amount0_out > ZERO and swaps[-1].amount1_out > ZERO:
            both_out = True

        if both_in:
            quote_assets = [
                (swaps[0].token0, swaps[0].amount0_in if not both_out else swaps[0].amount0_in / 2),  # noqa: E501
                (swaps[0].token1, swaps[0].amount1_in if not both_out else swaps[0].amount1_in / 2),  # noqa: E501
            ]
        elif swaps[0].amount0_in > ZERO:
            quote_assets = [(swaps[0].token0, swaps[0].amount0_in)]
        else:
            quote_assets = [(swaps[0].token1, swaps[0].amount1_in)]

        trade_index = 0
        if swaps[-1].amount0_out > ZERO:
            trades = add_trades_from_swaps(
                swaps=swaps,
                trades=trades,
                both_in=both_in,
                quote_assets=quote_assets,
                token_amount=swaps[-1].amount0_out,
                token=swaps[-1].token0,
                trade_index=trade_index,
            )
            trade_index += len(trades)
        if swaps[-1].amount1_out > ZERO:
            trades = add_trades_from_swaps(
                swaps=swaps,
                trades=trades,
                both_in=both_in,
                quote_assets=quote_assets,
                token_amount=swaps[-1].amount1_out,
                token=swaps[-1].token1,
                trade_index=trade_index,
            )

        return trades

    @staticmethod
    def swaps_to_trades(swaps: List[AMMSwap]) -> List[AMMTrade]:
        trades: List[AMMTrade] = []
        if not swaps:
            return trades

        # sort by timestamp and then by log index
        swaps.sort(key=lambda trade: (trade.timestamp, -trade.log_index), reverse=True)
        last_tx_hash = swaps[0].tx_hash
        current_swaps: List[AMMSwap] = []
        for swap in swaps:
            if swap.tx_hash != last_tx_hash:
                trades.extend(AMMSwapPlatform._tx_swaps_to_trades(current_swaps))
                current_swaps = []

            current_swaps.append(swap)
            last_tx_hash = swap.tx_hash

        if len(current_swaps) != 0:
            trades.extend(AMMSwapPlatform._tx_swaps_to_trades(current_swaps))
        return trades

    @staticmethod
    def _update_assets_prices_in_address_balances(
            address_balances: AddressToLPBalances,
            known_asset_price: AssetToPrice,
            unknown_asset_price: AssetToPrice,
    ) -> None:
        """Update the pools underlying assets prices in USD (prices obtained
        via Inquirer and the Uniswap subgraph)
        """
        for lps in address_balances.values():
            for lp in lps:
                # Try to get price from either known or unknown asset price.
                # Otherwise keep existing price (zero)
                total_user_balance = FVal(0)
                for asset in lp.assets:
                    asset_ethereum_address = asset.asset.ethereum_address
                    asset_usd_price = known_asset_price.get(
                        asset_ethereum_address,
                        unknown_asset_price.get(asset_ethereum_address, Price(ZERO)),
                    )
                    # Update <LiquidityPoolAsset> if asset USD price exists
                    if asset_usd_price != Price(ZERO):
                        asset.usd_price = asset_usd_price
                        asset.user_balance.usd_value = FVal(
                            asset.user_balance.amount * asset_usd_price,
                        )

                    total_user_balance += asset.user_balance.usd_value

                # Update <LiquidityPool> total balance in USD
                lp.user_balance.usd_value = total_user_balance

    def _get_events_graph(
            self,
            address: ChecksumEthAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
            event_type: EventType,
    ) -> List[LiquidityPoolEvent]:
        """Get the address' events (mints & burns) querying the Uniswap subgraph
        Each event data is stored in a <LiquidityPoolEvent>.
        """
        address_events: List[LiquidityPoolEvent] = []
        if event_type == EventType.MINT:
            query = MINTS_QUERY
            query_schema = 'mints'
        elif event_type == EventType.BURN:
            query = BURNS_QUERY
            query_schema = 'burns'
        else:
            log.error(f'Unexpected event_type: {event_type}. Skipping events query.')
            return address_events

        param_types = {
            '$limit': 'Int!',
            '$offset': 'Int!',
            '$address': 'Bytes!',
            '$start_ts': 'BigInt!',
            '$end_ts': 'BigInt!',
        }
        param_values = {
            'limit': GRAPH_QUERY_LIMIT,
            'offset': 0,
            'address': address.lower(),
            'start_ts': str(start_ts),
            'end_ts': str(end_ts),
        }
        querystr = format_query_indentation(query.format())

        while True:
            try:
                result = self.graph.query(
                    querystr=querystr,
                    param_types=param_types,
                    param_values=param_values,
                )
            except RemoteError as e:
                self.msg_aggregator.add_error(SUBGRAPH_REMOTE_ERROR_MSG.format(error_msg=str(e)))
                raise

            result_data = result[query_schema]

            for event in result_data:
                token0_ = event['pair']['token0']
                token1_ = event['pair']['token1']

                try:
                    token0_deserialized = deserialize_ethereum_address(token0_['id'])
                    token1_deserialized = deserialize_ethereum_address(token1_['id'])
                    pool_deserialized = deserialize_ethereum_address(event['pair']['id'])
                except DeserializationError as e:
                    msg = (
                        f'Failed to deserialize address involved in liquidity pool event. '
                        f'Token 0: {token0_["id"]}, token 1: {token0_["id"]},'
                        f' pair: {event["pair"]["id"]}.'
                    )
                    log.error(msg)
                    raise RemoteError(msg) from e

                token0 = get_or_create_ethereum_token(
                    userdb=self.database,
                    symbol=token0_['symbol'],
                    ethereum_address=token0_deserialized,
                    name=token0_['name'],
                    decimals=token0_['decimals'],
                )
                token1 = get_or_create_ethereum_token(
                    userdb=self.database,
                    symbol=token1_['symbol'],
                    ethereum_address=token1_deserialized,
                    name=token1_['name'],
                    decimals=int(token1_['decimals']),
                )
                lp_event = LiquidityPoolEvent(
                    tx_hash=event['transaction']['id'],
                    log_index=int(event['logIndex']),
                    address=address,
                    timestamp=Timestamp(int(event['timestamp'])),
                    event_type=event_type,
                    pool_address=pool_deserialized,
                    token0=token0,
                    token1=token1,
                    amount0=AssetAmount(FVal(event['amount0'])),
                    amount1=AssetAmount(FVal(event['amount1'])),
                    usd_price=Price(FVal(event['amountUSD'])),
                    lp_amount=AssetAmount(FVal(event['liquidity'])),
                )
                address_events.append(lp_event)

            # Check whether an extra request is needed
            if len(result_data) < GRAPH_QUERY_LIMIT:
                break

            # Update pagination step
            param_values = {
                **param_values,
                'offset': param_values['offset'] + GRAPH_QUERY_LIMIT,  # type: ignore
            }

        return address_events

    @abc.abstractmethod
    def _fetch_trades_from_db(
            self,
            addresses: List[ChecksumEthAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> AddressTrades:
        raise NotImplementedError

    def _get_trades_graph(
            self,
            addresses: List[ChecksumEthAddress],
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> AddressTrades:
        address_trades = {}
        for address in addresses:
            trades = self._get_trades_graph_for_address(address, start_ts, end_ts)
            if len(trades) != 0:
                address_trades[address] = trades

        return address_trades

    def get_events_history(
        self,
        addresses: List[ChecksumEthAddress],
        reset_db_data: bool,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> AddressEventsBalances:
        """Get the addresses' events history in the Uniswap protocol
        """
        with self.trades_lock:
            if reset_db_data is True:
                self.database.delete_uniswap_events_data()

            address_events_balances = self._get_events_balances(
                addresses=addresses,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
            )

        return address_events_balances

    def get_trades(
            self,
            addresses: List[ChecksumEthAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            only_cache: bool,
    ) -> List[AMMTrade]:
        if len(addresses) == 0:
            return []

        with self.trades_lock:
            all_trades = []
            trade_mapping = self._get_trades(
                addresses=addresses,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                only_cache=only_cache,
            )
            for _, trades in trade_mapping.items():
                all_trades.extend(trades)

            return all_trades

    def _fetch_trades_from_db(
            self,
            addresses: List[ChecksumEthAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> AddressTrades:
        """Fetch all DB Sushiswap trades within the time range"""
        db_address_trades: AddressTrades = {}
        for address in addresses:
            db_swaps = self.database.get_amm_swaps(
                from_ts=from_timestamp,
                to_ts=to_timestamp,
                location=self.location,
                address=address,
            )
            db_trades = self.swaps_to_trades(db_swaps)
            if db_trades:
                db_address_trades[address] = db_trades

        return db_address_trades

    @abc.abstractmethod
    def _get_trades_graph_for_address(
            self,
            address: ChecksumEthAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AMMTrade]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_trades_history(
        self,
        addresses: List[ChecksumEthAddress],
        reset_db_data: bool,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> AddressTrades:
        """Get the addresses' trades history in the AMMswap protocol"""
        raise NotImplementedError

    @abc.abstractmethod
    def _get_trades(
            self,
            addresses: List[ChecksumEthAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            only_cache: bool,
    ) -> AddressTrades:
        """Request via graph all trades for new addresses and the latest ones
        for already existing addresses. Then the requested trade are written in
        DB and finally all DB trades are read and returned.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _get_events_balances(
            self,
            addresses: List[ChecksumEthAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> AddressEventsBalances:
        """Request via graph all events for new addresses and the latest ones
        for already existing addresses. Then the requested events are written
        in DB and finally all DB events are read, and processed for calculating
        total profit/loss per LP (stored within <LiquidityPoolEventsBalance>).
        """
        raise NotImplementedError

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> Optional[List['AssetBalance']]:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass

    @abc.abstractmethod
    def deactivate(self) -> None:
        raise NotImplementedError