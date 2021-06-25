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

from .graph import (
    BURNS_QUERY,
    LIQUIDITY_POSITIONS_QUERY,
    MINTS_QUERY,
    SWAPS_QUERY,
    TOKEN_DAY_DATAS_QUERY,
    V3_SWAPS_QUERY,
)
from .typing import (
    UNISWAP_EVENTS_PREFIX,
    UNISWAP_TRADES_PREFIX,
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
from .utils import SUBGRAPH_REMOTE_ERROR_MSG, get_latest_lp_addresses, uniswap_lp_token_balances

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures import AssetBalance
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler

log = logging.getLogger(__name__)


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


class Uniswap(EthereumModule):
    """Uniswap integration module

    * Uniswap subgraph:
    https://github.com/Uniswap/uniswap-v2-subgraph
    """
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
        try:
            self.graph = Graph(
                'https://api.thegraph.com/subgraphs/name/benesjan/uniswap-v2',
            )
            self.graph_v3 = Graph(
                'https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3',
            )
        except RemoteError as e:
            self.msg_aggregator.add_error(SUBGRAPH_REMOTE_ERROR_MSG.format(error_msg=str(e)))
            raise ModuleInitializationFailure('subgraph remote error') from e

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

    def _get_balances_graph(
            self,
            addresses: List[ChecksumEthAddress],
    ) -> ProtocolBalance:
        """Get the addresses' pools data querying the Uniswap subgraph

        Each liquidity position is converted into a <LiquidityPool>.
        """
        address_balances: DDAddressToLPBalances = defaultdict(list)
        known_assets: Set[EthereumToken] = set()
        unknown_assets: Set[EthereumToken] = set()

        addresses_lower = [address.lower() for address in addresses]
        querystr = format_query_indentation(LIQUIDITY_POSITIONS_QUERY.format())
        param_types = {
            '$limit': 'Int!',
            '$offset': 'Int!',
            '$addresses': '[String!]',
            '$balance': 'BigDecimal!',
        }
        param_values = {
            'limit': GRAPH_QUERY_LIMIT,
            'offset': 0,
            'addresses': addresses_lower,
            'balance': '0',
        }
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
                        f'Failed to Deserialize address. Skipping pool {lp_pair}'
                        f'with user address {lp["user"]["id"]}'
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
                            f'Failed to deserialize token address {token["id"]}'
                            f'Bad token address in lp pair came from the graph.'
                        )
                        log.error(msg)
                        raise RemoteError(msg) from e

                    asset = get_or_create_ethereum_token(
                        userdb=self.database,
                        symbol=token['symbol'],
                        ethereum_address=deserialized_eth_address,
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

            # Check whether an extra request is needed
            if len(result_data) < GRAPH_QUERY_LIMIT:
                break

            # Update pagination step
            param_values = {
                **param_values,
                'offset': param_values['offset'] + GRAPH_QUERY_LIMIT,  # type: ignore
            }

        protocol_balance = ProtocolBalance(
            address_balances=dict(address_balances),
            known_assets=known_assets,
            unknown_assets=unknown_assets,
        )
        return protocol_balance

    def get_balances_chain(self, addresses: List[ChecksumEthAddress]) -> ProtocolBalance:
        """Get the addresses' pools data via chain queries.
        """
        known_assets: Set[EthereumToken] = set()
        unknown_assets: Set[EthereumToken] = set()
        lp_addresses = get_latest_lp_addresses(self.data_directory)

        address_mapping = {}
        for address in addresses:
            pool_balances = uniswap_lp_token_balances(
                userdb=self.database,
                address=address,
                ethereum=self.ethereum,
                lp_addresses=lp_addresses,
                known_assets=known_assets,
                unknown_assets=unknown_assets,
            )
            if len(pool_balances) != 0:
                address_mapping[address] = pool_balances

        protocol_balance = ProtocolBalance(
            address_balances=address_mapping,
            known_assets=known_assets,
            unknown_assets=unknown_assets,
        )
        return protocol_balance

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
        address_events_balances: AddressEventsBalances = {}
        address_events: DDAddressEvents = defaultdict(list)
        db_address_events: AddressEvents = {}
        new_addresses: List[ChecksumEthAddress] = []
        existing_addresses: List[ChecksumEthAddress] = []
        min_end_ts: Timestamp = to_timestamp

        # Get addresses' last used query range for Uniswap events
        for address in addresses:
            entry_name = f'{UNISWAP_EVENTS_PREFIX}_{address}'
            events_range = self.database.get_used_query_range(name=entry_name)

            if not events_range:
                new_addresses.append(address)
            else:
                existing_addresses.append(address)
                min_end_ts = min(min_end_ts, events_range[1])

        # Request new addresses' events
        if new_addresses:
            start_ts = Timestamp(0)
            for address in new_addresses:
                for event_type in EventType:
                    new_address_events = self._get_events_graph(
                        address=address,
                        start_ts=start_ts,
                        end_ts=to_timestamp,
                        event_type=event_type,
                    )
                    if new_address_events:
                        address_events[address].extend(new_address_events)

                # Insert new address' last used query range
                self.database.update_used_query_range(
                    name=f'{UNISWAP_EVENTS_PREFIX}_{address}',
                    start_ts=start_ts,
                    end_ts=to_timestamp,
                )

        # Request existing DB addresses' events
        if existing_addresses and to_timestamp > min_end_ts:
            for address in existing_addresses:
                for event_type in EventType:
                    address_new_events = self._get_events_graph(
                        address=address,
                        start_ts=min_end_ts,
                        end_ts=to_timestamp,
                        event_type=event_type,
                    )
                    if address_new_events:
                        address_events[address].extend(address_new_events)

                # Update existing address' last used query range
                self.database.update_used_query_range(
                    name=f'{UNISWAP_EVENTS_PREFIX}_{address}',
                    start_ts=min_end_ts,
                    end_ts=to_timestamp,
                )

        # Insert requested events in DB
        all_events = []
        for address in filter(lambda address: address in address_events, addresses):
            all_events.extend(address_events[address])

        self.database.add_uniswap_events(all_events)

        # Fetch all DB events within the time range
        for address in addresses:
            db_events = self.database.get_uniswap_events(
                from_ts=from_timestamp,
                to_ts=to_timestamp,
                address=address,
            )
            if db_events:
                # return events with the oldest first
                db_events.sort(key=lambda event: (event.timestamp, event.log_index))
                db_address_events[address] = db_events

        # Request addresses' current balances (UNI-V2s and underlying tokens)
        # if there is no specific time range in this endpoint call (i.e. all
        # events). Current balances in the protocol are needed for an accurate
        # profit/loss calculation.
        # TODO: when this endpoint is called with a specific time range,
        # getting the balances and underlying tokens within that time range
        # requires an archive node. Feature pending to be developed.
        address_balances: AddressToLPBalances = {}  # Empty when specific time range
        if from_timestamp == Timestamp(0):
            address_balances = self.get_balances(addresses)

        # Calculate addresses' event balances (i.e. profit/loss per pool)
        for address, events in db_address_events.items():
            balances = address_balances.get(address, [])  # Empty when specific time range
            events_balances = self._calculate_events_balances(
                address=address,
                events=events,
                balances=balances,
            )
            address_events_balances[address] = events_balances

        return address_events_balances

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

    def _fetch_trades_from_db(
            self,
            addresses: List[ChecksumEthAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> AddressTrades:
        """Fetch all DB Uniswap trades within the time range"""
        db_address_trades: AddressTrades = {}
        for address in addresses:
            db_swaps = self.database.get_amm_swaps(
                from_ts=from_timestamp,
                to_ts=to_timestamp,
                location=Location.UNISWAP,
                address=address,
            )
            db_trades = self.swaps_to_trades(db_swaps)
            if db_trades:
                db_address_trades[address] = db_trades

        return db_address_trades

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
        address_amm_trades: AddressTrades = {}
        new_addresses: List[ChecksumEthAddress] = []
        existing_addresses: List[ChecksumEthAddress] = []
        min_end_ts: Timestamp = to_timestamp

        if only_cache:
            return self._fetch_trades_from_db(addresses, from_timestamp, to_timestamp)

        # Get addresses' last used query range for Uniswap trades
        for address in addresses:
            entry_name = f'{UNISWAP_TRADES_PREFIX}_{address}'
            trades_range = self.database.get_used_query_range(name=entry_name)

            if not trades_range:
                new_addresses.append(address)
            else:
                existing_addresses.append(address)
                min_end_ts = min(min_end_ts, trades_range[1])

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
                entry_name = f'{UNISWAP_TRADES_PREFIX}_{address}'
                self.database.update_used_query_range(
                    name=entry_name,
                    start_ts=start_ts,
                    end_ts=to_timestamp,
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
                entry_name = f'{UNISWAP_TRADES_PREFIX}_{address}'
                self.database.update_used_query_range(
                    name=entry_name,
                    start_ts=min_end_ts,
                    end_ts=to_timestamp,
                )

        # Insert all unique swaps to the D
        all_swaps = set()
        for address in filter(lambda address: address in address_amm_trades, addresses):
            for trade in address_amm_trades[address]:
                for swap in trade.swaps:
                    all_swaps.add(swap)

        self.database.add_amm_swaps(list(all_swaps))
        return self._fetch_trades_from_db(addresses, from_timestamp, to_timestamp)

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
                trades.extend(Uniswap._tx_swaps_to_trades(current_swaps))
                current_swaps = []

            current_swaps.append(swap)
            last_tx_hash = swap.tx_hash

        if len(current_swaps) != 0:
            trades.extend(Uniswap._tx_swaps_to_trades(current_swaps))
        return trades

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

    def _get_trades_graph_for_address(
            self,
            address: ChecksumEthAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AMMTrade]:
        trades = []
        try:
            trades.extend(self._get_trades_graph_v2_for_address(address, start_ts, end_ts))
        except RemoteError as e:
            log.error(
                f'Error querying uniswap v2 trades using graph for address {address} '
                f'between {start_ts} and {end_ts}. {str(e)}',
            )
        try:
            trades.extend(self._get_trades_graph_v3_for_address(address, start_ts, end_ts))
        except RemoteError as e:
            log.error(
                f'Error querying uniswap v3 trades using graph for address {address} '
                f'between {start_ts} and {end_ts}. {str(e)}',
            )
        return trades

    def _get_trades_graph_v2_for_address(
            self,
            address: ChecksumEthAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AMMTrade]:
        """Get the address' trades data querying the Uniswap subgraph

        Each trade (swap) instantiates an <AMMTrade>.

        The trade pair (i.e. BASE_QUOTE) is determined by `reserve0_reserve1`.
        Translated to Uniswap lingo:

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
        querystr = format_query_indentation(SWAPS_QUERY.format())

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

            for entry in result['swaps']:
                swaps = []
                for swap in entry['transaction']['swaps']:
                    timestamp = swap['timestamp']
                    swap_token0 = swap['pair']['token0']
                    swap_token1 = swap['pair']['token1']

                    try:
                        token0_deserialized = deserialize_ethereum_address(swap_token0['id'])
                        token1_deserialized = deserialize_ethereum_address(swap_token1['id'])
                        from_address_deserialized = deserialize_ethereum_address(swap['sender'])
                        to_address_deserialized = deserialize_ethereum_address(swap['to'])
                    except DeserializationError:
                        msg = (
                            f'Failed to deserialize addresses in trade from uniswap graph with '
                            f'token 0: {swap_token0["id"]}, token 1: {swap_token1["id"]}, '
                            f'swap sender: {swap["sender"]}, swap receiver {swap["to"]}'
                        )
                        log.error(msg)
                        continue

                    token0 = get_or_create_ethereum_token(
                        userdb=self.database,
                        symbol=swap_token0['symbol'],
                        ethereum_address=token0_deserialized,
                        name=swap_token0['name'],
                        decimals=swap_token0['decimals'],
                    )
                    token1 = get_or_create_ethereum_token(
                        userdb=self.database,
                        symbol=swap_token1['symbol'],
                        ethereum_address=token1_deserialized,
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
                            f'Failed to read amounts in Uniswap V2 swap {str(swap)}. '
                            f'{str(e)}.',
                        )
                        continue

                    swaps.append(AMMSwap(
                        tx_hash=swap['id'].split('-')[0],
                        log_index=int(swap['logIndex']),
                        address=address,
                        from_address=from_address_deserialized,
                        to_address=to_address_deserialized,
                        timestamp=Timestamp(int(timestamp)),
                        location=Location.UNISWAP,
                        token0=token0,
                        token1=token1,
                        amount0_in=AssetAmount(amount0_in),
                        amount1_in=AssetAmount(amount1_in),
                        amount0_out=AssetAmount(amount0_out),
                        amount1_out=AssetAmount(amount1_out),
                    ))

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
            param_values = {
                **param_values,
                'offset': param_values['offset'] + GRAPH_QUERY_LIMIT,  # type: ignore
            }
        return trades

    def _get_trades_graph_v3_for_address(
            self,
            address: ChecksumEthAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AMMTrade]:
        """Get the address' trades data querying the Uniswap subgraph

        Each trade (swap) instantiates an <AMMTrade>.

        The trade pair (i.e. BASE_QUOTE) is determined by `reserve0_reserve1`.
        Translated to Uniswap lingo:

        Trade type BUY:
        - `amount1` (QUOTE, reserve1) is gt 0.
        - `amount0` (BASE, reserve0) is lt 0.

        Trade type SELL:
        - `amount0` (BASE, reserve0) is gt 0.
        - `amount1` (QUOTE, reserve1) is lt 0.

        May raise:
        - RemoteError
        """
        trades: List[AMMTrade] = []
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
        querystr = format_query_indentation(V3_SWAPS_QUERY.format())

        while True:
            try:
                result = self.graph_v3.query(
                    querystr=querystr,
                    param_types=param_types,
                    param_values=param_values,
                )
            except RemoteError as e:
                self.msg_aggregator.add_error(SUBGRAPH_REMOTE_ERROR_MSG.format(error_msg=str(e)))
                raise

            result_data = result['swaps']
            for entry in result_data:
                swaps = []
                for swap in entry['transaction']['swaps']:
                    timestamp = swap['timestamp']
                    swap_token0 = swap['token0']
                    swap_token1 = swap['token1']

                    try:
                        token0_deserialized = deserialize_ethereum_address(swap_token0['id'])
                        token1_deserialized = deserialize_ethereum_address(swap_token1['id'])
                        from_address_deserialized = deserialize_ethereum_address(swap['sender'])
                        to_address_deserialized = deserialize_ethereum_address(swap['recipient'])
                    except DeserializationError:
                        msg = (
                            f'Failed to deserialize addresses in trade from uniswap graph with '
                            f'token 0: {swap_token0["id"]}, token 1: {swap_token1["id"]}, '
                            f'swap sender: {swap["sender"]}, swap receiver {swap["to"]}'
                        )
                        log.error(msg)
                        continue

                    token0 = get_or_create_ethereum_token(
                        userdb=self.database,
                        symbol=swap_token0['symbol'],
                        ethereum_address=token0_deserialized,
                        name=swap_token0['name'],
                        decimals=swap_token0['decimals'],
                    )
                    token1 = get_or_create_ethereum_token(
                        userdb=self.database,
                        symbol=swap_token1['symbol'],
                        ethereum_address=token1_deserialized,
                        name=swap_token1['name'],
                        decimals=int(swap_token1['decimals']),
                    )

                    try:
                        if swap['amount0'].startswith('-'):
                            amount0_in = AssetAmount(FVal(ZERO))
                            amount0_out = deserialize_asset_amount_force_positive(swap['amount0'])
                            amount1_in = deserialize_asset_amount_force_positive(swap['amount1'])
                            amount1_out = AssetAmount(FVal(ZERO))
                        else:
                            amount0_in = deserialize_asset_amount_force_positive(swap['amount0'])
                            amount0_out = AssetAmount(FVal(ZERO))
                            amount1_in = AssetAmount(FVal(ZERO))
                            amount1_out = deserialize_asset_amount_force_positive(swap['amount1'])
                    except ValueError as e:
                        log.error(
                            f'Failed to read amounts in Uniswap V3 swap {str(swap)}. '
                            f'{str(e)}.',
                        )
                        continue

                    swaps.append(AMMSwap(
                        tx_hash=swap['id'].split('#')[0],
                        log_index=int(swap['logIndex']),
                        address=address,
                        from_address=from_address_deserialized,
                        to_address=to_address_deserialized,
                        timestamp=Timestamp(int(timestamp)),
                        location=Location.UNISWAP,
                        token0=token0,
                        token1=token1,
                        amount0_in=amount0_in,
                        amount1_in=amount1_in,
                        amount0_out=amount0_out,
                        amount1_out=amount1_out,
                    ))

                # with the new logic the list of swaps can be empty, in that case don't try
                # to make trades from the swaps
                if len(swaps) == 0:
                    continue

                # Now that we got all swaps for a transaction, create the trade object
                trades.extend(self._tx_swaps_to_trades(swaps))
            # Check whether an extra request is needed
            if len(result_data) < GRAPH_QUERY_LIMIT:
                break

            # Update pagination step
            param_values = {
                **param_values,
                'offset': param_values['offset'] + GRAPH_QUERY_LIMIT,  # type: ignore
            }
        return trades

    def _get_unknown_asset_price_graph(
            self,
            unknown_assets: Set[EthereumToken],
    ) -> AssetToPrice:
        """Get today's tokens prices via the Uniswap subgraph

        Uniswap provides a token price every day at 00:00:00 UTC
        This function can raise RemoteError
        """
        asset_price: AssetToPrice = {}

        unknown_assets_addresses = (
            [asset.ethereum_address.lower() for asset in unknown_assets]
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
                self.msg_aggregator.add_error(SUBGRAPH_REMOTE_ERROR_MSG.format(error_msg=str(e)))
                raise

            result_data = result['tokenDayDatas']

            for tdd in result_data:
                try:
                    token_address = deserialize_ethereum_address(tdd['token']['id'])
                except DeserializationError as e:
                    msg = (
                        f'Error deserializing address {tdd["token"]["id"]} '
                        f'during uniswap prices query from graph.'
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

    def get_balances(
        self,
        addresses: List[ChecksumEthAddress],
    ) -> AddressToLPBalances:
        """Get the addresses' balances in the Uniswap protocol

        Premium users can request balances either via the Uniswap subgraph or
        on-chain.
        """
        if self.premium:
            protocol_balance = self._get_balances_graph(addresses=addresses)
        else:
            protocol_balance = self.get_balances_chain(addresses)

        known_assets = protocol_balance.known_assets
        unknown_assets = protocol_balance.unknown_assets

        known_asset_price = self._get_known_asset_price(
            known_assets=known_assets,
            unknown_assets=unknown_assets,
        )

        unknown_asset_price: AssetToPrice = {}
        if self.premium:
            unknown_asset_price = self._get_unknown_asset_price_graph(unknown_assets=unknown_assets)  # noqa:E501

        self._update_assets_prices_in_address_balances(
            address_balances=protocol_balance.address_balances,
            known_asset_price=known_asset_price,
            unknown_asset_price=unknown_asset_price,
        )

        return protocol_balance.address_balances

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

    def get_trades_history(
        self,
        addresses: List[ChecksumEthAddress],
        reset_db_data: bool,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> AddressTrades:
        """Get the addresses' trades history in the Uniswap protocol
        """
        with self.trades_lock:
            if reset_db_data is True:
                self.database.delete_uniswap_trades_data()

            trades = self._get_trades(
                addresses=addresses,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                only_cache=False,
            )

        return trades

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> Optional[List['AssetBalance']]:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass

    def deactivate(self) -> None:
        self.database.delete_uniswap_trades_data()
        self.database.delete_uniswap_events_data()
