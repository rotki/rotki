import abc
import logging
from functools import reduce
from operator import mul
from typing import TYPE_CHECKING, List, Optional, Tuple, Union

from eth_utils import to_checksum_address
from web3.types import BlockIdentifier

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.contracts import EthereumContract
from rotkehlchen.chain.ethereum.utils import multicall, multicall_specific
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_USDT, A_WETH
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
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.interfaces import PriceOracleInterface
from rotkehlchen.types import ChecksumEthAddress, Price, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class UniswapOracle(PriceOracleInterface):
    """
    Provides shared logic between Uniswap V2 and Uniswap V3 to use them as price oracles.
    """
    def __init__(self, eth_manager: 'EthereumManager'):
        super().__init__(oracle_name=self.get_oracle_name())
        self.eth_manager = eth_manager
        self.routing_assets = [
            A_WETH,
            A_DAI,
            A_USDT,
        ]

    @abc.abstractmethod
    def get_oracle_name(self) -> str:
        ...

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
    ) -> Tuple[FVal, EthereumToken, EthereumToken]:
        """Returns the price for the tokens in the given pool and the token0 and
        token1 of the pool
        """
        ...

    def rate_limited_in_last(  # pylint: disable=no-self-use
            self,
            seconds: Optional[int] = None,  # pylint: disable=unused-argument
    ) -> bool:
        return False  # noop for uniswap

    def can_query_history(  # pylint: disable=no-self-use
        self,
        from_asset: Asset,  # pylint: disable=unused-argument
        to_asset: Asset,  # pylint: disable=unused-argument
        timestamp: Timestamp,  # pylint: disable=unused-argument
        seconds: Optional[int] = None,  # pylint: disable=unused-argument
    ) -> bool:
        return False  # noop for uniswap oracles atm

    def find_route(self, from_asset: EthereumToken, to_asset: EthereumToken) -> List[str]:
        """
        Calculate the path needed to go from from_asset to to_asset and return a
        list of the pools needed to jump through to do that.
        """
        output = []
        # If any of the assets is in the glue assets let's see if we find any path
        # (avoids iterating the list of glue assets)
        if to_asset in self.routing_assets or from_asset in self.routing_assets:
            pools = self.get_pool(from_asset, to_asset)
            for pool in pools:
                if pool != ZERO_ADDRESS:
                    return [pool]

        if from_asset == to_asset:
            return []

        # Try to find one asset that can be used between from_asset and to_asset
        link_asset = None
        found_first_link, found_second_link = False, False
        for asset in self.routing_assets:
            if asset != from_asset:
                pools = self.get_pool(from_asset, asset)
                for pool in pools:
                    if pool != ZERO_ADDRESS:
                        found_first_link = True
                        output.append(pool)
                        link_asset = asset
                        break
                if found_first_link:
                    # If we have an asset lets see if we can pair with to_asset
                    assert link_asset is not None
                    pools = self.get_pool(link_asset, to_asset)
                    for pool in pools:
                        if pool != ZERO_ADDRESS:
                            found_second_link = True
                            output.append(pool)
                            break
                    if found_second_link:
                        return output

        # if we reach this point it means that we need 2 more jumps
        if not found_first_link:
            return []

        second_link_asset = None
        for asset in self.routing_assets:
            if asset != to_asset:
                pools = self.get_pool(asset, to_asset)
                for pool in pools:
                    if pool != ZERO_ADDRESS:
                        found_second_link = True
                        second_link_asset = asset
                        output.append(pool)
                        break
                if found_second_link:
                    break

        if not found_second_link:
            return []

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
        log.debug(f'Searching price for {from_asset} to {to_asset} at {block_identifier!r}')
        if not (from_asset.is_eth_token() or to_asset.is_eth_token()):
            raise PriceQueryUnsupportedAsset(
                f'Neither {from_asset} nor {to_asset} are ethereum tokens for the uniswap oracle',
            )

        # Use weth internally
        if from_asset == A_ETH:
            from_asset = A_WETH
        if to_asset == A_ETH:
            to_asset = A_WETH

        if from_asset == to_asset:
            return Price(ONE)

        # If we are working with tokens and not ETH just make as if we want to go from eth/to eth
        # and then find the price of asset <=> eth from a different oracle
        from_asset_aux: Union[Asset, EthereumToken] = from_asset
        to_asset_aux: Union[Asset, EthereumToken] = to_asset
        if not from_asset.is_eth_token():
            from_asset_aux = A_WETH
        else:
            from_as_token = EthereumToken.from_identifier(from_asset_aux.identifier)
            if from_as_token is None:
                raise PriceQueryUnsupportedAsset(f'Unsupported asset for uniswap {from_asset_aux}')
            from_asset_aux = from_as_token
        if not to_asset.is_eth_token():
            to_asset_aux = A_WETH
        else:
            to_as_token = EthereumToken.from_identifier(to_asset_aux.identifier)
            if to_as_token is None:
                raise PriceQueryUnsupportedAsset(f'Unsupported asset for uniswap {to_asset_aux}')
            to_asset_aux = to_as_token

        assert isinstance(from_asset_aux, EthereumToken), f'Got non valid token {from_asset_aux}'
        assert isinstance(to_asset_aux, EthereumToken), f'Found non valid token {to_asset_aux}'
        route = self.find_route(from_asset_aux, to_asset_aux)

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

        # Looking at which one is token0 and token1 we need to see if we need price or
        # 1/price (the price from going token0->token1)
        if prices_and_tokens[0][2] != from_asset:
            prices_and_tokens[0] = (
                1 / prices_and_tokens[0][0],
                prices_and_tokens[0][2],
                prices_and_tokens[0][1],
            )

        # For the possible intermediate steps also make sure that we use the correct price
        for pos, item in enumerate(prices_and_tokens[:-1]):
            if item[2] != prices_and_tokens[pos + 1][1]:
                prices_and_tokens[pos] = (
                    1 / item[0],
                    item[2],
                    item[1],
                )

        # Finally for the tail query the price
        if prices_and_tokens[-1][2] != to_asset:
            prices_and_tokens[-1] = (
                1 / prices_and_tokens[-1][0],
                prices_and_tokens[-1][2],
                prices_and_tokens[-1][1],
            )

        price = FVal(reduce(mul, [item[0] for item in prices_and_tokens], 1))
        if not from_asset.is_eth_token():
            price = price * Inquirer().find_price(from_asset, A_ETH)

        if not to_asset.is_eth_token():
            price = price * Inquirer().find_price(A_ETH, to_asset)

        return Price(price)

    def query_current_price(self, from_asset: Asset, to_asset: Asset) -> Price:
        return self.get_price(
            from_asset=from_asset,
            to_asset=to_asset,
            block_identifier='latest',
        )

    def can_query_history(
            self,
            from_asset: Asset,  # pylint: disable=unused-argument
            to_asset: Asset,  # pylint: disable=unused-argument
            timestamp: Timestamp,  # pylint: disable=unused-argument
            seconds: Optional[int] = None,  # pylint: disable=unused-argument
    ) -> bool:
        return False

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
    ) -> Tuple[FVal, EthereumToken, EthereumToken]:
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

        return (price, token_0, token_1)


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
    ) -> Tuple[FVal, EthereumToken, EthereumToken]:
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

        return (price, token_0, token_1)
