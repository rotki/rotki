import logging
from collections import defaultdict
from typing import TYPE_CHECKING, List, Optional, Set

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.utils import get_or_create_ethereum_token
from rotkehlchen.chain.ethereum.graph import GRAPH_QUERY_LIMIT, Graph, format_query_indentation
from rotkehlchen.chain.ethereum.interfaces.ammswap import UNISWAP_TRADES_PREFIX
from rotkehlchen.chain.ethereum.interfaces.ammswap.ammswap import AMMSwapPlatform
from rotkehlchen.chain.ethereum.interfaces.ammswap.typing import (
    AddressEvents,
    AddressEventsBalances,
    AddressToLPBalances,
    AddressTrades,
    AssetToPrice,
    DDAddressEvents,
    EventType,
    ProtocolBalance,
)
from rotkehlchen.chain.ethereum.interfaces.ammswap.utils import SUBGRAPH_REMOTE_ERROR_MSG
from rotkehlchen.chain.ethereum.trades import AMMSwap, AMMTrade
from rotkehlchen.constants import ZERO
from rotkehlchen.errors import DeserializationError, ModuleInitializationFailure, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount_force_positive,
    deserialize_ethereum_address,
)
from rotkehlchen.typing import AssetAmount, ChecksumEthAddress, Location, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule

from .graph import V3_SWAPS_QUERY
from .utils import get_latest_lp_addresses, uniswap_lp_token_balances

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures import AssetBalance
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

UNISWAP_EVENTS_PREFIX = 'uniswap_events'


class Uniswap(AMMSwapPlatform, EthereumModule):
    """Uniswap integration module

    * Uniswap subgraph:
    https://github.com/Uniswap/uniswap-v2-subgraph
    https://github.com/croco-finance/uniswap-v3-subgraph
    """
    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: 'DBHandler',
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ) -> None:
        try:
            self.graph = Graph(
                'https://api.thegraph.com/subgraphs/name/benesjan/uniswap-v2',
            )
            self.graph_v3 = Graph(
                'https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3',
            )
        except RemoteError as e:
            self.msg_aggregator.add_error(
                SUBGRAPH_REMOTE_ERROR_MSG.format(
                    error_msg=str(e),
                    location=self.location,
                ),
            )
            raise ModuleInitializationFailure('Uniswap subgraph remote error') from e

        super().__init__(
            location=Location.UNISWAP,
            ethereum_manager=ethereum_manager,
            database=database,
            premium=premium,
            msg_aggregator=msg_aggregator,
            graph=self.graph,
        )

    def get_balances_chain(self, addresses: List[ChecksumEthAddress]) -> ProtocolBalance:
        """Get the addresses' pools data via chain queries."""
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

        self.database.add_amm_events(all_events)

        # Fetch all DB events within the time range
        for address in addresses:
            db_events = self.database.get_amm_events(
                events=[EventType.MINT_UNISWAP, EventType.BURN_UNISWAP],
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

        # Insert all unique swaps to the DB
        all_swaps = set()
        for address in filter(lambda address: address in address_amm_trades, addresses):
            for trade in address_amm_trades[address]:
                for swap in trade.swaps:
                    all_swaps.add(swap)

        self.database.add_amm_swaps(list(all_swaps))
        return self._fetch_trades_from_db(addresses, from_timestamp, to_timestamp)

    def _get_trades_graph_for_address(
            self,
            address: ChecksumEthAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AMMTrade]:
        trades = []
        try:
            trades.extend(self._read_subgraph_trades(address, start_ts, end_ts))
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
                self.msg_aggregator.add_error(
                    SUBGRAPH_REMOTE_ERROR_MSG.format(
                        error_msg=str(e),
                        location=self.location,
                    ),
                )
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

    def get_trades_history(
        self,
        addresses: List[ChecksumEthAddress],
        reset_db_data: bool,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> AddressTrades:
        """Get the addresses' trades history in the Uniswap protocol"""
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

    def delete_events_data(self) -> None:
        self.database.delete_uniswap_events_data()

    def deactivate(self) -> None:
        self.database.delete_uniswap_trades_data()
        self.database.delete_uniswap_events_data()

    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> Optional[List['AssetBalance']]:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass
