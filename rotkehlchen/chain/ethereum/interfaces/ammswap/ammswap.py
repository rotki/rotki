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
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Sequence, Set, Tuple

from gevent.lock import Semaphore

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.graph import (
    GRAPH_QUERY_LIMIT,
    GRAPH_QUERY_SKIP_LIMIT,
    Graph,
    format_query_indentation,
)
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import (
    AddressEventsBalances,
    AddressToLPBalances,
    AddressTrades,
    AggregatedAmount,
    AssetToPrice,
    DDAddressToLPBalances,
    EventType,
    LiquidityPool,
    LiquidityPoolAsset,
    LiquidityPoolEvent,
    LiquidityPoolEventsBalance,
    ProtocolBalance,
)
from rotkehlchen.chain.ethereum.interfaces.ammswap.utils import (
    SUBGRAPH_REMOTE_ERROR_MSG,
    update_asset_price_in_lp_balances,
)
from rotkehlchen.chain.ethereum.trades import AMMSwap, AMMTrade
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.resolver import ChainID
from rotkehlchen.db.ranges import DBQueryRanges
from rotkehlchen.errors.misc import ModuleInitializationFailure, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.serialization.deserialize import deserialize_ethereum_address
from rotkehlchen.types import (
    AssetAmount,
    ChecksumEvmAddress,
    Location,
    Price,
    Timestamp,
    TradeType,
    deserialize_evm_tx_hash,
)
from rotkehlchen.user_messages import MessagesAggregator

from .graph import (
    BURNS_QUERY,
    LIQUIDITY_POSITIONS_QUERY,
    MINTS_QUERY,
    SUSHISWAP_SWAPS_QUERY,
    SWAPS_QUERY,
    TOKEN_DAY_DATAS_QUERY,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def add_trades_from_swaps(
        swaps: List[AMMSwap],
        trades: List[AMMTrade],
        both_in: bool,
        quote_assets: Sequence[Tuple[Any, ...]],
        token_amount: AssetAmount,
        token: EvmToken,
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


UNISWAP_TRADES_PREFIX = 'uniswap_trades'
SUSHISWAP_TRADES_PREFIX = 'sushiswap_trades'


class AMMSwapPlatform(metaclass=abc.ABCMeta):
    """AMM Module interace"""
    def __init__(
            self,
            location: Location,
            ethereum_manager: 'EthereumManager',
            database: 'DBHandler',
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
            graph: Graph,
    ) -> None:
        self.location = location
        self.ethereum = ethereum_manager
        self.database = database
        self.premium = premium
        self.msg_aggregator = msg_aggregator
        self.data_directory = database.user_data_dir.parent
        self.trades_lock = Semaphore()
        self.graph = graph

        if self.location == Location.UNISWAP:
            self.mint_event = EventType.MINT_UNISWAP
            self.burn_event = EventType.BURN_UNISWAP
            self.swaps_query = SWAPS_QUERY
            self.trades_prefix = UNISWAP_TRADES_PREFIX
        elif self.location == Location.SUSHISWAP:
            self.mint_event = EventType.MINT_SUSHISWAP
            self.burn_event = EventType.BURN_SUSHISWAP
            self.swaps_query = SUSHISWAP_SWAPS_QUERY
            self.trades_prefix = SUSHISWAP_TRADES_PREFIX
        else:
            raise NotImplementedError(f'AMM platform with location {self.location} not valid.')

    def _calculate_events_balances(
        self,
        address: ChecksumEvmAddress,
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
        pool_balance: Dict[ChecksumEvmAddress, LiquidityPool] = (
            {pool.address: pool for pool in balances}
        )
        pool_aggregated_amount: Dict[ChecksumEvmAddress, AggregatedAmount] = {}
        # Populate `pool_aggregated_amount` dict, being the keys the pools'
        # addresses and the values the aggregated amounts from their events
        for event in events:
            pool = event.pool_address

            if pool not in pool_aggregated_amount:
                pool_aggregated_amount[pool] = AggregatedAmount()

            pool_aggregated_amount[pool].events.append(event)

            if event.event_type == self.mint_event:
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

            # Add current pool balances by looking up the pool
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
            known_assets: Set[EvmToken],
            unknown_assets: Set[EvmToken],
    ) -> AssetToPrice:
        """Get the tokens prices via Inquirer

        Given an asset, if `find_usd_price()` returns zero, it will be added
        into `unknown_assets`.
        """
        asset_price: AssetToPrice = {}

        for known_asset in known_assets:
            asset_usd_price = Inquirer().find_usd_price(known_asset)

            if asset_usd_price != Price(ZERO):
                asset_price[known_asset.evm_address] = asset_usd_price
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
        """Update the Uniswap V2 & SushiSwap pools underlying assets prices in USD"""
        update_asset_price_in_lp_balances(
            address_balances=address_balances,
            known_asset_price=known_asset_price,
            unknown_asset_price=unknown_asset_price,
        )

    def _get_events_graph(
            self,
            address: ChecksumEvmAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
            event_type: EventType,
    ) -> List[LiquidityPoolEvent]:
        """Get the address' events (mints & burns) querying the AMM's subgraph
        Each event data is stored in a <LiquidityPoolEvent>.
        """
        address_events: List[LiquidityPoolEvent] = []
        if event_type == self.mint_event:
            query = MINTS_QUERY
            query_schema = 'mints'
        elif event_type == self.burn_event:
            query = BURNS_QUERY
            query_schema = 'burns'
        else:
            log.error(
                f'Unexpected {self.location} event_type: {event_type}. Skipping events query.',
            )
            return address_events

        query_id = '0'
        query_offset = 0
        param_types = {
            '$limit': 'Int!',
            '$offset': 'Int!',
            '$address': 'Bytes!',
            '$start_ts': 'BigInt!',
            '$end_ts': 'BigInt!',
            '$id': 'ID!',
        }
        param_values = {
            'limit': GRAPH_QUERY_LIMIT,
            'offset': query_offset,
            'address': address.lower(),
            'start_ts': str(start_ts),
            'end_ts': str(end_ts),
            'id': query_id,
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
                self.msg_aggregator.add_error(
                    SUBGRAPH_REMOTE_ERROR_MSG.format(error_msg=str(e), location=self.location),
                )
                raise
            except AttributeError as e:
                raise ModuleInitializationFailure(f'{self.location} subgraph remote error') from e

            result_data = result[query_schema]

            for event in result_data:
                token0_ = event['pair']['token0']
                token1_ = event['pair']['token1']

                try:
                    token0_deserialized = deserialize_ethereum_address(token0_['id'])
                    token1_deserialized = deserialize_ethereum_address(token1_['id'])
                    pool_deserialized = deserialize_ethereum_address(event['pair']['id'])
                    tx_hash_deserialized = deserialize_evm_tx_hash(event['transaction']['id'])
                except DeserializationError as e:
                    msg = (
                        f'Failed to deserialize address/txn hash involved in liquidity pool event '
                        f'for {self.location}. Token 0: {token0_["id"]}, token 1: {token0_["id"]},'
                        f' pair: {event["pair"]["id"]}.'
                    )
                    log.error(msg)
                    raise RemoteError(msg) from e

                token0 = get_or_create_evm_token(
                    userdb=self.database,
                    symbol=token0_['symbol'],
                    evm_address=token0_deserialized,
                    chain=ChainID.ETHEREUM,
                    name=token0_['name'],
                    decimals=token0_['decimals'],
                )
                token1 = get_or_create_evm_token(
                    userdb=self.database,
                    symbol=token1_['symbol'],
                    evm_address=token1_deserialized,
                    chain=ChainID.ETHEREUM,
                    name=token1_['name'],
                    decimals=int(token1_['decimals']),
                )
                lp_event = LiquidityPoolEvent(
                    tx_hash=tx_hash_deserialized,
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
                query_id = event['id']

            # Check whether an extra request is needed
            if len(result_data) < GRAPH_QUERY_LIMIT:
                break

            # Update pagination step
            if query_offset == GRAPH_QUERY_SKIP_LIMIT:
                query_offset = 0
                new_query_id = query_id
            else:
                query_offset += GRAPH_QUERY_LIMIT
                new_query_id = '0'
            param_values = {
                **param_values,
                'id': new_query_id,
                'offset': query_offset,
            }

        return address_events

    def _read_subgraph_trades(
            self,
            address: ChecksumEvmAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AMMTrade]:
        """Get the address' trades data querying the AMM subgraph

        Each trade (swap) instantiates an <AMMTrade>.

        The trade pair (i.e. BASE_QUOTE) is determined by `reserve0_reserve1`.
        Translated to AMM lingo:

        Trade type BUY:
        - `asset1In` (QUOTE, reserve1) is gt 0.
        - `asset0Out` (BASE, reserve0) is gt 0.

        Trade type SELL:
        - `asset0In` (BASE, reserve0) is gt 0.
        - `asset1Out` (QUOTE, reserve1) is gt 0.

        May raise
        - RemoteError
        """
        trades: List[AMMTrade] = []
        query_id = '0'
        query_offset = 0
        param_types = {
            '$limit': 'Int!',
            '$offset': 'Int!',
            '$address': 'Bytes!',
            '$start_ts': 'BigInt!',
            '$end_ts': 'BigInt!',
            '$id': 'ID!',
        }
        param_values = {
            'limit': GRAPH_QUERY_LIMIT,
            'offset': 0,
            'address': address.lower(),
            'start_ts': str(start_ts),
            'end_ts': str(end_ts),
            'id': query_id,
        }
        querystr = format_query_indentation(self.swaps_query.format())

        while True:
            try:
                result = self.graph.query(
                    querystr=querystr,
                    param_types=param_types,
                    param_values=param_values,
                )
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    SUBGRAPH_REMOTE_ERROR_MSG.format(error_msg=str(e), location=self.location),
                )
                raise

            for entry in result['swaps']:
                swaps = []
                try:
                    for swap in entry['transaction']['swaps']:
                        timestamp = swap['timestamp']
                        swap_token0 = swap['pair']['token0']
                        swap_token1 = swap['pair']['token1']

                        try:
                            token0_deserialized = deserialize_ethereum_address(swap_token0['id'])
                            token1_deserialized = deserialize_ethereum_address(swap_token1['id'])
                            from_address_deserialized = deserialize_ethereum_address(swap['sender'])  # noqa
                            to_address_deserialized = deserialize_ethereum_address(swap['to'])
                            tx_hash_deserialized = deserialize_evm_tx_hash(swap['id'].split('-')[0])  # noqa: 501
                        except DeserializationError:
                            msg = (
                                f'Failed to deserialize addresses/txn hash in trade from {self.location} graph'  # noqa
                                f' with token 0: {swap_token0["id"]}, token 1: {swap_token1["id"]}, '  # noqa
                                f'swap sender: {swap["sender"]}, swap receiver {swap["to"]}'
                            )
                            log.error(msg)
                            continue

                        token0 = get_or_create_evm_token(
                            userdb=self.database,
                            symbol=swap_token0['symbol'],
                            evm_address=token0_deserialized,
                            chain=ChainID.ETHEREUM,
                            name=swap_token0['name'],
                            decimals=swap_token0['decimals'],
                        )
                        token1 = get_or_create_evm_token(
                            userdb=self.database,
                            symbol=swap_token1['symbol'],
                            evm_address=token1_deserialized,
                            chain=ChainID.ETHEREUM,
                            name=swap_token1['name'],
                            decimals=int(swap_token1['decimals']),
                        )

                        try:
                            amount0_in = FVal(swap['amount0In'])
                            amount1_in = FVal(swap['amount1In'])
                            amount0_out = FVal(swap['amount0Out'])
                            amount1_out = FVal(swap['amount1Out'])
                        except ValueError as e:
                            log.error(
                                f'Failed to read amounts in {self.location} swap {str(swap)}. '
                                f'{str(e)}.',
                            )
                            continue

                        swaps.append(AMMSwap(
                            tx_hash=tx_hash_deserialized,
                            log_index=int(swap['logIndex']),
                            address=address,
                            from_address=from_address_deserialized,
                            to_address=to_address_deserialized,
                            timestamp=Timestamp(int(timestamp)),
                            location=self.location,
                            token0=token0,
                            token1=token1,
                            amount0_in=AssetAmount(amount0_in),
                            amount1_in=AssetAmount(amount1_in),
                            amount0_out=AssetAmount(amount0_out),
                            amount1_out=AssetAmount(amount1_out),
                        ))
                    query_id = entry['id']
                except KeyError as e:
                    log.error(
                        f'Failed to read trade in {self.location} swap {str(entry)}. '
                        f'{str(e)}.',
                    )
                    continue

                # with the new logic the list of swaps can be empty, in that case don't try
                # to make trades from the swaps
                if len(swaps) == 0:
                    continue

                # Now that we got all swaps for a transaction, create the trade object
                trades.extend(self._tx_swaps_to_trades(swaps))

            # Check whether an extra request is needed
            if len(result['swaps']) < GRAPH_QUERY_LIMIT:
                break

            # Update pagination step
            if query_offset == GRAPH_QUERY_SKIP_LIMIT:
                query_offset = 0
                new_query_id = query_id
            else:
                query_offset += GRAPH_QUERY_LIMIT
                new_query_id = '0'
            param_values = {
                **param_values,
                'id': new_query_id,
                'offset': query_offset,
            }

        return trades

    def _get_trades_graph(
            self,
            addresses: List[ChecksumEvmAddress],
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> AddressTrades:
        address_trades = {}
        for address in addresses:
            trades = self._get_trades_graph_for_address(address, start_ts, end_ts)
            if len(trades) != 0:
                address_trades[address] = trades

        return address_trades

    def _get_trades(
            self,
            addresses: List[ChecksumEvmAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            only_cache: bool,
    ) -> AddressTrades:
        """Request via graph all trades for new addresses and the latest ones
        for already existing addresses. Then the requested trade are written in
        DB and finally all DB trades are read and returned.
        """
        address_amm_trades: AddressTrades = {}
        new_addresses: List[ChecksumEvmAddress] = []
        existing_addresses: List[ChecksumEvmAddress] = []
        min_end_ts: Timestamp = to_timestamp

        with self.database.conn.read_ctx() as cursor:
            if only_cache:
                return self._fetch_trades_from_db(cursor, addresses, from_timestamp, to_timestamp)

            dbranges = DBQueryRanges(self.database)
            # Get addresses' last used query range for this AMM's trades
            for address in addresses:
                entry_name = f'{self.trades_prefix}_{address}'
                trades_range = self.database.get_used_query_range(cursor, name=entry_name)

                if not trades_range:
                    new_addresses.append(address)
                else:
                    existing_addresses.append(address)
                    min_end_ts = min(min_end_ts, trades_range[1])

        with self.database.user_write() as cursor:
            # Request new addresses' trades
            if new_addresses:
                start_ts = Timestamp(0)
                new_address_trades = self._get_trades_graph(
                    addresses=new_addresses,
                    start_ts=start_ts,
                    end_ts=to_timestamp,
                )
                address_amm_trades.update(new_address_trades)

                # Insert last used query range for new addresses
                for address in new_addresses:
                    entry_name = f'{self.trades_prefix}_{address}'
                    dbranges.update_used_query_range(
                        write_cursor=cursor,
                        location_string=entry_name,
                        queried_ranges=[(start_ts, to_timestamp)],
                    )

            # Request existing DB addresses' trades
            if existing_addresses and to_timestamp > min_end_ts:
                address_new_trades = self._get_trades_graph(
                    addresses=existing_addresses,
                    start_ts=min_end_ts,
                    end_ts=to_timestamp,
                )
                address_amm_trades.update(address_new_trades)

                # Update last used query range for existing addresses
                for address in existing_addresses:
                    entry_name = f'{self.trades_prefix}_{address}'
                    dbranges.update_used_query_range(
                        write_cursor=cursor,
                        location_string=entry_name,
                        queried_ranges=[(min_end_ts, to_timestamp)],
                    )

            # Insert all unique swaps to the DB
            all_swaps = set()
            for address in filter(lambda x: x in address_amm_trades, addresses):
                for trade in address_amm_trades[address]:
                    for swap in trade.swaps:
                        all_swaps.add(swap)

            self.database.add_amm_swaps(cursor, list(all_swaps))

        with self.database.conn.read_ctx() as cursor:
            return self._fetch_trades_from_db(cursor, addresses, from_timestamp, to_timestamp)

    def _get_unknown_asset_price_graph(
            self,
            unknown_assets: Set[EvmToken],
    ) -> AssetToPrice:
        """Get today's tokens prices via the AMM subgraph

        AMM provides a token price every day at 00:00:00 UTC
        This function can raise RemoteError
        """
        asset_price: AssetToPrice = {}

        unknown_assets_addresses = (
            [asset.evm_address.lower() for asset in unknown_assets]
        )
        querystr = format_query_indentation(TOKEN_DAY_DATAS_QUERY.format())
        today_epoch = int(
            datetime.combine(datetime.utcnow().date(), time.min).timestamp(),
        )
        param_types = {
            '$limit': 'Int!',
            '$offset': 'Int!',
            '$token_ids': '[String!]',
            '$datetime': 'Int!',
        }
        param_values = {
            'limit': GRAPH_QUERY_LIMIT,
            'offset': 0,
            'token_ids': unknown_assets_addresses,
            'datetime': today_epoch,
        }
        while True:
            try:
                result = self.graph.query(
                    querystr=querystr,
                    param_types=param_types,
                    param_values=param_values,
                )
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    SUBGRAPH_REMOTE_ERROR_MSG.format(error_msg=str(e), location=self.location),
                )
                raise

            result_data = result['tokenDayDatas']

            for tdd in result_data:
                try:
                    token_address = deserialize_ethereum_address(tdd['token']['id'])
                except DeserializationError as e:
                    msg = (
                        f'Error deserializing address {tdd["token"]["id"]} '
                        f'during {self.location} prices query from graph.'
                    )
                    log.error(msg)
                    raise RemoteError(msg) from e
                asset_price[token_address] = Price(FVal(tdd['priceUSD']))

            # Check whether an extra request is needed
            if len(result_data) < GRAPH_QUERY_LIMIT:
                break

            # Update pagination step
            param_values = {
                **param_values,
                'offset': param_values['offset'] + GRAPH_QUERY_LIMIT,  # type: ignore
            }

        return asset_price

    def get_events_history(
        self,
        addresses: List[ChecksumEvmAddress],
        reset_db_data: bool,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> AddressEventsBalances:
        """Get the addresses' events history in the AMM"""
        with self.trades_lock:
            with self.database.user_write() as cursor:
                if reset_db_data is True:
                    self.delete_events_data(cursor)

                address_events_balances = self._get_events_balances(
                    write_cursor=cursor,
                    addresses=addresses,
                    from_timestamp=from_timestamp,
                    to_timestamp=to_timestamp,
                )

        return address_events_balances

    def get_trades(
            self,
            addresses: List[ChecksumEvmAddress],
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
            cursor: 'DBCursor',
            addresses: List[ChecksumEvmAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> AddressTrades:
        """Fetch all DB AMM trades within the time range"""
        db_address_trades: AddressTrades = {}
        for address in addresses:
            db_swaps = self.database.get_amm_swaps(
                cursor=cursor,
                from_ts=from_timestamp,
                to_ts=to_timestamp,
                location=self.location,
                address=address,
            )
            db_trades = self.swaps_to_trades(db_swaps)
            if db_trades:
                db_address_trades[address] = db_trades

        return db_address_trades

    def _get_balances_graph(
            self,
            addresses: List[ChecksumEvmAddress],
    ) -> ProtocolBalance:
        """Get the addresses' pools data querying this AMM's subgraph

        Each liquidity position is converted into a <LiquidityPool>.
        """
        address_balances: DDAddressToLPBalances = defaultdict(list)
        known_assets: Set[EvmToken] = set()
        unknown_assets: Set[EvmToken] = set()

        addresses_lower = [address.lower() for address in addresses]
        querystr = format_query_indentation(LIQUIDITY_POSITIONS_QUERY.format())
        query_id = '0'
        query_offset = 0
        param_types = {
            '$limit': 'Int!',
            '$offset': 'Int!',
            '$addresses': '[String!]',
            '$balance': 'BigDecimal!',
            '$id': 'ID!',
        }
        param_values = {
            'limit': GRAPH_QUERY_LIMIT,
            'offset': 0,
            'addresses': addresses_lower,
            'balance': '0',
            'id': query_id,
        }
        while True:
            try:
                result = self.graph.query(
                    querystr=querystr,
                    param_types=param_types,
                    param_values=param_values,
                )
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    SUBGRAPH_REMOTE_ERROR_MSG.format(
                        error_msg=str(e),
                        location=self.location,
                    ),
                )
                raise

            result_data = result['liquidityPositions']
            for lp in result_data:
                lp_pair = lp['pair']
                lp_total_supply = FVal(lp_pair['totalSupply'])
                user_lp_balance = FVal(lp['liquidityTokenBalance'])
                try:
                    user_address = deserialize_ethereum_address(lp['user']['id'])
                    lp_address = deserialize_ethereum_address(lp_pair['id'])
                except DeserializationError as e:
                    msg = (
                        f'Failed to Deserialize address. Skipping {self.location} '
                        f'pool {lp_pair} with user address {lp["user"]["id"]}'
                    )
                    log.error(msg)
                    raise RemoteError(msg) from e

                # Insert LP tokens reserves within tokens dicts
                token0 = lp_pair['token0']
                token0['total_amount'] = lp_pair['reserve0']
                token1 = lp_pair['token1']
                token1['total_amount'] = lp_pair['reserve1']

                liquidity_pool_assets = []
                for token in token0, token1:
                    try:
                        deserialized_eth_address = deserialize_ethereum_address(token['id'])
                    except DeserializationError as e:
                        msg = (
                            f'Failed to deserialize token address {token["id"]} '
                            f'Bad token address in {self.location} lp pair came from the graph.'
                        )
                        log.error(msg)
                        raise RemoteError(msg) from e

                    asset = get_or_create_evm_token(
                        userdb=self.database,
                        symbol=token['symbol'],
                        evm_address=deserialized_eth_address,
                        chain=ChainID.ETHEREUM,
                        name=token['name'],
                        decimals=int(token['decimals']),
                    )
                    if asset.has_oracle():
                        known_assets.add(asset)
                    else:
                        unknown_assets.add(asset)

                    # Estimate the underlying asset total_amount
                    asset_total_amount = FVal(token['total_amount'])
                    user_asset_balance = (
                        user_lp_balance / lp_total_supply * asset_total_amount
                    )

                    liquidity_pool_asset = LiquidityPoolAsset(
                        asset=asset,
                        total_amount=asset_total_amount,
                        user_balance=Balance(amount=user_asset_balance),
                    )
                    liquidity_pool_assets.append(liquidity_pool_asset)

                liquidity_pool = LiquidityPool(
                    address=lp_address,
                    assets=liquidity_pool_assets,
                    total_supply=lp_total_supply,
                    user_balance=Balance(amount=user_lp_balance),
                )
                address_balances[user_address].append(liquidity_pool)
                query_id = lp['id']

            # Check whether an extra request is needed
            if len(result_data) < GRAPH_QUERY_LIMIT:
                break

            # Update pagination step
            if query_offset == GRAPH_QUERY_SKIP_LIMIT:
                query_offset = 0
                new_query_id = query_id
            else:
                query_offset += GRAPH_QUERY_LIMIT
                new_query_id = '0'
            param_values = {
                **param_values,
                'id': new_query_id,
                'offset': query_offset,
            }

        protocol_balance = ProtocolBalance(
            address_balances=dict(address_balances),
            known_assets=known_assets,
            unknown_assets=unknown_assets,
        )
        return protocol_balance

    def add_lp_tokens_to_db(
            self,
            lp_balances_mappings: AddressToLPBalances,
            protocol: Literal['uniswap-v2', 'sushiswap-v2'],
    ) -> None:
        """Adds LP token addresses to the database if not present."""
        name = 'Uniswap V2' if protocol == 'uniswap-v2' else 'SushiSwap LP Token'
        symbol = 'UNI-V2' if protocol == 'uniswap-v2' else 'SLP'
        for lp_balances in lp_balances_mappings.values():
            for lp_balance in lp_balances:
                get_or_create_evm_token(
                    userdb=self.database,
                    evm_address=lp_balance.address,
                    chain=ChainID.ETHEREUM,
                    decimals=18,
                    protocol=protocol,
                    name=name,
                    symbol=symbol,
                )

    @abc.abstractmethod
    def _get_trades_graph_for_address(
            self,
            address: ChecksumEvmAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AMMTrade]:
        raise NotImplementedError('should only be implemented by subclasses')

    @abc.abstractmethod
    def get_trades_history(
        self,
        addresses: List[ChecksumEvmAddress],
        reset_db_data: bool,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> AddressTrades:
        """Get the addresses' trades history in the AMMswap protocol"""
        raise NotImplementedError('should only be implemented by subclasses')

    @abc.abstractmethod
    def _get_events_balances(
            self,
            write_cursor: 'DBCursor',
            addresses: List[ChecksumEvmAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> AddressEventsBalances:
        """Request via graph all events for new addresses and the latest ones
        for already existing addresses. Then the requested events are written
        in DB and finally all DB events are read, and processed for calculating
        total profit/loss per LP (stored within <LiquidityPoolEventsBalance>).
        """
        raise NotImplementedError('should only be implemented by subclasses')

    @abc.abstractmethod
    def delete_events_data(self, write_cursor: 'DBCursor') -> None:
        raise NotImplementedError('should only be implemented by subclasses')
