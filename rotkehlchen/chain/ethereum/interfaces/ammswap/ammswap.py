"""
Implements an interface for ethereum modules that are AMM with support for subgraphs
implementing functionalities similar to the Uniswap one.

This interface is used at the moment in:

- Uniswap Module
- Sushiswap Module
"""
import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import (
    AddressToLPBalances,
    AssetToPrice,
)
from rotkehlchen.chain.ethereum.modules.uniswap.utils import uniswap_lp_token_balances
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


UNISWAP_TRADES_PREFIX = 'uniswap_trades'
SUSHISWAP_TRADES_PREFIX = 'sushiswap_trades'


class AMMSwapPlatform:
    """
    AMM Module interface
    This class uses decoded events from protocols following the Uniswap design to query balances.
    The counterparties provided are the ones used to filter the history events for querying the
    pools with balances and the mint/burn events. For example CPT_SUSHISWAP
    """
    def __init__(
            self,
            counterparties: list[str],
            ethereum_inquirer: 'EthereumInquirer',
            database: 'DBHandler',
            premium: Premium | None,
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        self.counterparties = counterparties
        self.ethereum = ethereum_inquirer
        self.database = database
        self.premium = premium
        self.msg_aggregator = msg_aggregator
        self.data_directory = database.user_data_dir.parent

    @staticmethod
    def _get_known_asset_price(
            known_assets: set[EvmToken],
            unknown_assets: set[EvmToken],
    ) -> AssetToPrice:
        """Get the tokens prices via Inquirer

        Given an asset, if `find_usd_price()` returns zero, it will be added
        into `unknown_assets`.
        """
        asset_price: AssetToPrice = {}

        for known_asset in known_assets:
            asset_usd_price = Inquirer.find_usd_price(known_asset)

            if asset_usd_price != ZERO_PRICE:
                asset_price[known_asset.evm_address] = asset_usd_price
            else:
                unknown_assets.add(known_asset)

        return asset_price

    def _get_lp_addresses(
            self,
            addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, set[Asset]]:
        """Query all LP tokens that the given users have ever gotten as a result of depositing"""
        db_filter = EvmEventFilterQuery.make(
            counterparties=self.counterparties,
            location_labels=addresses,  # type: ignore[arg-type]
            event_subtypes=[
                HistoryEventSubType.RECEIVE_WRAPPED,
            ],
        )
        query, bindings = db_filter.prepare()
        address_to_pools = defaultdict(set)
        with self.database.conn.read_ctx() as cursor:
            cursor.execute('SELECT location_label, asset FROM history_events JOIN chain_events_info ON history_events.identifier = chain_events_info.identifier ' + query, bindings)  # noqa: E501
            for address, lp_token in cursor:
                address_to_pools[string_to_evm_address(address)].add(Asset(lp_token))

        return address_to_pools

    def get_balances_chain(self, addresses: list[ChecksumEvmAddress]) -> AddressToLPBalances:
        """Get the addresses' pools data via chain queries"""
        addresses_to_lps = self._get_lp_addresses(addresses=addresses)
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

    def _update_asset_price_in_lp_balances(self, address_balances: AddressToLPBalances) -> None:
        """Utility function to update the pools underlying assets prices in USD
        (prices obtained via Inquirer) used by all AMM platforms.
        """
        with self.database.conn.read_ctx() as cursor:
            main_currency = self.database.get_setting(cursor=cursor, name='main_currency')

        for lps in address_balances.values():
            for lp in lps:
                # Try to get price from either known or unknown asset price.
                # Otherwise keep existing price (zero)
                total_user_balance = ZERO
                for asset in lp.assets:
                    # Update <LiquidityPoolAsset> if asset price exists in main currency
                    if (asset_main_currency_price := Inquirer.find_price(
                        from_asset=asset.token,
                        to_asset=main_currency,
                    )) != ZERO_PRICE:
                        asset.user_balance.value = FVal(asset.user_balance.amount * asset_main_currency_price)  # noqa: E501

                    total_user_balance += asset.user_balance.value

                # Update <LiquidityPool> total balance in main currency
                lp.user_balance.value = total_user_balance

    def get_balances(self, addresses: list[ChecksumEvmAddress]) -> AddressToLPBalances:
        """Get the given addresses' balances in the current protocol"""
        protocol_balance = self.get_balances_chain(addresses)
        self._update_asset_price_in_lp_balances(protocol_balance)
        return protocol_balance
