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
from typing import TYPE_CHECKING, Dict, List, Literal, Optional, Set

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
from rotkehlchen.constants import ZERO
from rotkehlchen.errors.misc import ModuleInitializationFailure, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import (
    AssetAmount,
    ChainID,
    ChecksumEvmAddress,
    Location,
    Price,
    Timestamp,
    deserialize_evm_tx_hash,
)
from rotkehlchen.user_messages import MessagesAggregator

from .graph import BURNS_QUERY, LIQUIDITY_POSITIONS_QUERY, MINTS_QUERY, TOKEN_DAY_DATAS_QUERY

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


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
        elif self.location == Location.SUSHISWAP:
            self.mint_event = EventType.MINT_SUSHISWAP
            self.burn_event = EventType.BURN_SUSHISWAP
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
                token0 = pool_balance[pool].assets[0].token
                token1 = pool_balance[pool].assets[1].token
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
                    token0_deserialized = deserialize_evm_address(token0_['id'])
                    token1_deserialized = deserialize_evm_address(token1_['id'])
                    pool_deserialized = deserialize_evm_address(event['pair']['id'])
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
                    token_address = deserialize_evm_address(tdd['token']['id'])
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
                    user_address = deserialize_evm_address(lp['user']['id'])
                    lp_address = deserialize_evm_address(lp_pair['id'])
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
                        deserialized_eth_address = deserialize_evm_address(token['id'])
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
                        token=asset,
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
