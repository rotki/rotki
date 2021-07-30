import logging
from collections import defaultdict
from typing import TYPE_CHECKING, List, Optional, Set

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.utils import get_or_create_ethereum_token
from rotkehlchen.chain.ethereum.graph import GRAPH_QUERY_LIMIT, Graph, format_query_indentation
from rotkehlchen.chain.ethereum.interfaces.ammswap.ammswap import AMMSwapPlatform
from rotkehlchen.chain.ethereum.interfaces.ammswap.typing import (
    AddressEvents,
    AddressEventsBalances,
    AddressToLPBalances,
    AddressTrades,
    AssetToPrice,
    DDAddressEvents,
    DDAddressToLPBalances,
    EventType,
    LiquidityPool,
    LiquidityPoolAsset,
    ProtocolBalance,
)
from rotkehlchen.chain.ethereum.interfaces.ammswap.utils import SUBGRAPH_REMOTE_ERROR_MSG
from rotkehlchen.chain.ethereum.trades import AMMTrade
from rotkehlchen.errors import DeserializationError, ModuleInitializationFailure, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.premium.premium import Premium
from rotkehlchen.serialization.deserialize import deserialize_ethereum_address
from rotkehlchen.typing import (
    ChecksumEthAddress,
    Location,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule

from .graph import LIQUIDITY_POSITIONS_QUERY

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures import AssetBalance
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler

log = logging.getLogger(__name__)

SUSHISWAP_EVENTS_PREFIX = 'sushiswap_events'


class Sushiswap(AMMSwapPlatform, EthereumModule):
    """Sushiswap integration module

    * Sushiswap subgraph:
    https://github.com/sushiswap/sushiswap-subgraph
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
                'https://api.thegraph.com/subgraphs/name/sushiswap/exchange',
            )
        except RemoteError as e:
            self.msg_aggregator.add_error(SUBGRAPH_REMOTE_ERROR_MSG.format(error_msg=str(e)))
            raise ModuleInitializationFailure('Sushiswap subgraph remote error') from e

        super().__init__(
            location=Location.SUSHISWAP,
            ethereum_manager=ethereum_manager,
            database=database,
            premium=premium,
            msg_aggregator=msg_aggregator,
            graph=self.graph,
        )

    def _get_balances_graph(
            self,
            addresses: List[ChecksumEthAddress],
    ) -> ProtocolBalance:
        """Get the addresses' pools data querying the Sushiswap subgraph

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
                        f'Failed to Deserialize address. Skipping pool {lp_pair} '
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
                            f'Failed to deserialize token address {token["id"]} '
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

        # Get addresses' last used query range for Sushiswap events
        for address in addresses:
            entry_name = f'{SUSHISWAP_EVENTS_PREFIX}_{address}'
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
                    name=f'{SUSHISWAP_EVENTS_PREFIX}_{address}',
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
                    name=f'{SUSHISWAP_EVENTS_PREFIX}_{address}',
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
                events=[EventType.MINT_SUSHISWAP, EventType.BURN_SUSHISWAP],
                from_ts=from_timestamp,
                to_ts=to_timestamp,
                address=address,
            )
            if db_events:
                # return events with the oldest first
                db_events.sort(key=lambda event: (event.timestamp, event.log_index))
                db_address_events[address] = db_events

        # Request addresses' current balances (LP and underlying tokens)
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

    def get_balances(
        self,
        addresses: List[ChecksumEthAddress],
    ) -> AddressToLPBalances:
        """Get the addresses' balances in the Sushiswap protocol

        Premium users can request balances either via the Sushiswap subgraph or
        on-chain.
        """
        protocol_balance = self._get_balances_graph(addresses=addresses)

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
        """Get the addresses' trades history in the Sushiswap protocol
        """
        with self.trades_lock:
            if reset_db_data is True:
                self.database.delete_sushiswap_trades_data()

            trades = self._get_trades(
                addresses=addresses,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                only_cache=False,
            )
        return trades

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
                f'Error querying sushiswap trades using graph for address {address} '
                f'between {start_ts} and {end_ts}. {str(e)}',
            )

        return trades

    def delete_trade_events(self) -> None:
        self.database.delete_sushiswap_trades_data()

    def deactivate(self) -> None:
        self.database.delete_sushiswap_trades_data()
        self.database.delete_sushiswap_events_data()

    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> Optional[List['AssetBalance']]:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass
