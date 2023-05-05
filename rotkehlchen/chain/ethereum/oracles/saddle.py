import logging
from typing import TYPE_CHECKING, Optional

from web3.types import BlockIdentifier

from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ALETH, A_ETH, A_WETH
from rotkehlchen.constants.misc import EXP18
from rotkehlchen.errors.price import PriceQueryUnsupportedAsset
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.interfaces import CurrentPriceOracleInterface
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Price

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SaddleOracle(CurrentPriceOracleInterface):
    """
    Provides logic to use saddle as oracle for certain assets
    """
    def __init__(self, ethereum_inquirer: 'EthereumInquirer'):
        super().__init__(oracle_name='saddle')
        self.ethereum = ethereum_inquirer

    def rate_limited_in_last(
            self,
            seconds: Optional[int] = None,  # pylint: disable=unused-argument
    ) -> bool:
        return False

    def get_price(
            self,
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
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

        saddle_aleth_pool = self.ethereum.contracts.contract(string_to_evm_address('0xa6018520EAACC06C30fF2e1B3ee2c7c22e64196a'))  # noqa: E501
        aleth_eth_price = saddle_aleth_pool.call(
            node_inquirer=self.ethereum,
            method_name='calculateSwap',
            arguments=[1, 0, 1000000000000000000],
            block_identifier=block_identifier,
        )
        aleth_eth_price /= EXP18
        if to_asset not in (A_WETH, A_ETH):
            eth_price = Inquirer().find_price(A_ETH, to_asset)
            return aleth_eth_price * eth_price

        return aleth_eth_price

    def query_current_price(
            self,
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
            match_main_currency: bool,
    ) -> tuple[Price, bool]:
        """At the moment until more pools get implemented this function is limited to ALETH
        Refer to the docstring of `get_price`.
        May raise:
        - PriceQueryUnsupportedAsset: If an asset not supported by saddle is used in the oracle
        Returns:
        1. The price of from_asset at the current timestamp
        for the current oracle
        2. False value, since it never tries to match main currency
        """
        price = self.get_price(
            from_asset=from_asset,
            to_asset=to_asset,
            block_identifier='latest',
        )
        return price, False
