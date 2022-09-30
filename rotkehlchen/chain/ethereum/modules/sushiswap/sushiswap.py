import logging
from collections import defaultdict
from typing import TYPE_CHECKING, List, Optional

from rotkehlchen.chain.ethereum.graph import Graph
from rotkehlchen.chain.ethereum.interfaces.ammswap.ammswap import AMMSwapPlatform
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import (
    AddressEvents,
    AddressEventsBalances,
    AddressToLPBalances,
    AssetToPrice,
    DDAddressEvents,
    EventType,
)
from rotkehlchen.chain.ethereum.interfaces.ammswap.utils import SUBGRAPH_REMOTE_ERROR_MSG
from rotkehlchen.chain.ethereum.modules.sushiswap.constants import CPT_SUSHISWAP_V2
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
            self.msg_aggregator.add_error(
                SUBGRAPH_REMOTE_ERROR_MSG.format(
                    error_msg=str(e),
                    location=self.location,
                ),
            )
            raise ModuleInitializationFailure('Sushiswap subgraph remote error') from e

        super().__init__(
            location=Location.SUSHISWAP,
            ethereum_manager=ethereum_manager,
            database=database,
            premium=premium,
            msg_aggregator=msg_aggregator,
            graph=self.graph,
        )

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

        # Get addresses' last used query range for Sushiswap events
        for address in addresses:
            entry_name = f'{SUSHISWAP_EVENTS_PREFIX}_{address}'
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
                    write_cursor=write_cursor,
                    name=f'{SUSHISWAP_EVENTS_PREFIX}_{address}',
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
        addresses: List[ChecksumEvmAddress],
    ) -> AddressToLPBalances:
        """Get the addresses' balances in the Sushiswap protocol

        Premium users can request balances either via the Sushiswap subgraph or
        on-chain.
        """
        protocol_balance = self._get_balances_graph(addresses=addresses)

        self.add_lp_tokens_to_db(
            lp_balances_mappings=protocol_balance.address_balances,
            protocol=CPT_SUSHISWAP_V2,
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

    def delete_events_data(self, write_cursor: 'DBCursor') -> None:
        self.database.delete_sushiswap_events_data(write_cursor)

    def deactivate(self) -> None:
        with self.database.user_write() as cursor:
            self.database.delete_sushiswap_events_data(cursor)

    def on_account_addition(self, address: ChecksumEvmAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        pass
