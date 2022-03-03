import logging
from typing import TYPE_CHECKING, Optional

from web3.types import BlockIdentifier

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.constants.assets import A_ETH, A_WETH
from rotkehlchen.constants.ethereum import SADDLE_ALETH_POOL
from rotkehlchen.errors import PriceQueryUnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Price, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SaddleOracle:
    """
    Provides logic to use saddle as oracle for certain assets
    """
    def __init__(self, eth_manager: 'EthereumManager'):
        self.eth_manager = eth_manager

    def rate_limited_in_last(  # pylint: disable=no-self-use
            self,
            seconds: Optional[int] = None,  # pylint: disable=unused-argument
    ) -> bool:
        return False  # noop for saddle

    def can_query_history(  # pylint: disable=no-self-use
        self,
        from_asset: Asset,  # pylint: disable=unused-argument
        to_asset: Asset,  # pylint: disable=unused-argument
        timestamp: Timestamp,  # pylint: disable=unused-argument
        seconds: Optional[int] = None,  # pylint: disable=unused-argument
    ) -> bool:
        return False  # noop for uniswap oracles atm

    def get_price(
        self,
        from_asset: Asset,
        to_asset: Asset,
        block_identifier: BlockIdentifier,
    ) -> Price:
        log.debug(f'Querying saddle for price of {from_asset} to {to_asset}')
        aleth = EthereumToken('0x0100546F2cD4C9D97f798fFC9755E47865FF7Ee6')
        if from_asset != aleth:
            raise PriceQueryUnsupportedAsset(
                f'{from_asset} is not a valid asset for the Saddle oracle',
            )

        aleth_eth_price = SADDLE_ALETH_POOL.call(
            ethereum=self.eth_manager,
            method_name='calculateSwap',
            arguments=[1, 0, 1000000000000000000],
            block_identifier=block_identifier,
        )
        aleth_eth_price /= FVal(1e18)
        if to_asset not in (A_WETH, A_ETH):
            eth_price = Inquirer().find_price(A_ETH, to_asset)
            return aleth_eth_price * eth_price

        return aleth_eth_price

    def query_current_price(self, from_asset: Asset, to_asset: Asset) -> Price:
        return self.get_price(
            from_asset=from_asset,
            to_asset=to_asset,
            block_identifier='latest',
        )
