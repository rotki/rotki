import logging
from typing import TYPE_CHECKING, Optional

from web3.types import BlockIdentifier

from rotkehlchen.assets.asset import Asset, CryptoAsset
from rotkehlchen.constants.assets import A_ALETH, A_ETH, A_WETH
from rotkehlchen.constants.ethereum import SADDLE_ALETH_POOL
from rotkehlchen.constants.misc import EXP18
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.price import PriceQueryUnsupportedAsset
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.interfaces import CurrentPriceOracleInterface
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Price

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SaddleOracle(CurrentPriceOracleInterface):
    """
    Provides logic to use saddle as oracle for certain assets
    """
    def __init__(self, eth_manager: 'EthereumManager'):
        super().__init__(oracle_name='saddle')
        self.eth_manager = eth_manager

    def rate_limited_in_last(
            self,
            seconds: Optional[int] = None,  # pylint: disable=unused-argument
    ) -> bool:
        return False

    def get_price(
        self,
        from_asset: CryptoAsset,
        to_asset: CryptoAsset,
        block_identifier: BlockIdentifier,
    ) -> Price:
        """
        NOTE: This function is limited to be used for ALETH at the moment.
        The reason for that is how pools for saddle are engineered and the lack
        of an automated way to get the pools. ALETH was chosen because this is
        the only place where its price can be queried.
        What the code does is querying the pool for the swap ALETH -> ETH
        and then get the eth price to calculate the ALETH price
        """
        log.debug(f'Querying saddle for price of {from_asset} to {to_asset}')
        if from_asset != A_ALETH:
            raise PriceQueryUnsupportedAsset(
                f'{from_asset} is not a valid asset for the Saddle oracle',
            )

        aleth_eth_price = SADDLE_ALETH_POOL.call(
            manager=self.eth_manager,
            method_name='calculateSwap',
            arguments=[1, 0, 1000000000000000000],
            block_identifier=block_identifier,
        )
        aleth_eth_price /= EXP18
        if to_asset not in (A_WETH, A_ETH):
            eth_price = Inquirer().find_price(A_ETH, to_asset)
            return aleth_eth_price * eth_price

        return aleth_eth_price

    def query_current_price(self, from_asset: Asset, to_asset: Asset) -> Price:
        """At the moment until more pools get implemented this function is limited to ALETH
        Refer to the docstring of `get_price`.
        """
        try:
            return self.get_price(
                from_asset=from_asset.resolve_to_crypto_asset(),
                to_asset=to_asset.resolve_to_crypto_asset(),
                block_identifier='latest',
            )
        except UnknownAsset as e:
            # Means that either from_asset or to_asset is not a crypto asset
            raise PriceQueryUnsupportedAsset(e.asset_name) from e
