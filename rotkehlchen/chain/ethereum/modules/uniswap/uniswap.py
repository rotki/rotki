import logging
from collections import defaultdict
from typing import TYPE_CHECKING, List, Optional, Set

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.graph import Graph
from rotkehlchen.chain.ethereum.interfaces.ammswap.ammswap import AMMSwapPlatform
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import (
    AddressEvents,
    AddressEventsBalances,
    AddressToLPBalances,
    AssetToPrice,
    DDAddressEvents,
    EventType,
    LiquidityPoolAsset,
    ProtocolBalance,
)
from rotkehlchen.chain.ethereum.interfaces.ammswap.utils import SUBGRAPH_REMOTE_ERROR_MSG
from rotkehlchen.chain.ethereum.modules.uniswap.constants import CPT_UNISWAP_V2
from rotkehlchen.chain.ethereum.modules.uniswap.utils import (
    get_latest_lp_addresses,
    uniswap_lp_token_balances,
)
from rotkehlchen.chain.ethereum.modules.uniswap.v3.types import (
    AddressToUniswapV3LPBalances,
    UniswapV3ProtocolBalance,
)
from rotkehlchen.chain.ethereum.modules.uniswap.v3.utils import (
    get_unknown_asset_price_chain,
    uniswap_v3_lp_token_balances,
    update_asset_price_in_uniswap_v3_lp_balances,
)
from rotkehlchen.errors.misc import ModuleInitializationFailure, RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import ChecksumEvmAddress, Location, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

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

    def get_balances_chain(self, addresses: List[ChecksumEvmAddress]) -> ProtocolBalance:
        """Get the addresses' pools data via chain queries."""
        known_tokens: Set[EvmToken] = set()
        unknown_tokens: Set[EvmToken] = set()
        lp_addresses = get_latest_lp_addresses(self.data_directory)

        address_mapping = {}
        for address in addresses:
            pool_balances = uniswap_lp_token_balances(
                userdb=self.database,
                address=address,
                ethereum=self.ethereum,
                lp_addresses=lp_addresses,
                known_tokens=known_tokens,
                unknown_tokens=unknown_tokens,
            )
            if len(pool_balances) != 0:
                address_mapping[address] = pool_balances

        protocol_balance = ProtocolBalance(
            address_balances=address_mapping,
            known_tokens=known_tokens,
            unknown_tokens=unknown_tokens,
        )
        return protocol_balance

    def get_v3_balances_chain(self, addresses: List[ChecksumEvmAddress]) -> UniswapV3ProtocolBalance:  # noqa: 501
        """Get the addresses' Uniswap V3 pools data via chain queries."""
        price_known_tokens: Set[EvmToken] = set()
        price_unknown_tokens: Set[EvmToken] = set()

        address_mapping = {}
        for address in addresses:
            pool_balances = uniswap_v3_lp_token_balances(
                userdb=self.database,
                address=address,
                msg_aggregator=self.msg_aggregator,
                ethereum=self.ethereum,
                price_known_tokens=price_known_tokens,
                price_unknown_tokens=price_unknown_tokens,
            )
            if len(pool_balances) != 0:
                address_mapping[address] = pool_balances

        protocol_balance = UniswapV3ProtocolBalance(
            address_balances=address_mapping,
            known_tokens=price_known_tokens,
            unknown_tokens=price_unknown_tokens,
        )
        return protocol_balance

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
        address_events_balances: AddressEventsBalances = {}
        address_events: DDAddressEvents = defaultdict(list)
        db_address_events: AddressEvents = {}
        new_addresses: List[ChecksumEvmAddress] = []
        existing_addresses: List[ChecksumEvmAddress] = []
        min_end_ts: Timestamp = to_timestamp

        # Get addresses' last used query range for Uniswap events
        for address in addresses:
            entry_name = f'{UNISWAP_EVENTS_PREFIX}_{address}'
            events_range = self.database.get_used_query_range(cursor=write_cursor, name=entry_name)

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
                    write_cursor=write_cursor,
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
                    write_cursor=write_cursor,
                    name=f'{UNISWAP_EVENTS_PREFIX}_{address}',
                    start_ts=min_end_ts,
                    end_ts=to_timestamp,
                )

        # Insert requested events in DB
        all_events = []
        for address in filter(lambda x: x in address_events, addresses):
            all_events.extend(address_events[address])

        self.database.add_amm_events(write_cursor, all_events)

        # Fetch all DB events within the time range
        for address in addresses:
            db_events = self.database.get_amm_events(
                cursor=write_cursor,
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

    def get_balances(
        self,
        addresses: List[ChecksumEvmAddress],
    ) -> AddressToLPBalances:
        """Get the addresses' balances in the Uniswap protocol

        Premium users can request balances either via the Uniswap subgraph or
        on-chain.
        """
        if self.premium:
            protocol_balance = self._get_balances_graph(addresses=addresses)
        else:
            protocol_balance = self.get_balances_chain(addresses)

        self.add_lp_tokens_to_db(
            lp_balances_mappings=protocol_balance.address_balances,
            protocol=CPT_UNISWAP_V2,
        )
        known_assets = protocol_balance.known_tokens
        unknown_assets = protocol_balance.unknown_tokens

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

    def get_v3_balances(
            self,
            addresses: List[ChecksumEvmAddress],
    ) -> AddressToUniswapV3LPBalances:
        """Get the addresses' balances in the Uniswap V3 protocol."""
        protocol_balance = self.get_v3_balances_chain(addresses)
        known_assets = protocol_balance.known_tokens
        unknown_assets = protocol_balance.unknown_tokens
        known_asset_price = self._get_known_asset_price(
            known_assets=known_assets,
            unknown_assets=unknown_assets,
        )

        unknown_asset_price: AssetToPrice = {}
        unknown_asset_price = get_unknown_asset_price_chain(
            ethereum=self.ethereum,
            unknown_tokens=unknown_assets,
        )

        update_asset_price_in_uniswap_v3_lp_balances(
            address_balances=protocol_balance.address_balances,
            known_asset_price=known_asset_price,
            unknown_asset_price=unknown_asset_price,
        )
        return self._update_v3_balances_for_premium(
            address_balances=protocol_balance.address_balances,
        )

    def _update_v3_balances_for_premium(
            self,
            address_balances: AddressToUniswapV3LPBalances,
    ) -> AddressToUniswapV3LPBalances:
        """Update the Uniswap V3 LP positions to remove certain fields depending
        on the premium status of the user.
        """
        if not self.premium:
            for lps in address_balances.values():
                for lp in lps:
                    lp.total_supply = None
                    lp.assets = [
                        LiquidityPoolAsset(token=lp_asset.token, total_amount=None, user_balance=Balance())  # noqa: E501
                        for lp_asset in lp.assets
                    ]
        return address_balances

    def delete_events_data(self, write_cursor: 'DBCursor') -> None:
        self.database.delete_uniswap_events_data(write_cursor)

    def deactivate(self) -> None:
        with self.database.user_write() as cursor:
            self.database.delete_uniswap_events_data(cursor)

    def on_account_addition(self, address: ChecksumEvmAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        pass
