import datetime
import logging
from collections import defaultdict
from operator import add, sub
from typing import TYPE_CHECKING, DefaultDict, List, Optional, Set, Tuple

from gevent.lock import Semaphore
from typing_extensions import Literal

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken, UnderlyingToken
from rotkehlchen.assets.utils import add_ethereum_token_to_db
from rotkehlchen.chain.ethereum.graph import (
    GRAPH_QUERY_LIMIT,
    GRAPH_QUERY_SKIP_LIMIT,
    Graph,
    format_query_indentation,
)
from rotkehlchen.chain.ethereum.modules.uniswap.graph import TOKEN_DAY_DATAS_QUERY
from rotkehlchen.chain.ethereum.trades import AMMSwap, AMMTrade
from rotkehlchen.constants import ZERO
from rotkehlchen.errors import DeserializationError, ModuleInitializationFailure, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.price import query_usd_price_or_use_default
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import AssetAmount, ChecksumEthAddress, Location, Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import ts_now

from .graph import (
    ADD_LIQUIDITIES_QUERY,
    BURNS_QUERY,
    MINTS_QUERY,
    POOLSHARES_QUERY,
    REMOVE_LIQUIDITIES_QUERY,
    SWAPS_QUERY,
    TOKENPRICES_QUERY,
)
from .typing import (
    BALANCER_EVENTS_PREFIX,
    BALANCER_TRADES_PREFIX,
    POOL_MAX_NUMBER_TOKENS,
    AddressToBPTEvents,
    AddressToEvents,
    AddressToEventsData,
    AddressToInvestEvents,
    AddressToPoolBalances,
    AddressToPoolEventsBalances,
    AddressToSwaps,
    AddressToTrades,
    BalancerBPTEventType,
    BalancerEvent,
    BalancerEventsData,
    BalancerInvestEventType,
    BalancerPoolBalance,
    BalancerPoolEventsBalance,
    DDAddressToEvents,
    DDAddressToPoolBalances,
    DDAddressToProfitLossAmounts,
    DDAddressToUniqueBPTEvents,
    DDAddressToUniqueInvestEvents,
    DDAddressToUniqueSwaps,
    PoolAddrToTokenAddrToIndex,
    ProtocolBalance,
    TokenToPrices,
)
from .utils import (
    SUBGRAPH_REMOTE_ERROR_MSG,
    UNISWAP_REMOTE_ERROR_MSG,
    deserialize_bpt_event,
    deserialize_invest_event,
    deserialize_pool_share,
    deserialize_swap,
    deserialize_token_day_data,
    deserialize_token_price,
    deserialize_transaction_id,
    get_trades_from_tx_swaps,
)

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures import AssetBalance
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Balancer(EthereumModule):
    """Balancer integration module"""
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
        self.trades_lock = Semaphore()
        try:
            # If both fail, let's take the safest approach and consider the module unusable
            self.graph = Graph(
                'https://api.thegraph.com/subgraphs/name/balancer-labs/balancer',
            )
            self.graph_events = Graph(
                'https://api.thegraph.com/subgraphs/name/yurycooliq/balancer',
            )
        except RemoteError as e:
            self.msg_aggregator.add_error(SUBGRAPH_REMOTE_ERROR_MSG.format(error_msg=str(e)))
            raise ModuleInitializationFailure('subgraph remote error') from e

        try:
            self.graph_uniswap: Optional[Graph] = Graph(
                'https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2',
            )
        except RemoteError as e:
            self.graph_uniswap = None
            self.msg_aggregator.add_error(UNISWAP_REMOTE_ERROR_MSG.format(error_msg=str(e)))

    @staticmethod
    def _calculate_pool_events_balances(
            address: ChecksumEthAddress,
            events: List[BalancerEvent],
            pool_balances: List[BalancerPoolBalance],
    ) -> List[BalancerPoolEventsBalance]:
        """Calculate the balance of the events on each pool the address has
        added or removed liquidity.
        """
        pool_addr_to_events: DDAddressToEvents = defaultdict(list)
        pool_addr_to_profit_loss_amounts: DDAddressToProfitLossAmounts = (
            defaultdict(lambda: [AssetAmount(ZERO)] * POOL_MAX_NUMBER_TOKENS)
        )
        pool_addr_to_usd_value: DefaultDict[EthereumToken, FVal] = defaultdict(lambda: ZERO)
        pool_events_balances: List[BalancerPoolEventsBalance] = []
        # Calculate the profit and loss of the pool events
        for event in events:
            pool_addr_to_events[event.pool_address_token].append(event)
            operator = sub if event.event_type == BalancerBPTEventType.MINT else add
            profit_loss_amounts = pool_addr_to_profit_loss_amounts[event.pool_address_token]
            event_amounts = event.amounts + [AssetAmount(ZERO)] * (POOL_MAX_NUMBER_TOKENS - len(event.amounts))  # noqa: E501
            pool_addr_to_profit_loss_amounts[event.pool_address_token] = list(
                map(operator, profit_loss_amounts, event_amounts),
            )
            usd_value = pool_addr_to_usd_value[event.pool_address_token]
            pool_addr_to_usd_value[event.pool_address_token] = operator(usd_value, event.lp_balance.usd_value)  # noqa: E501

        # Take into account the current pool balances
        for pool_balance in pool_balances:
            profit_loss_amounts = pool_addr_to_profit_loss_amounts[pool_balance.pool_token]
            for idx in range(len(pool_balance.underlying_tokens_balance)):
                profit_loss_amounts[idx] += pool_balance.underlying_tokens_balance[idx].user_balance.amount  # type: ignore # noqa: E501
                pool_addr_to_usd_value[pool_balance.pool_token] += pool_balance.underlying_tokens_balance[idx].user_balance.usd_value  # noqa: E501

        for pool_address_token, pool_events in pool_addr_to_events.items():
            pool_tokens = pool_address_token.underlying_tokens
            profit_loss_amounts = pool_addr_to_profit_loss_amounts[pool_address_token][:len(pool_tokens)]  # noqa: E501
            pool_events_balance = BalancerPoolEventsBalance(
                address=address,
                pool_address_token=pool_address_token,
                events=pool_events,  # Already sorted by timestamp and log_index
                profit_loss_amounts=profit_loss_amounts,
                usd_profit_loss=pool_addr_to_usd_value[pool_address_token],
            )
            pool_events_balances.append(pool_events_balance)

        return pool_events_balances

    def _fetch_trades_from_db(
            self,
            addresses: List[ChecksumEthAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> AddressToTrades:
        """Fetch all DB Balancer swaps within the time range and format as trades"""
        db_address_to_trades: AddressToTrades = {}
        for address in addresses:
            db_swaps = self.database.get_amm_swaps(
                from_ts=from_timestamp,
                to_ts=to_timestamp,
                location=Location.BALANCER,
                address=address,
            )
            if db_swaps:
                try:
                    db_trades = self._get_trades_from_swaps(db_swaps)
                except DeserializationError as e:
                    raise RemoteError('Failed to deserialize balancer trades') from e

                db_address_to_trades[address] = db_trades

        return db_address_to_trades

    def _get_address_to_bpt_events_graph(
            self,
            addresses: List[ChecksumEthAddress],
            transactions: List[str],
            event_type: Literal[BalancerBPTEventType.MINT, BalancerBPTEventType.BURN],
    ) -> AddressToBPTEvents:
        """Get a mapping of addresses to BPT events for a given time range

        May raise RemoteError
        """
        addresses_lower = [address.lower() for address in addresses]
        querystr: str
        schema: Literal['mints', 'burns']
        if event_type == BalancerBPTEventType.MINT:
            querystr = format_query_indentation(MINTS_QUERY.format())
            schema = 'mints'
        elif event_type == BalancerBPTEventType.BURN:
            querystr = format_query_indentation(BURNS_QUERY.format())
            schema = 'burns'
        else:
            raise AssertionError(f'Unexpected event type: {event_type}.')

        query_id = '0'
        query_offset = 0
        param_types = {
            '$limit': 'Int!',
            '$offset': 'Int!',
            '$id': 'ID!',
            '$addresses': '[ID!]',
            '$transactions': '[String!]',
        }
        param_values = {
            'limit': GRAPH_QUERY_LIMIT,
            'offset': query_offset,
            'id': query_id,
            'addresses': addresses_lower,
            'transactions': transactions,
        }
        address_to_unique_bpt_events: DDAddressToUniqueBPTEvents = defaultdict(set)
        while True:
            try:
                result = self.graph_events.query(
                    querystr=querystr,
                    param_types=param_types,
                    param_values=param_values,
                )
            except RemoteError as e:
                self.msg_aggregator.add_error(SUBGRAPH_REMOTE_ERROR_MSG.format(error_msg=str(e)))
                raise

            try:
                raw_events = result[schema]
            except KeyError as e:
                log.error(
                    f'Failed to deserialize balancer {event_type} events',
                    error=f'Missing key: {schema}',
                    result=result,
                    param_values=param_values,
                )
                raise RemoteError('Failed to deserialize balancer events') from e

            for raw_event in raw_events:
                try:
                    bpt_event = deserialize_bpt_event(self.database, raw_event, event_type=event_type)  # noqa: E501
                except DeserializationError as e:
                    log.error(
                        f'Failed to deserialize a {event_type} event',
                        error=str(e),
                        raw_event=raw_event,
                        param_values=param_values,
                    )
                    raise RemoteError('Failed to deserialize balancer events') from e

                address_to_unique_bpt_events[bpt_event.address].add(bpt_event)

            if len(raw_events) < GRAPH_QUERY_LIMIT:
                break

            if query_offset == GRAPH_QUERY_SKIP_LIMIT:
                query_id = f'{bpt_event.tx_hash}-{bpt_event.log_index}'
                query_offset = 0
            else:
                query_offset += GRAPH_QUERY_LIMIT

            param_values = {
                **param_values,
                'id': query_id,
                'offset': query_offset,
            }

        address_to_bpt_events: AddressToBPTEvents = {}
        for address, bpt_events in address_to_unique_bpt_events.items():
            address_to_bpt_events[address] = sorted(
                bpt_events,
                key=lambda event: (event.tx_hash, event.log_index),
            )
        return address_to_bpt_events

    def _get_address_to_events_data(
            self,
            addresses: List[ChecksumEthAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> AddressToEventsData:
        """Get a mapping of addresses to events data (addresses without events
        are not included in the returned dict).

        There are 2 groups of events: invest events and BPT events.
        - Invest event: contains the amount of a single token added or removed by
        the user into/from a pool. N invest events can happen at the same transaction.
        - BPT event: contains the total amount of BPT minted or burnt at the transaction
        where the related invest events took place.

        It is required to request 4 types:
        - Invest events: ADD_LIQUIDITY and REMOVE_LIQUIDITY. Both are filtered
        by addresses and timestamps.
        - BPT events: MINT and BURN. Both are filtered by the transactions of
        their respective invest events.

        NB: each MINT/BURN event must have at least 1 ADD_LIQUIDITY/REMOVE_LIQUIDITY
        event (and as many invest events as token amounts are involved in the transaction).
        Otherwise the subgraph is not providing all the required data.

        May raise RemoteError
        """
        # Get add liquidity and mint events per address
        address_to_add_liquidity_events, address_to_mint_events = self._get_address_to_invest_events_graph(  # noqa: E501
            addresses=addresses,
            start_ts=from_timestamp,
            end_ts=to_timestamp,
            event_type=BalancerInvestEventType.ADD_LIQUIDITY,
        )
        # Get remove liquidity and burn events per address
        address_to_remove_liquidity_events, address_to_burn_events = self._get_address_to_invest_events_graph(  # noqa: E501
            addresses=addresses,
            start_ts=from_timestamp,
            end_ts=to_timestamp,
            event_type=BalancerInvestEventType.REMOVE_LIQUIDITY,
        )
        self._update_used_query_range(
            addresses=addresses,
            prefix='balancer_events',
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )
        addresses_with_events = (
            set(address_to_add_liquidity_events.keys())
            .union(set(address_to_remove_liquidity_events.keys()))
        )
        address_to_events_data: AddressToEventsData = {}
        for address in addresses_with_events:
            address_to_events_data[address] = BalancerEventsData(
                add_liquidities=address_to_add_liquidity_events.get(address, []),
                remove_liquidities=address_to_remove_liquidity_events.get(address, []),
                mints=address_to_mint_events.get(address, []),
                burns=address_to_burn_events.get(address, []),
            )
        return address_to_events_data

    def _get_address_to_invest_events_graph(
            self,
            addresses: List[ChecksumEthAddress],
            event_type: Literal[
                BalancerInvestEventType.ADD_LIQUIDITY,
                BalancerInvestEventType.REMOVE_LIQUIDITY,
            ],
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> Tuple[AddressToInvestEvents, AddressToBPTEvents]:
        """Get a mapping of addresses to invest events for a given time range

        May raise RemoteError
        """
        addresses_lower = [address.lower() for address in addresses]
        querystr: str
        schema: Literal['addLiquidities', 'removeLiquidities']
        mint_or_burn_type: BalancerBPTEventType
        if event_type == BalancerInvestEventType.ADD_LIQUIDITY:
            querystr = format_query_indentation(ADD_LIQUIDITIES_QUERY.format())
            schema = 'addLiquidities'
            mint_or_burn_type = BalancerBPTEventType.MINT
        elif event_type == BalancerInvestEventType.REMOVE_LIQUIDITY:
            querystr = format_query_indentation(REMOVE_LIQUIDITIES_QUERY.format())
            schema = 'removeLiquidities'
            mint_or_burn_type = BalancerBPTEventType.BURN
        else:
            raise AssertionError(f'Unexpected event type: {event_type}.')

        query_start_ts = start_ts
        query_offset = 0
        param_types = {
            '$limit': 'Int!',
            '$offset': 'Int!',
            '$addresses': '[ID!]',
            '$start_ts': 'Int!',
            '$end_ts': 'Int!',
        }
        param_values = {
            'limit': GRAPH_QUERY_LIMIT,
            'offset': query_offset,
            'addresses': addresses_lower,
            'start_ts': query_start_ts,
            'end_ts': end_ts,
        }
        address_to_unique_invest_events: DDAddressToUniqueInvestEvents = defaultdict(set)
        while True:
            try:
                result = self.graph_events.query(
                    querystr=querystr,
                    param_types=param_types,
                    param_values=param_values,
                )
            except RemoteError as e:
                self.msg_aggregator.add_error(SUBGRAPH_REMOTE_ERROR_MSG.format(error_msg=str(e)))
                raise

            try:
                raw_events = result[schema]
            except KeyError as e:
                log.error(
                    f'Failed to deserialize balancer {event_type} events',
                    error=f'Missing key: {schema}',
                    result=result,
                    param_values=param_values,
                )
                raise RemoteError('Failed to deserialize balancer events') from e

            # first do a run to gather all transaction hashes. We need it to get all pool data
            mint_or_burn_transactions = {deserialize_transaction_id(x['id'])[0] for x in raw_events}  # noqa: E501
            address_to_mint_events = self._get_address_to_bpt_events_graph(
                addresses=addresses,
                transactions=list(mint_or_burn_transactions),
                event_type=mint_or_burn_type,
            )

            for raw_event in raw_events:
                try:
                    invest_event = deserialize_invest_event(raw_event, event_type=event_type)
                except DeserializationError as e:
                    log.error(
                        f'Failed to deserialize a {event_type} event',
                        error=str(e),
                        raw_event=raw_event,
                        start_ts=start_ts,
                        end_ts=end_ts,
                        param_values=param_values,
                    )
                    raise RemoteError('Failed to deserialize balancer events') from e

                address_to_unique_invest_events[invest_event.address].add(invest_event)

            if len(raw_events) < GRAPH_QUERY_LIMIT:
                break

            if query_offset == GRAPH_QUERY_SKIP_LIMIT:
                query_start_ts = invest_event.timestamp
                query_offset = 0
            else:
                query_offset += GRAPH_QUERY_LIMIT

            param_values = {
                **param_values,
                'start_ts': query_start_ts,
                'offset': query_offset,
            }

        address_to_invest_events: AddressToInvestEvents = {}
        for address, invest_events in address_to_unique_invest_events.items():
            address_to_invest_events[address] = sorted(
                invest_events,
                key=lambda event: (event.tx_hash, event.log_index),
            )
        return address_to_invest_events, address_to_mint_events

    def _get_address_to_pool_events_balances(
            self,
            addresses: List[ChecksumEthAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> AddressToPoolEventsBalances:
        """Get a mapping of addresses to pool events balance for a given time range

        May raise RemoteError
        """
        new_addresses: List[ChecksumEthAddress] = []
        existing_addresses: List[ChecksumEthAddress] = []
        min_to_timestamp: Timestamp = to_timestamp

        # Get the events last used query range of the addresses
        for address in addresses:
            entry_name = f'{BALANCER_EVENTS_PREFIX}_{address}'
            trades_range = self.database.get_used_query_range(name=entry_name)

            if not trades_range:
                new_addresses.append(address)
            else:
                existing_addresses.append(address)
                min_to_timestamp = min(min_to_timestamp, trades_range[1])

        address_to_events_data: AddressToEventsData = {}
        # Request the events of the new addresses
        if new_addresses:
            address_to_events_data_ = self._get_address_to_events_data(
                addresses=new_addresses,
                from_timestamp=Timestamp(0),
                to_timestamp=to_timestamp,
            )
            address_to_events_data.update(address_to_events_data_)

        # Request the events of the existing addresses
        if existing_addresses and to_timestamp > min_to_timestamp:
            address_to_events_data_ = self._get_address_to_events_data(
                addresses=existing_addresses,
                from_timestamp=min_to_timestamp,
                to_timestamp=to_timestamp,
            )
            address_to_events_data.update(address_to_events_data_)

        # Aggregate the events, get the new pools and store them all in the DB
        if len(address_to_events_data) != 0:
            balancer_events = self._get_balancer_aggregated_events_data(
                address_to_events_data=address_to_events_data,
            )
            self.database.add_balancer_events(balancer_events)

        # Calculate the balance of the events per pool at the given timestamp per address.
        # NB: take into account the current balances of each address in the protocol
        db_address_to_events: AddressToEvents = {}
        db_pool_addresses: Set[EthereumToken] = set()
        for address in addresses:
            db_events = self.database.get_balancer_events(
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                address=address,
            )
            if db_events:
                db_events.sort(key=lambda event: (event.timestamp, event.log_index))
                db_address_to_events[address] = db_events
                db_pool_addresses.union({db_event.pool_address_token for db_event in db_events})

        address_to_pool_events_balances: AddressToPoolEventsBalances = {}
        if len(db_address_to_events) == 0:
            return address_to_pool_events_balances

        # TODO: calculating the balances of an address at a particular timestamp
        # requires an archive node. Feature pending to be developed.
        address_to_pool_balances: AddressToPoolBalances = {}
        if from_timestamp == Timestamp(0):
            address_to_pool_balances = self.get_balances(addresses)

        for address, db_events in db_address_to_events.items():
            pool_balances = address_to_pool_balances.get(address, [])
            pool_events_balances = self._calculate_pool_events_balances(
                address=address,
                events=db_events,
                pool_balances=pool_balances,
            )
            address_to_pool_events_balances[address] = pool_events_balances

        return address_to_pool_events_balances

    def _get_address_to_swaps_graph(
            self,
            addresses: List[ChecksumEthAddress],
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> AddressToSwaps:
        """Get a mapping of addresses to swaps for a given time range

        May raise RemoteError
        """
        addresses_lower = [address.lower() for address in addresses]
        querystr = format_query_indentation(SWAPS_QUERY.format())
        query_start_ts = start_ts
        query_offset = 0
        param_types = {
            '$limit': 'Int!',
            '$offset': 'Int!',
            '$addresses': '[ID!]',
            '$start_ts': 'Int!',
            '$end_ts': 'Int!',
        }
        param_values = {
            'limit': GRAPH_QUERY_LIMIT,
            'offset': query_offset,
            'addresses': addresses_lower,
            'start_ts': query_start_ts,
            'end_ts': end_ts,
        }
        address_to_unique_swaps: DDAddressToUniqueSwaps = defaultdict(set)
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

            try:
                raw_swaps = result['swaps']
            except KeyError as e:
                log.error(
                    'Failed to deserialize balancer swaps',
                    error='Missing key: swaps',
                    result=result,
                    param_values=param_values,
                )
                raise RemoteError('Failed to deserialize balancer trades') from e

            for raw_swap in raw_swaps:
                try:
                    amm_swap = deserialize_swap(self.database, raw_swap)
                except DeserializationError as e:
                    log.error(
                        'Failed to deserialize a balancer swap',
                        error=str(e),
                        raw_swap=raw_swap,
                        start_ts=start_ts,
                        end_ts=end_ts,
                        param_values=param_values,
                    )
                    raise RemoteError('Failed to deserialize balancer trades') from e

                address_to_unique_swaps[amm_swap.address].add(amm_swap)

            if len(raw_swaps) < GRAPH_QUERY_LIMIT:
                break

            if query_offset == GRAPH_QUERY_SKIP_LIMIT:
                query_start_ts = amm_swap.timestamp
                query_offset = 0
            else:
                query_offset += GRAPH_QUERY_LIMIT

            param_values = {
                **param_values,
                'start_ts': query_start_ts,
                'offset': query_offset,
            }

        address_to_swaps: AddressToSwaps = {
            address: list(amm_swaps) for address, amm_swaps in address_to_unique_swaps.items()
        }
        return address_to_swaps

    def _get_address_to_trades(
            self,
            addresses: List[ChecksumEthAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            only_cache: bool,
    ) -> AddressToTrades:
        """Get a mapping of addresses to trades for a given time range

        Requests all the new swaps (since last used query range) of the existing
        addresses via subgraph.

        May raise RemoteError
        """
        new_addresses: List[ChecksumEthAddress] = []
        existing_addresses: List[ChecksumEthAddress] = []
        min_to_timestamp: Timestamp = to_timestamp

        if only_cache:
            return self._fetch_trades_from_db(
                addresses=addresses,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
            )

        # Get the trades last used query range of the addresses
        for address in addresses:
            entry_name = f'{BALANCER_TRADES_PREFIX}_{address}'
            trades_range = self.database.get_used_query_range(name=entry_name)

            if not trades_range:
                new_addresses.append(address)
            else:
                existing_addresses.append(address)
                min_to_timestamp = min(min_to_timestamp, trades_range[1])

        address_to_swaps: AddressToSwaps = {}
        # Request new addresses' trades
        if new_addresses:
            start_ts = Timestamp(0)
            address_to_swaps_ = self._get_address_to_swaps_graph(
                addresses=new_addresses,
                start_ts=start_ts,
                end_ts=to_timestamp,
            )
            address_to_swaps.update(address_to_swaps_)
            self._update_used_query_range(
                addresses=new_addresses,
                prefix='balancer_trades',
                from_timestamp=start_ts,
                to_timestamp=to_timestamp,
            )

        # Request existing DB addresses' trades
        if existing_addresses and to_timestamp > min_to_timestamp:
            address_to_swaps_ = self._get_address_to_swaps_graph(
                addresses=existing_addresses,
                start_ts=min_to_timestamp,
                end_ts=to_timestamp,
            )
            address_to_swaps.update(address_to_swaps_)
            self._update_used_query_range(
                addresses=existing_addresses,
                prefix='balancer_trades',
                from_timestamp=min_to_timestamp,
                to_timestamp=to_timestamp,
            )

        # Insert all swaps to the DB
        if address_to_swaps:
            all_swaps = [swap for a_swaps in address_to_swaps.values() for swap in a_swaps]
            self.database.add_amm_swaps(all_swaps)

        return self._fetch_trades_from_db(
            addresses=addresses,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )

    def _get_balancer_aggregated_events_data(
            self,
            address_to_events_data: AddressToEventsData,
    ) -> List[BalancerEvent]:
        """Get a structure that contains all the new pools and events to be
        stored in the DB.

        May raise RemoteError
        """
        balancer_pools: List[EthereumToken] = []
        balancer_events: List[BalancerEvent] = []
        pool_addr_to_token_addr_to_index: PoolAddrToTokenAddrToIndex = {}
        # Create a map that allows getting the index of a token in the pool
        db_pools = GlobalDBHandler().get_ethereum_tokens(protocol='balancer')
        for db_pool in db_pools:
            token_addr_to_index = {
                pool_token.address: idx
                for idx, pool_token in enumerate(db_pool.underlying_tokens)
            }
            pool_addr_to_token_addr_to_index[db_pool] = token_addr_to_index

        for event_type in BalancerBPTEventType:
            self._get_balancer_aggregated_events_data_by_event_type(
                address_to_events_data=address_to_events_data,
                event_type=event_type,
                balancer_pools=balancer_pools,
                balancer_events=balancer_events,
                pool_addr_to_token_addr_to_index=pool_addr_to_token_addr_to_index,
            )
        return balancer_events

    def _get_balancer_aggregated_events_data_by_event_type(
            self,
            address_to_events_data: AddressToEventsData,
            event_type: Literal[BalancerBPTEventType.MINT, BalancerBPTEventType.BURN],
            balancer_pools: List[EthereumToken],
            balancer_events: List[BalancerEvent],
            pool_addr_to_token_addr_to_index: PoolAddrToTokenAddrToIndex,
    ) -> None:
        """Store pools and events in the DB

        The `event_type` (MINT or BURN) determines from which type of events the
        <BalancerEvent> is built:
        - MINT: aggregate 1 MINT <BalancerBPTEvent> and N ADD_LIQUIDITY <BalancerInvestEvent>.
        - BURN: aggregate 1 BURN <BalancerBPTEvent> and N REMOVE_LIQUIDITY <BalancerInvestEvent>.

        Criteria for aggregating events:
        - All the events must have the same user address, transaction and pool address.

        Criteria for calculating the event amounts:
        - `amounts` is a list initialized with as many zero items as tokens in the pool.
        - Each <BalancerInvestEvent>.amount is added to its respective `amounts`
        item.

        Criteria for calculating the LP (BPT) balance:
        - The `amount` comes from the MINT and BURN <BalancerBPTEvent>.amount
        and it is always accurate.
        - The `usd_value` is estimated by adding the USD value of all the
        <BalancerInvestEvent>.amount added or removed. It requires to request
        the USD price of the underlying pool token at a particular timestamp.
        - BE AWARE: if the USD price at a particular time can't be obtained
        (e.g. zero, the request failed), the LP USD value is set to zero.

        May raise RemoteError
        """
        # Set the BalancerEvents attributes to be accessed via getattr
        if event_type == BalancerBPTEventType.MINT:
            attr_invest_events = 'add_liquidities'
            attr_bpt_events = 'mints'
        elif event_type == BalancerBPTEventType.BURN:
            attr_invest_events = 'remove_liquidities'
            attr_bpt_events = 'burns'
        else:
            raise AssertionError(f'Unexpected event type: {event_type}.')

        for events in address_to_events_data.values():
            # Create a map that allows getting the invest events by (tx_hash, pool address)
            tx_hash_and_pool_addr_to_invest_events = defaultdict(list)
            for invest_event in getattr(events, attr_invest_events):  # noqa: E501
                key = (invest_event.tx_hash, invest_event.pool_address_token)
                tx_hash_and_pool_addr_to_invest_events[key].append(invest_event)

            # Create a <BalancerEvent> by aggregating invest and bpt events that happened
            # in the same transaction and for the same pool. Optionally create a
            # BalancerPool token if it does not exist in the DB.
            for bpt_event in getattr(events, attr_bpt_events):
                key = (bpt_event.tx_hash, bpt_event.pool_address_token)
                invest_events = tx_hash_and_pool_addr_to_invest_events[key]
                # NB: 1 <BalancerBPTEvent> requires at least 1 <BalancerInvestEvent>
                # Otherwise the subgraph is missing required data
                if len(invest_events) == 0:
                    log.error(
                        f'Failed to generate a balancer event. Missing {attr_invest_events} events for {event_type} event',  # noqa: E501
                        bpt_event=bpt_event,
                    )
                    raise RemoteError('Failed to deserialize balancer events')

                # If the pool is new, add it into the `pool_addr_to_token_addr_to_index` map
                # and create the BalancerPool token
                if bpt_event.pool_address_token not in pool_addr_to_token_addr_to_index:
                    token_addr_to_index = {
                        underlying_token.address: idx
                        for idx, underlying_token in enumerate(bpt_event.pool_address_token.underlying_tokens)  # noqa: E501
                    }
                    pool_addr_to_token_addr_to_index[bpt_event.pool_address_token] = token_addr_to_index  # noqa: E501
                    underlying_tokens = [
                        UnderlyingToken(
                            address=x.token.ethereum_address,
                            weight=x.weight / FVal(100),
                        ) for x in bpt_event.pool_tokens
                    ]
                    token_data = EthereumToken.initialize(
                        address=bpt_event.pool_address,
                        underlying_tokens=underlying_tokens,
                        protocol='balancer',
                    )
                    balancer_pool = add_ethereum_token_to_db(token_data)
                    balancer_pools.append(balancer_pool)

                # Aggregate the <BalancerInvestEvent> token amounts related with the
                # <BalancerBPTEvent> and create the <BalancerEvent>
                amounts = [AssetAmount(ZERO)] * len(bpt_event.pool_address_token.underlying_tokens)
                lp_balance = Balance(amount=bpt_event.amount)
                is_missing_token_price = False
                for invest_event in invest_events:
                    tokenaddr_to_index = pool_addr_to_token_addr_to_index[bpt_event.pool_address_token]  # noqa: E501
                    token_idx = tokenaddr_to_index[invest_event.token_address]
                    amounts[token_idx] += invest_event.amount
                    token = EthereumToken(invest_event.token_address)  # should exist at this point
                    if is_missing_token_price is False:
                        usd_price = self._get_token_price_at_timestamp_zero_if_error(
                            token=token,
                            timestamp=invest_event.timestamp,
                        )
                        lp_balance.usd_value += usd_price * invest_event.amount
                        if usd_price == ZERO:
                            is_missing_token_price = True
                            self.msg_aggregator.add_error(
                                f"Failed to request the USD price of {token.identifier} at "
                                f"timestamp {invest_event.timestamp}. The USD price of the "
                                f"Balancer {event_type} for the pool {bpt_event.pool_address} "
                                f"at transaction {bpt_event.tx_hash} can't be calculated and "
                                f"it will be set to zero.",
                            )
                if is_missing_token_price is True:
                    lp_balance.usd_value = ZERO

                balancer_event = BalancerEvent(
                    tx_hash=bpt_event.tx_hash,
                    log_index=bpt_event.log_index,
                    address=bpt_event.address,
                    timestamp=invest_events[0].timestamp,
                    event_type=event_type,
                    pool_address_token=bpt_event.pool_address_token,
                    lp_balance=lp_balance,
                    amounts=amounts,
                )
                balancer_events.append(balancer_event)

    def _get_known_token_to_prices(self, known_tokens: Set[EthereumToken]) -> TokenToPrices:
        """Get a mapping of known token addresses to USD price"""
        token_to_prices: TokenToPrices = {}
        for token in known_tokens:
            usd_price = Inquirer().find_usd_price(token)
            if usd_price == Price(ZERO):
                self.msg_aggregator.add_error(
                    f"Failed to request the USD price of {token.identifier}. "
                    f"Balances of the balancer pools that have this token won't be accurate.",
                )
                continue

            token_to_prices[token.ethereum_address] = usd_price
        return token_to_prices

    def _get_protocol_balance_graph(
            self,
            addresses: List[ChecksumEthAddress],
    ) -> ProtocolBalance:
        """Get a mapping of addresses to protocol balance.

        May raise RemoteError
        """
        known_tokens: Set[EthereumToken] = set()
        unknown_tokens: Set[EthereumToken] = set()
        addresses_lower = [address.lower() for address in addresses]
        querystr = format_query_indentation(POOLSHARES_QUERY.format())
        query_offset = 0
        param_types = {
            '$limit': 'Int!',
            '$offset': 'Int!',
            '$addresses': '[ID!]',
            '$balance': 'BigDecimal!',
        }
        param_values = {
            'limit': GRAPH_QUERY_LIMIT,
            'offset': query_offset,
            'addresses': addresses_lower,
            'balance': '0',
        }
        address_to_pool_balances: DDAddressToPoolBalances = defaultdict(list)
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

            try:
                raw_pool_shares = result['poolShares']
            except KeyError as e:
                log.error(
                    'Failed to deserialize balancer balances',
                    error='Missing key: poolShares',
                    result=result,
                    param_values=param_values,
                )
                raise RemoteError('Failed to deserialize balancer balances') from e

            for raw_pool_share in raw_pool_shares:
                try:
                    address, balancer_pool = deserialize_pool_share(self.database, raw_pool_share)
                    for pool_token in balancer_pool.pool_token.underlying_tokens:
                        token = EthereumToken(pool_token.address)  # should not raise
                        if token.has_oracle():
                            known_tokens.add(token)
                        else:
                            unknown_tokens.add(token)
                except DeserializationError as e:
                    log.error(
                        'Failed to deserialize a balancer pool balance',
                        error=str(e),
                        raw_pool_share=raw_pool_share,
                        param_values=param_values,
                    )
                    raise RemoteError('Failed to deserialize balancer balances') from e

                address_to_pool_balances[address].append(balancer_pool)

            if len(raw_pool_shares) < GRAPH_QUERY_LIMIT:
                break

            query_offset += GRAPH_QUERY_LIMIT
            param_values = {
                **param_values,
                'offset': query_offset,
            }

        protocol_balance = ProtocolBalance(
            address_to_pool_balances=dict(address_to_pool_balances),
            known_tokens=known_tokens,
            unknown_tokens=unknown_tokens,
        )
        return protocol_balance

    def _get_token_price_at_timestamp_zero_if_error(
            self,
            token: EthereumToken,
            timestamp: Timestamp,
    ) -> Price:
        if token.has_oracle():
            usd_price = query_usd_price_or_use_default(
                asset=token,
                time=timestamp,
                default_value=ZERO,
                location=str(Location.BALANCER),
            )
        else:
            token_to_prices = {}
            try:
                token_to_prices = self._get_unknown_token_to_prices_uniswap_graph(
                    unknown_token_addresses={token.ethereum_address},
                    timestamp=timestamp,
                )
            except RemoteError:
                # This error hiding is exclusive to the Balancer module. The Uniswap
                # module also calls tokenDayDatas and processes the results in the
                # same way, so in case of an error we should know.
                pass

            usd_price = token_to_prices.get(token.ethereum_address, Price(ZERO))

        return usd_price

    @staticmethod
    def _get_trades_from_swaps(swaps: List[AMMSwap]) -> List[AMMTrade]:
        """May raise DeserializationError"""
        assert len(swaps) != 0, "Swaps can't be an empty list"

        swaps.sort(key=lambda swap: (swap.timestamp, -swap.log_index), reverse=True)
        current_swaps: List[AMMSwap] = []
        trades: List[AMMTrade] = []
        last_tx_hash = swaps[0].tx_hash
        for swap in swaps:
            if swap.tx_hash != last_tx_hash:
                trades.extend(get_trades_from_tx_swaps(current_swaps))
                last_tx_hash = swap.tx_hash
                current_swaps = []

            current_swaps.append(swap)

        if len(current_swaps) != 0:
            trades.extend(get_trades_from_tx_swaps(current_swaps))

        return trades

    def _get_unknown_token_to_prices_balancer_graph(
            self,
            unknown_token_addresses: Set[ChecksumEthAddress],
    ) -> TokenToPrices:
        """Get a mapping of unknown token addresses to USD price via Balancer

        May raise RemoteError
        """
        unknown_token_addresses_lower = [address.lower() for address in unknown_token_addresses]
        querystr = format_query_indentation(TOKENPRICES_QUERY.format())
        query_offset = 0
        param_types = {
            '$limit': 'Int!',
            '$offset': 'Int!',
            '$token_ids': '[ID!]',
        }
        param_values = {
            'limit': GRAPH_QUERY_LIMIT,
            'offset': query_offset,
            'token_ids': unknown_token_addresses_lower,
        }
        token_to_prices: TokenToPrices = {}
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

            try:
                raw_token_prices = result['tokenPrices']
            except KeyError as e:
                log.error(
                    'Failed to deserialize balancer unknown token prices',
                    error='Missing key: tokenPrices',
                    result=result,
                    param_values=param_values,
                )
                raise RemoteError('Failed to deserialize balancer balances') from e

            for raw_token_price in raw_token_prices:
                try:
                    token_address, usd_price = deserialize_token_price(raw_token_price)
                except DeserializationError as e:
                    log.error(
                        'Failed to deserialize a balancer unknown token price',
                        error=str(e),
                        raw_token_price=raw_token_price,
                        param_values=param_values,
                    )
                    continue

                token_to_prices[token_address] = usd_price

            if len(raw_token_prices) < GRAPH_QUERY_LIMIT:
                break

            query_offset += GRAPH_QUERY_LIMIT
            param_values = {
                **param_values,
                'offset': query_offset,
            }

        return token_to_prices

    def _get_unknown_token_to_prices_graph(
            self,
            unknown_tokens: Set[EthereumToken],
    ) -> TokenToPrices:
        """Get a mapping of unknown token addresses to USD price

        Attempts first to get the price via Balancer, otherwise via Uniswap

        May raise RemoteError
        """
        unknown_token_addresses = {token.ethereum_address for token in unknown_tokens}
        token_to_prices_bal = self._get_unknown_token_to_prices_balancer_graph(unknown_token_addresses)  # noqa: E501
        token_to_prices = dict(token_to_prices_bal)
        still_unknown_token_addresses = unknown_token_addresses - set(token_to_prices_bal.keys())
        if self.graph_uniswap is not None:
            # Requesting the missing prices from Uniswap is
            # a nice to have alternative to the main oracle (Balancer). Therefore
            # in case of failing to request, it will just continue.
            try:
                token_to_prices_uni = self._get_unknown_token_to_prices_uniswap_graph(still_unknown_token_addresses)  # noqa: E501
            except RemoteError:
                # This error hiding is exclusive to the Balancer module. The Uniswap
                # module also calls tokenDayDatas and processes the results in the
                # same way, so in case of an error we should know.
                token_to_prices_uni = {}

            token_to_prices = {**token_to_prices, **token_to_prices_uni}

        for unknown_token in unknown_tokens:
            if unknown_token.ethereum_address not in token_to_prices:
                self.msg_aggregator.add_error(
                    f"Failed to request the USD price of {unknown_token.identifier}. "
                    f"Balances of the balancer pools that have this token won't be accurate.",
                )
        return token_to_prices

    def _get_unknown_token_to_prices_uniswap_graph(
            self,
            unknown_token_addresses: Set[ChecksumEthAddress],
            timestamp: Optional[Timestamp] = None,
    ) -> TokenToPrices:
        """Get a mapping of unknown token addresses to USD price via Uniswap

        May raise RemoteError
        """
        unknown_token_addresses_lower = [address.lower() for address in unknown_token_addresses]
        querystr = format_query_indentation(TOKEN_DAY_DATAS_QUERY.format())
        from_timestamp = ts_now() if timestamp is None else timestamp
        midnight_epoch = int(
            datetime.datetime.combine(
                datetime.datetime.fromtimestamp(from_timestamp),
                datetime.time.min,
            ).timestamp(),
        )
        query_offset = 0
        param_types = {
            '$limit': 'Int!',
            '$offset': 'Int!',
            '$token_ids': '[String!]',
            '$datetime': 'Int!',
        }
        param_values = {
            'limit': GRAPH_QUERY_LIMIT,
            'offset': query_offset,
            'token_ids': unknown_token_addresses_lower,
            'datetime': midnight_epoch,
        }
        token_to_prices: TokenToPrices = {}
        while True:
            try:
                result = self.graph_uniswap.query(  # type: ignore # caller already checks
                    querystr=querystr,
                    param_types=param_types,
                    param_values=param_values,
                )
            except RemoteError as e:
                self.msg_aggregator.add_error(UNISWAP_REMOTE_ERROR_MSG.format(error_msg=str(e)))
                raise

            try:
                raw_token_day_datas = result['tokenDayDatas']
            except KeyError as e:
                log.error(
                    'Failed to deserialize balancer unknown token day datas',
                    error='Missing key: tokenDayDatas',
                    result=result,
                    param_values=param_values,
                )
                raise RemoteError('Failed to deserialize balancer balances') from e

            for raw_token_day_data in raw_token_day_datas:
                try:
                    token_address, usd_price = deserialize_token_day_data(raw_token_day_data)
                except DeserializationError as e:
                    log.error(
                        'Failed to deserialize a balancer unknown token day data',
                        error=str(e),
                        raw_token_day_data=raw_token_day_data,
                        param_values=param_values,
                    )
                    continue

                token_to_prices[token_address] = usd_price

            if len(raw_token_day_datas) < GRAPH_QUERY_LIMIT:
                break

            query_offset += GRAPH_QUERY_LIMIT
            param_values = {
                **param_values,
                'offset': query_offset,
            }

        return token_to_prices

    @staticmethod
    def _update_tokens_prices_in_address_to_pool_balances(
            address_to_pool_balances: AddressToPoolBalances,
            known_token_to_prices: TokenToPrices,
            unknown_token_to_prices: TokenToPrices,
    ) -> None:
        """Update the prices (in USD) of the underlying pool tokens"""
        for balancer_pool_balances in address_to_pool_balances.values():
            for pool_balance in balancer_pool_balances:
                total_usd_value = ZERO
                for pool_token_balance in pool_balance.underlying_tokens_balance:
                    token_ethereum_address = pool_token_balance.token.ethereum_address
                    usd_price = known_token_to_prices.get(
                        token_ethereum_address,
                        unknown_token_to_prices.get(token_ethereum_address, Price(ZERO)),
                    )
                    if usd_price != Price(ZERO):
                        pool_token_balance.usd_price = usd_price
                        pool_token_balance.user_balance.usd_value = FVal(
                            pool_token_balance.user_balance.amount * usd_price,
                        )
                    total_usd_value += pool_token_balance.user_balance.usd_value
                pool_balance.user_balance.usd_value = total_usd_value

    def _update_used_query_range(
            self,
            addresses: List[ChecksumEthAddress],
            prefix: Literal['balancer_events', 'balancer_trades'],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> None:
        for address in addresses:
            entry_name = f'{prefix}_{address}'
            self.database.update_used_query_range(
                name=entry_name,
                start_ts=from_timestamp,
                end_ts=to_timestamp,
            )

    def get_balances(
        self,
        addresses: List[ChecksumEthAddress],
    ) -> AddressToPoolBalances:
        """Get the balances of the given addresses in any Balancer pool

        May raise RemoteError
        """
        protocol_balance = self._get_protocol_balance_graph(addresses)
        known_tokens = protocol_balance.known_tokens
        unknown_tokens = protocol_balance.unknown_tokens
        known_token_to_prices = self._get_known_token_to_prices(known_tokens)
        unknown_token_to_prices = self._get_unknown_token_to_prices_graph(unknown_tokens)
        self._update_tokens_prices_in_address_to_pool_balances(
            address_to_pool_balances=protocol_balance.address_to_pool_balances,
            known_token_to_prices=known_token_to_prices,
            unknown_token_to_prices=unknown_token_to_prices,
        )
        return protocol_balance.address_to_pool_balances

    def get_events_history(
        self,
        addresses: List[ChecksumEthAddress],
        reset_db_data: bool,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> AddressToPoolEventsBalances:
        """Get the events history of the given addresses

        May raise RemoteError
        """
        with self.trades_lock:
            if reset_db_data is True:
                self.database.delete_balancer_events_data()

            address_to_pool_events_balances = self._get_address_to_pool_events_balances(
                addresses=addresses,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
            )

        return address_to_pool_events_balances

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
            address_to_trades = self._get_address_to_trades(
                addresses=addresses,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                only_cache=only_cache,
            )
            for _, trades in address_to_trades.items():
                all_trades.extend(trades)

            return all_trades

    def get_trades_history(
        self,
        addresses: List[ChecksumEthAddress],
        reset_db_data: bool,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> AddressToTrades:
        """Get the trades history of the given addresses

        May raise RemoteError
        """
        with self.trades_lock:
            if reset_db_data is True:
                self.database.delete_balancer_trades_data()

            address_to_trades = self._get_address_to_trades(
                addresses=addresses,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                only_cache=False,
            )

        return address_to_trades

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> Optional[List['AssetBalance']]:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass

    def deactivate(self) -> None:
        self.database.delete_balancer_events_data()
        self.database.delete_balancer_trades_data()
