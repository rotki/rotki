import logging
from typing import TYPE_CHECKING, Optional

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.interfaces.ammswap.ammswap import AMMSwapPlatform
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import AssetToPrice, LiquidityPoolAsset
from rotkehlchen.chain.ethereum.modules.uniswap.constants import CPT_UNISWAP_V2
from rotkehlchen.chain.ethereum.modules.uniswap.v3.types import (
    AddressToUniswapV3LPBalances,
    UniswapV3ProtocolBalance,
)
from rotkehlchen.chain.ethereum.modules.uniswap.v3.utils import (
    get_unknown_asset_price_chain,
    uniswap_v3_lp_token_balances,
    update_asset_price_in_uniswap_v3_lp_balances,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule

from .constants import CPT_UNISWAP_V1

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.ethereum.manager import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler

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
            counterparties=[CPT_UNISWAP_V1, CPT_UNISWAP_V2],  # counterparties for ammswapinterface. uniswap v3 doesn't follow it.  # noqa: E501
            ethereum_inquirer=ethereum_inquirer,
            database=database,
            premium=premium,
            msg_aggregator=msg_aggregator,
        )

    def get_v3_balances_chain(self, addresses: list[ChecksumEvmAddress]) -> UniswapV3ProtocolBalance:  # noqa: E501
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
