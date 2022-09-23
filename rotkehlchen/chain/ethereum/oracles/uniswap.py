import abc
import logging
from functools import reduce
from operator import mul
from typing import TYPE_CHECKING, List, NamedTuple, Optional

from eth_utils import to_checksum_address
from web3.types import BlockIdentifier

from rotkehlchen.assets.asset import Asset, CryptoAsset, EvmToken
from rotkehlchen.chain.ethereum.constants import ZERO_ADDRESS
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_USD, A_USDC, A_USDT, A_WETH
from rotkehlchen.constants.ethereum import (
    SINGLE_SIDE_USD_POOL_LIMIT,
    UNISWAP_V2_FACTORY,
    UNISWAP_V2_LP_ABI,
    UNISWAP_V3_FACTORY,
    UNISWAP_V3_POOL_ABI,
)
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.defi import DefiPoolError
from rotkehlchen.errors.price import PriceQueryUnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.interfaces import CurrentPriceOracleInterface
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Price
from rotkehlchen.utils.mixins.cacheable import CacheableMixIn, cache_response_timewise

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
UNISWAP_FACTORY_DEPLOYED_BLOCK = 12369621


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class PoolPrice(NamedTuple):
    price: FVal
    token_0: EvmToken
    token_1: EvmToken

    def swap_tokens(self) -> 'PoolPrice':
        return PoolPrice(
            price=1 / self.price,
            token_0=self.token_1,
            token_1=self.token_0,
        )


class UniswapOracle(CurrentPriceOracleInterface, CacheableMixIn):
    """
    Provides shared logic between Uniswap V2 and Uniswap V3 to use them as price oracles.
    """
    def __init__(self, eth_manager: 'EthereumManager', version: int):
        CacheableMixIn.__init__(self)
        CurrentPriceOracleInterface.__init__(self, oracle_name=f'Uniswap V{version} oracle')
        self.eth_manager = eth_manager
        self.routing_assets = [
            A_WETH.resolve_to_evm_token(),
            A_DAI.resolve_to_evm_token(),
            A_USDT.resolve_to_evm_token(),
        ]

    def rate_limited_in_last(
            self,
            seconds: Optional[int] = None,  # pylint: disable=unused-argument
    ) -> bool:
        return False

    @abc.abstractmethod
    def get_pool(
        self,
        token_0: EvmToken,
        token_1: EvmToken,
    ) -> List[str]:
        """Given two tokens returns a list of pools where they can be swapped"""
        ...

    @abc.abstractmethod
    def get_pool_price(
        self,
        pool_addr: ChecksumEvmAddress,
        block_identifier: BlockIdentifier = 'latest',
    ) -> PoolPrice:
        """Returns the price for the tokens in the given pool and the token0 and
        token1 of the pool.
        May raise:
        - DefiPoolError
        """
        ...

    def _find_pool_for(
        self,
        asset: EvmToken,
        link_asset: EvmToken,
        path: List[str],
    ) -> bool:
        pools = self.get_pool(asset, link_asset)
        for pool in pools:
            if pool != ZERO_ADDRESS:
                path.append(pool)
                return True

        return False

    def find_route(self, from_asset: EvmToken, to_asset: EvmToken) -> List[str]:
        """
        Calculate the path needed to go from from_asset to to_asset and return a
        list of the pools needed to jump through to do that.
        """
        output: List[str] = []
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
        from_asset: CryptoAsset,
        to_asset: CryptoAsset,
        block_identifier: BlockIdentifier,
    ) -> Price:
        """
        Return the price of from_asset to to_asset at the block block_identifier.

        Can raise:
        - DefiPoolError
        - RemoteError
        """
        log.debug(
            f'Searching price for {from_asset} to {to_asset} at '
            f'{block_identifier!r} with {self.name}',
        )

        # Uniswap V2 and V3 use in their contracts WETH instead of ETH
        if from_asset == A_ETH:
            from_asset = A_WETH.resolve_to_crypto_asset()
        if to_asset == A_ETH:
            to_asset = A_WETH.resolve_to_crypto_asset()

        try:
            from_token = from_asset.resolve_to_evm_token()
            to_token = to_asset.resolve_to_evm_token()
        except WrongAssetType as e:
            raise PriceQueryUnsupportedAsset(e.identifier) from e

        if from_token == to_token:
            return Price(ONE)

        route = self.find_route(from_token, to_token)

        if len(route) == 0:
            log.debug(f'Failed to find uniswap price for {from_token} to {to_token}')
            return Price(ZERO)
        log.debug(f'Found price route {route} for {from_token} to {to_token} using {self.name}')

        prices_and_tokens = []
        for step in route:
            log.debug(f'Getting pool price for {step}')
            prices_and_tokens.append(
                self.get_pool_price(
                    pool_addr=to_checksum_address(step),
                    block_identifier=block_identifier,
                ),
            )

        # Looking at which one is token0 and token1 we need to see if we need price or 1/price
        if prices_and_tokens[0].token_0 != from_token:
            prices_and_tokens[0] = prices_and_tokens[0].swap_tokens()

        # For the possible intermediate steps also make sure that we use the correct price
        for pos, item in enumerate(prices_and_tokens[1:-1]):
            if item.token_0 != prices_and_tokens[pos - 1].token_1:
                prices_and_tokens[pos - 1] = prices_and_tokens[pos - 1].swap_tokens()

        # Finally for the tail query the price
        if prices_and_tokens[-1].token_1 != to_token:
            prices_and_tokens[-1] = prices_and_tokens[-1].swap_tokens()

        price = FVal(reduce(mul, [item.price for item in prices_and_tokens], 1))
        return Price(price)

    def query_current_price(self, from_asset: Asset, to_asset: Asset) -> Price:
        """
        This method gets the current price for two ethereum tokens finding a pool
        or a path of pools in the uniswap protocol. The special case of USD as asset
        is handled using USDC instead of USD since is one of the most used stables
        right now for pools.
        """
        if to_asset == A_USD:
            to_asset = A_USDC
        elif from_asset == A_USD:
            from_asset = A_USDC

        try:
            to_asset = to_asset.resolve_to_crypto_asset()
            from_asset = from_asset.resolve_to_crypto_asset()
        except UnknownAsset as e:
            raise PriceQueryUnsupportedAsset(e.asset_name) from e
        except WrongAssetType as e:
            raise PriceQueryUnsupportedAsset(e.identifier) from e

        return self.get_price(
            from_asset=from_asset,
            to_asset=to_asset,
            block_identifier='latest',
        )


class UniswapV3Oracle(UniswapOracle):

    def __init__(self, eth_manager: 'EthereumManager'):
        super().__init__(eth_manager=eth_manager, version=3)

    @cache_response_timewise()
    def get_pool(
        self,
        token_0: EvmToken,
        token_1: EvmToken,
    ) -> List[str]:
        result = self.eth_manager.multicall_specific(
            contract=UNISWAP_V3_FACTORY,
            method_name='getPool',
            arguments=[[
                token_0.evm_address,
                token_1.evm_address,
                fee,
            ] for fee in (3000, 500, 10000)],
        )

        # get liquidity for each pool and choose the pool with the highest liquidity
        best_pool, max_liquidity = to_checksum_address(result[0][0]), 0
        for query in result:
            if query[0] == ZERO_ADDRESS:
                continue
            pool_address = to_checksum_address(query[0])
            pool_contract = EvmContract(
                address=pool_address,
                abi=UNISWAP_V3_POOL_ABI,
                deployed_block=UNISWAP_FACTORY_DEPLOYED_BLOCK,
            )
            pool_liquidity = pool_contract.call(
                manager=self.eth_manager,
                method_name='liquidity',
                arguments=[],
                call_order=None,
            )
            if pool_liquidity > max_liquidity:
                best_pool = pool_address

        return [best_pool]

    def get_pool_price(
        self,
        pool_addr: ChecksumEvmAddress,
        block_identifier: BlockIdentifier = 'latest',
    ) -> PoolPrice:
        """
        Returns the units of token1 that one token0 can buy

        May raise:
        - DefiPoolError
        """
        pool_contract = EvmContract(
            address=pool_addr,
            abi=UNISWAP_V3_POOL_ABI,
            deployed_block=UNISWAP_FACTORY_DEPLOYED_BLOCK,
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
        output = self.eth_manager.multicall(
            calls=calls,
            require_success=True,
            block_identifier=block_identifier,
        )
        token_0 = EvmToken(
            ethaddress_to_identifier(to_checksum_address(pool_contract.decode(output[1], 'token0')[0])),  # noqa: E501 pylint:disable=unsubscriptable-object
        )
        token_1 = EvmToken(
            ethaddress_to_identifier(to_checksum_address(pool_contract.decode(output[2], 'token1')[0])),  # noqa: E501 pylint:disable=unsubscriptable-object
        )

        sqrt_price_x96, _, _, _, _, _, _ = pool_contract.decode(output[0], 'slot0')
        if token_0.decimals is None:
            raise DefiPoolError(f'Token {token_0} has None as decimals')
        if token_1.decimals is None:
            raise DefiPoolError(f'Token {token_1} has None as decimals')
        decimals_constant = 10 ** (token_0.decimals - token_1.decimals)

        price = FVal((sqrt_price_x96 * sqrt_price_x96) / 2 ** (192) * decimals_constant)

        if ZERO == price:
            raise DefiPoolError(f'Uniswap pool for {token_0}/{token_1} has price 0')

        return PoolPrice(price=price, token_0=token_0, token_1=token_1)


class UniswapV2Oracle(UniswapOracle):

    def __init__(self, eth_manager: 'EthereumManager'):
        super().__init__(eth_manager=eth_manager, version=3)

    @cache_response_timewise()
    def get_pool(
        self,
        token_0: EvmToken,
        token_1: EvmToken,
    ) -> List[str]:
        result = UNISWAP_V2_FACTORY.call(
            manager=self.eth_manager,
            method_name='getPair',
            arguments=[
                token_0.evm_address,
                token_1.evm_address,
            ],
        )
        return [result]

    def get_pool_price(
        self,
        pool_addr: ChecksumEvmAddress,
        block_identifier: BlockIdentifier = 'latest',
    ) -> PoolPrice:
        """
        Returns the units of token1 that one token0 can buy

        May raise:
        - DefiPoolError
        """
        pool_contract = EvmContract(
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
        output = self.eth_manager.multicall(
            calls=calls,
            require_success=True,
            block_identifier=block_identifier,
        )
        token_0 = EvmToken(
            ethaddress_to_identifier(to_checksum_address(pool_contract.decode(output[1], 'token0')[0])),  # noqa: E501 pylint:disable=unsubscriptable-object
        )
        token_1 = EvmToken(
            ethaddress_to_identifier(to_checksum_address(pool_contract.decode(output[2], 'token1')[0])),  # noqa: E501 pylint:disable=unsubscriptable-object
        )

        if token_0.decimals is None:
            raise DefiPoolError(f'Token {token_0} has None as decimals')
        if token_1.decimals is None:
            raise DefiPoolError(f'Token {token_1} has None as decimals')
        reserve_0, reserve_1, _ = pool_contract.decode(output[0], 'getReserves')
        decimals_constant = 10**(token_0.decimals - token_1.decimals)

        if ZERO in (reserve_0, reserve_1):
            raise DefiPoolError(f'Uniswap pool for {token_0}/{token_1} has asset with no reserves')

        # Ignore pools with too low single side-liquidity. Imperfect approach to avoid spam
        # pylint: disable=unexpected-keyword-arg  # no idea why pylint sees this here
        price_0 = Inquirer().find_usd_price(token_0, skip_onchain=True)
        price_1 = Inquirer().find_usd_price(token_1, skip_onchain=True)
        if price_0 != ZERO and price_0 * token_normalized_value(token_amount=reserve_0, token=token_0) < SINGLE_SIDE_USD_POOL_LIMIT:  # noqa: E501
            raise DefiPoolError(f'Uniswap pool for {token_0}/{token_1} has too low reserves')
        if price_1 != ZERO and price_1 * token_normalized_value(token_amount=reserve_1, token=token_1) < SINGLE_SIDE_USD_POOL_LIMIT:  # noqa: E501
            raise DefiPoolError(f'Uniswap pool for {token_0}/{token_1} has too low reserves')

        price = FVal((reserve_1 / reserve_0) * decimals_constant)
        return PoolPrice(price=price, token_0=token_0, token_1=token_1)
