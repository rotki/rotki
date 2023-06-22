import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Optional

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.interfaces.ammswap.ammswap import AMMSwapPlatform
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import (
    UNISWAP_EVENTS_TYPES,
    AddressEvents,
    AddressEventsBalances,
    AddressToLPBalances,
    AssetToPrice,
    DDAddressEvents,
    LiquidityPoolAsset,
    ProtocolBalance,
)
from rotkehlchen.chain.ethereum.interfaces.ammswap.utils import update_asset_price_in_lp_balances
from rotkehlchen.chain.ethereum.modules.uniswap.constants import CPT_UNISWAP_V2
from rotkehlchen.chain.ethereum.modules.uniswap.utils import uniswap_lp_token_balances
from rotkehlchen.chain.ethereum.modules.uniswap.v3.types import (
    AddressToUniswapV3LPBalances,
    UniswapV3ProtocolBalance,
)
from rotkehlchen.chain.ethereum.modules.uniswap.v3.utils import (
    get_unknown_asset_price_chain,
    uniswap_v3_lp_token_balances,
    update_asset_price_in_uniswap_v3_lp_balances,
)
from rotkehlchen.constants.misc import ZERO, ZERO_PRICE
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import ChecksumEvmAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule

from .constants import CPT_UNISWAP_V1, UNISWAP_EVENTS_PREFIX

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.ethereum.manager import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Uniswap(AMMSwapPlatform, EthereumModule):
    """Uniswap integration module

    * Uniswap subgraph:
    https://github.com/Uniswap/uniswap-v2-subgraph
    https://github.com/croco-finance/uniswap-v3-subgraph
    """
    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            database: 'DBHandler',
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(
            counterparties=[CPT_UNISWAP_V1, CPT_UNISWAP_V2],
            ethereum_inquirer=ethereum_inquirer,
            database=database,
            premium=premium,
            msg_aggregator=msg_aggregator,
        )

    def get_balances_chain(self, addresses: list[ChecksumEvmAddress]) -> AddressToLPBalances:
        """Get the addresses' pools data via chain queries"""
        addresses_to_lps = self.get_lp_addresses(addresses=addresses)
        address_mapping = {}
        for address, lps in addresses_to_lps.items():
            token_addresses = [token.resolve_to_evm_token().evm_address for token in lps]
            pool_balances = uniswap_lp_token_balances(
                userdb=self.database,
                address=address,
                ethereum=self.ethereum,
                lp_addresses=token_addresses,
            )
            if len(pool_balances) != 0:
                address_mapping[address] = pool_balances
        return address_mapping

    def get_v3_balances_chain(self, addresses: list[ChecksumEvmAddress]) -> UniswapV3ProtocolBalance:  # noqa: 501
        """Get the addresses' Uniswap V3 pools data via chain queries."""
        price_known_tokens: set[EvmToken] = set()
        price_unknown_tokens: set[EvmToken] = set()

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

    def get_events_balances(
            self,
            addresses: list[ChecksumEvmAddress],
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
        new_addresses: list[ChecksumEvmAddress] = []
        existing_addresses: list[ChecksumEvmAddress] = []
        min_end_ts: Timestamp = to_timestamp 

        # Insert requested events in DB
        all_events = []
        for address in filter(lambda x: x in address_events, addresses):
            all_events.extend(address_events[address])
        with self.database.user_write() as write_cursor:
            self.database.add_amm_events(write_cursor, all_events)

        with self.database.conn.read_ctx() as cursor:
            # Fetch all DB events within the time range
            for address in addresses:
                db_events = self.database.get_amm_events(
                    cursor=cursor,
                    events=UNISWAP_EVENTS_TYPES,
                    from_ts=from_timestamp,
                    to_ts=to_timestamp,
                    address=address,
                )
                if db_events:
                    db_address_events[address] = db_events

        # Request addresses' current balances (UNI-V2s and underlying tokens)
        # if there is no specific time range in this endpoint call (i.e. all
        # events). Current balances in the protocol are needed for an accurate
        # profit/loss calculation.
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
    
    def _update_asset_price_in_lp_balances(self, address_balances: AddressToLPBalances) -> None:
        """Utility function to update the pools underlying assets prices in USD
        (prices obtained via Inquirer and the subgraph) used by all AMM platforms.
        """
        for lps in address_balances.values():
            for lp in lps:
                # Try to get price from either known or unknown asset price.
                # Otherwise keep existing price (zero)
                total_user_balance = ZERO
                for asset in lp.assets:
                    asset_usd_price = Inquirer().find_usd_price(asset.token)
                    # Update <LiquidityPoolAsset> if asset USD price exists
                    if asset_usd_price != ZERO_PRICE:
                        asset.usd_price = asset_usd_price
                        asset.user_balance.usd_value = FVal(
                            asset.user_balance.amount * asset_usd_price,
                        )

                    total_user_balance += asset.user_balance.usd_value

                # Update <LiquidityPool> total balance in USD
                lp.user_balance.usd_value = total_user_balance

    def get_balances(self, addresses: list[ChecksumEvmAddress]) -> AddressToLPBalances:
        """Get the addresses' balances in the Uniswap protocol"""
        protocol_balance = self.get_balances_chain(addresses)
        self._update_asset_price_in_lp_balances(protocol_balance)
        return protocol_balance

    def get_v3_balances(
            self,
            addresses: list[ChecksumEvmAddress],
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

    def deactivate(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEvmAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        pass
