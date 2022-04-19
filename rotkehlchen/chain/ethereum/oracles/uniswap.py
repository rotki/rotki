import abc
import logging
from functools import reduce
from multiprocessing import Pool
from operator import mul
from typing import TYPE_CHECKING, List, NamedTuple, Tuple, Union

from eth_utils import to_checksum_address
from web3.types import BlockIdentifier

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.contracts import EthereumContract
from rotkehlchen.chain.ethereum.utils import multicall, multicall_specific
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_USDT, A_WETH, A_USDC, A_USD
from rotkehlchen.constants.ethereum import (
    UNISWAP_V2_FACTORY,
    UNISWAP_V2_LP_ABI,
    UNISWAP_V3_FACTORY,
    UNISWAP_V3_POOL_ABI,
    ZERO_ADDRESS,
)
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.errors import PriceQueryUnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.interfaces import CurrentPriceOracleInterface
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEthAddress, Price

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class PoolPrice(NamedTuple):
    price: FVal
    token_0: EthereumToken
    token_1: EthereumToken

    def swap_tokens(self) -> 'PoolPrice':
        return PoolPrice(
            price = 1 / self.price,
            token_0 = self.token_1,
            token_1 = self.token_0,
        )


class UniswapOracle(CurrentPriceOracleInterface):
    """
    Provides shared logic between Uniswap V2 and Uniswap V3 to use them as price oracles.
    """
    def __init__(self, eth_manager: 'EthereumManager'):
        self.eth_manager = eth_manager
        self.routing_assets = [
            A_WETH,
            A_DAI,
            A_USDT,
        ]

    @abc.abstractmethod
    def get_pool(
        self,
        token_0: EthereumToken,
        token_1: EthereumToken,
    ) -> List[str]:
        """Given two tokens returns a list of pools where they can be swapped"""
        ...

    @abc.abstractmethod
    def get_pool_price(
        self,
        pool_addr: ChecksumEthAddress,
        block_identifier: BlockIdentifier = 'latest',
    ) -> PoolPrice:
        """Returns the price for the tokens in the given pool and the token0 and
        token1 of the pool
        """
        ...

    def _find_pool_for(self, asset, link_asset, path: List[str]) -> bool:
        pools = self.get_pool(asset, link_asset)
        for pool in pools:
            if pool != ZERO_ADDRESS:
                path.append(pool)
                return True

    def find_route(self, from_asset: EthereumToken, to_asset: EthereumToken) -> List[str]:
        """
        Calculate the path needed to go from from_asset to to_asset and return a
        list of the pools needed to jump through to do that.
        """
        output = []
        # If any of the assets is in the glue assets let's see if we find any path
        # (avoids iterating the list of glue assets)
        if any(x in self.routing_assets for x in (to_asset, from_asset)):
            output = []
            found_path = self._find_pool_for(
                asset=from_asset,
                link_asset=to_asset,
                path=output,
            )
            if found_path:
                return output

        if from_asset == to_asset:
            return []

        # Try to find one asset that can be used between from_asset and to_asset
        # from_asset < first link > glue asset < second link > to_asset
        link_asset = None
        found_first_link, found_second_link = False, False
        for asset in self.routing_assets:
            if asset != from_asset:
                found_first_link = self._find_pool_for(
                    asset=from_asset,
                    link_asset=asset,
                    path=output,
                )
                if found_first_link:
                    link_asset = asset
                    found_second_link = self._find_pool_for(
                        asset=to_asset,
                        link_asset=link_asset,
                        path=output,
                    )
                    if found_second_link:
                        return output

        if not found_first_link:
            return []

        # if we reach this point it means that we need 2 more jumps
        # from asset <1st link> glue asset A <2nd link> glue asset B <3rd link> to asset
        # find now the part for glue asset B <3rd link> to asset
        second_link_asset = None
        for asset in self.routing_assets:
            if asset != to_asset:
                found_second_link = self._find_pool_for(
                    asset=to_asset,
                    link_asset=asset,
                    path=output,
                )
                if found_second_link:
                    second_link_asset = asset
                    break

        if not found_second_link:
            return []

        # finally find the step of glue asset A <2nd link> glue asset B
        assert second_link_asset is not None
        assert link_asset is not None
        pools = self.get_pool(link_asset, second_link_asset)
        for pool in pools:
            if pool != ZERO_ADDRESS:
                output.insert(1, pool)
                return output

        return []

    def get_price(
        self,
        from_asset: Asset,
        to_asset: Asset,
        block_identifier: BlockIdentifier,
    ) -> Price:
        """
        Return the price of from_asset to to_asset at the block block_identifier.
        External oracles are used if non eth tokens are used.

        Can raise:
        - PriceQueryUnsupportedAsset
        - RemoteError
        """
        log.debug(
            f'Searching price for {from_asset} to {to_asset} at '
            f'{block_identifier!r} with {self.get_oracle_name()}'
        )

        # Use weth internally
        if from_asset == A_ETH:
            from_asset = A_WETH
        if to_asset == A_ETH:
            to_asset = A_WETH

        if from_asset == to_asset:
            return Price(ONE)

        if not (from_asset.is_eth_token() and to_asset.is_eth_token()):
            raise PriceQueryUnsupportedAsset(
                f'Neither {from_asset} nor {to_asset} are ethereum tokens for the uniswap oracle',
            )

        # Could be that we are dealing with ethereum tokens as intances of Asset instead of
        # EthereumToken, handle the conversion
        from_asset_raw: Union[Asset, EthereumToken] = from_asset
        to_asset_raw: Union[Asset, EthereumToken] = to_asset
        if not isinstance(from_asset, EthereumToken):
            from_as_token = EthereumToken.from_identifier(from_asset_raw.identifier)
            if from_as_token is None:
                raise PriceQueryUnsupportedAsset(f'Unsupported asset for uniswap {from_asset_raw}')
            from_asset = from_as_token
        if not isinstance(to_asset, EthereumToken):
            to_as_token = EthereumToken.from_identifier(to_asset_raw.identifier)
            if to_as_token is None:
                raise PriceQueryUnsupportedAsset(f'Unsupported asset for uniswap {to_asset_raw}')
            to_asset = to_as_token

        assert isinstance(from_asset, EthereumToken), f'Got non valid token {from_asset}'
        assert isinstance(to_asset, EthereumToken), f'Found non valid token {to_asset}'
        route = self.find_route(from_asset_raw, to_asset_raw)

        if len(route) == 0:
            log.debug(f'Failed to find price for {from_asset} to {to_asset}')
            return Price(ZERO)

        prices_and_tokens = []
        for step in route:
            prices_and_tokens.append(
                self.get_pool_price(
                    pool_addr=to_checksum_address(step),
                    block_identifier=block_identifier,
                ),
            )

        # Looking at which one is token0 and token1 we need to see if we need price or 1/price
        if prices_and_tokens[0].token_0 != from_asset:
            prices_and_tokens[0] = prices_and_tokens[0].swap_tokens()

        # For the possible intermediate steps also make sure that we use the correct price
        for pos, item in enumerate(prices_and_tokens[1:-1]):
            if item.token_0 != prices_and_tokens[pos - 1].token_1:
                prices_and_tokens[pos-1] = prices_and_tokens[pos-1].swap_tokens()

        # Finally for the tail query the price
        if prices_and_tokens[-1].token_1 != to_asset:
            prices_and_tokens[-1] = prices_and_tokens[-1].swap_tokens()

        price = FVal(reduce(mul, [item.price for item in prices_and_tokens], 1))
        return Price(price)

    def query_current_price(self, from_asset: Asset, to_asset: Asset) -> Price:
        if to_asset == A_USD:
            to_asset = A_USDC
        elif from_asset == A_USD:
            from_asset = A_USDC
        
        return self.get_price(
            from_asset=from_asset,
            to_asset=to_asset,
            block_identifier='latest',
        )


class UniswapV3Oracle(UniswapOracle):

    def get_oracle_name(self) -> str:
        return 'Uniswap V3 oracle'

    def get_pool(
        self,
        token_0: EthereumToken,
        token_1: EthereumToken,
    ) -> List[str]:
        result = multicall_specific(
            ethereum=self.eth_manager,
            contract=UNISWAP_V3_FACTORY,
            method_name='getPool',
            arguments=[[
                token_0.ethereum_address,
                token_1.ethereum_address,
                fee,
            ] for fee in (3000, 500, 10000)],
        )

        return [pool[0] for pool in result]

    def get_pool_price(
        self,
        pool_addr: ChecksumEthAddress,
        block_identifier: BlockIdentifier = 'latest',
    ) -> PoolPrice:
        """
        Returns the units of token1 that one token0 can buy
        """
        pool_contract = EthereumContract(
            address=pool_addr,
            abi=UNISWAP_V3_POOL_ABI,
            deployed_block=12369621,  # Factory deployment block
        )
        calls = [
            (
                pool_contract.address,
                pool_contract.encode(method_name='slot0'),
            ), (
                pool_contract.address,
                pool_contract.encode(method_name='token0'),
            ), (
                pool_contract.address,
                pool_contract.encode(method_name='token1'),
            ),
        ]
        output = multicall(
            ethereum=self.eth_manager,
            calls=calls,
            require_success=True,
            block_identifier=block_identifier,
        )
        token_0 = EthereumToken(
            to_checksum_address(pool_contract.decode(output[1], 'token0')[0]),  # noqa: E501 pylint:disable=unsubscriptable-object
        )
        token_1 = EthereumToken(
            to_checksum_address(pool_contract.decode(output[2], 'token1')[0]),  # noqa: E501 pylint:disable=unsubscriptable-object
        )
        sqrt_price_x96, _, _, _, _, _, _ = pool_contract.decode(output[0], 'slot0')
        decimals_constant = 10 ** (token_0.decimals - token_1.decimals)

        price = (sqrt_price_x96 * sqrt_price_x96) / 2 ** (192) * decimals_constant

        return PoolPrice(price=price, token_0=token_0, token_1=token_1)


class UniswapV2Oracle(UniswapOracle):

    def get_oracle_name(self) -> str:
        return 'Uniswap V2 oracle'

    def get_pool(
        self,
        token_0: EthereumToken,
        token_1: EthereumToken,
    ) -> List[str]:
        result = UNISWAP_V2_FACTORY.call(
            ethereum=self.eth_manager,
            method_name='getPair',
            arguments=[
                token_0.ethereum_address,
                token_1.ethereum_address,
            ],
        )
        return [result]

    def get_pool_price(
        self,
        pool_addr: ChecksumEthAddress,
        block_identifier: BlockIdentifier = 'latest',
    ) -> PoolPrice:
        """
        Returns the units of token1 that one token0 can buy
        """
        pool_contract = EthereumContract(
            address=pool_addr,
            abi=UNISWAP_V2_LP_ABI,
            deployed_block=10000835,  # Factory deployment block
        )
        calls = [
            (
                pool_contract.address,
                pool_contract.encode(method_name='getReserves'),
            ), (
                pool_contract.address,
                pool_contract.encode(method_name='token0'),
            ), (
                pool_contract.address,
                pool_contract.encode(method_name='token1'),
            ),
        ]
        output = multicall(
            ethereum=self.eth_manager,
            calls=calls,
            require_success=True,
            block_identifier=block_identifier,
        )
        token_0 = EthereumToken(
            to_checksum_address(pool_contract.decode(output[1], 'token0')[0]),  # noqa: E501 pylint:disable=unsubscriptable-object
        )
        token_1 = EthereumToken(
            to_checksum_address(pool_contract.decode(output[2], 'token1')[0]),  # noqa: E501 pylint:disable=unsubscriptable-object
        )
        reserve_0, reserve_1, _ = pool_contract.decode(output[0], 'getReserves')
        decimals_constant = 10**(token_0.decimals - token_1.decimals)

        price = (reserve_1 / reserve_0) * decimals_constant

        return PoolPrice(price=price, token_0=token_0, token_1=token_1)
