import abc
import logging
from functools import reduce
from operator import mul
from typing import TYPE_CHECKING, Final, NamedTuple

from eth_utils import to_checksum_address
from web3.types import BlockIdentifier

from rotkehlchen.assets.asset import Asset, AssetWithOracles, EvmToken
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import (
    A_DAI,
    A_ETH,
    A_ETH_EURE,
    A_EUR,
    A_USD,
    A_USDC,
    A_USDT,
    A_WETH,
)
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.resolver import ChainID, ethaddress_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.defi import DefiPoolError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.interfaces import HistoricalPriceOracleInterface
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTokenKind, Price, Timestamp
from rotkehlchen.utils.mixins.cacheable import CacheableMixIn, cache_response_timewise

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer

UNISWAPV3_FACTORY_DEPLOYED_BLOCK: Final = 12369621
UNISWAPV2_FACTORY_DEPLOYED_BLOCK: Final = 10000835
MULTICALL_DEPLOYED_BLOCK: Final = 14353601
SINGLE_SIDE_USD_POOL_LIMIT: Final = 5000

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


class UniswapOracle(HistoricalPriceOracleInterface, CacheableMixIn):
    """
    Provides shared logic between Uniswap V2 and Uniswap V3 to use them as price oracles.
    """
    def __init__(self, ethereum_inquirer: 'EthereumInquirer', version: int):
        CacheableMixIn.__init__(self)
        HistoricalPriceOracleInterface.__init__(self, oracle_name=f'Uniswap V{version} oracle')
        self.ethereum = ethereum_inquirer
        self.weth = A_WETH.resolve_to_evm_token()
        self.routing_assets = [
            self.weth,
            A_DAI.resolve_to_evm_token(),
            A_USDT.resolve_to_evm_token(),
        ]

    def rate_limited_in_last(
            self,
            seconds: int | None = None,  # pylint: disable=unused-argument
    ) -> bool:
        return False

    @abc.abstractmethod
    def get_pool(
            self,
            token_0: EvmToken,
            token_1: EvmToken,
    ) -> list[str]:
        """Given two tokens returns a list of pools where they can be swapped"""

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

    @abc.abstractmethod
    def is_before_contract_creation(self, block_identifier: BlockIdentifier) -> bool:
        """Check if block_identifier is before the creation of the uniswap version's contract.
        When querying current prices block_identifier will be 'latest' instead of a block number,
        so return False if block_identifier is not an int.
        """

    def _find_pool_for(
            self,
            asset: EvmToken,
            link_asset: EvmToken,
            path: list[str],
    ) -> bool:
        pools = self.get_pool(asset, link_asset)
        for pool in pools:
            if pool != ZERO_ADDRESS:
                path.append(pool)
                return True

        return False

    def find_route(self, from_asset: EvmToken, to_asset: EvmToken) -> list[str]:
        """
        Calculate the path needed to go from from_asset to to_asset and return a
        list of the pools needed to jump through to do that.
        """
        output: list[str] = []
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
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
            block_identifier: BlockIdentifier,
            timestamp: Timestamp | None = None,
    ) -> Price:
        """
        Return the price of from_asset to to_asset at the block block_identifier.
        Timestamp enables properly raising NoPriceForGivenTimestamp during historical price queries

        Can raise:
        - DefiPoolError
        - RemoteError
        """
        # Uniswap V2 and V3 use in their contracts WETH instead of ETH
        if from_asset == A_ETH:
            from_asset = self.weth
        if to_asset == A_ETH:
            to_asset = self.weth

        try:
            from_token = from_asset.resolve_to_evm_token()
            to_token = to_asset.resolve_to_evm_token()
        except WrongAssetType as e:
            raise PriceQueryUnsupportedAsset(e.identifier) from e

        if from_token == to_token:
            return Price(ONE)

        if (
                from_token.token_kind != EvmTokenKind.ERC20 or
                to_token.token_kind != EvmTokenKind.ERC20 or
                from_token.chain_id != ChainID.ETHEREUM or
                to_token.chain_id != ChainID.ETHEREUM
        ):
            raise PriceQueryUnsupportedAsset(f'{self.name} oracle: Either {from_token} or {to_token} is not an ERC20 token in Ethereum mainnet')  # noqa: E501

        log.debug(
            f'Searching price for {from_asset} to {to_asset} at '
            f'{block_identifier!r} with {self.name}',
        )

        if timestamp is not None and self.is_before_contract_creation(block_identifier):
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
            )

        route = self.find_route(from_token, to_token)

        if len(route) == 0:
            log.debug(f'Failed to find uniswap price for {from_token} to {to_token}')
            return ZERO_PRICE
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

    def _replace_fiat_with_stablecoin(self, assets: list[AssetWithOracles]) -> list[AssetWithOracles]:  # noqa: E501
        """Replace fiat assets with their stablecoin equivalents."""
        for index, asset in enumerate(assets):
            if asset == A_USD:
                assets[index] = A_USDC.resolve_to_asset_with_oracles()
            elif asset == A_EUR:
                assets[index] = A_ETH_EURE.resolve_to_asset_with_oracles()

        return assets

    def query_current_price(
            self,
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
    ) -> Price:
        """
        This method gets the current price for two ethereum tokens finding a pool
        or a path of pools in the uniswap protocol.
        Returns:
        1. The price of from_asset at the current timestamp
        for the current oracle
        """
        to_asset, from_asset = self._replace_fiat_with_stablecoin([to_asset, from_asset])
        return self.get_price(
            from_asset=from_asset,
            to_asset=to_asset,
            block_identifier='latest',
        )

    def _call_methods(
            self,
            pool_contract: EvmContract,
            methods: list[str],
            block_identifier: BlockIdentifier,
    ) -> dict:
        """Call methods on the pool contract using multicall if block_identifier
        is since the multicall contract creation, otherwise use individual calls.
        Returns a dict that maps method names to responses.
        """
        if (
            (isinstance(block_identifier, str) and block_identifier == 'latest') or
            (isinstance(block_identifier, int) and block_identifier > MULTICALL_DEPLOYED_BLOCK)
        ):
            response = self.ethereum.multicall(
                calls=[
                    (
                        pool_contract.address,
                        pool_contract.encode(method_name=method_name),
                    )
                    for method_name in methods
                ],
                require_success=True,
                block_identifier=block_identifier,
            )
            output = {}
            for index, method_name in enumerate(methods):
                data = pool_contract.decode(response[index], method_name)
                output[method_name] = data[0] if len(data) == 1 else data
        else:
            output = {
                method_name: self.ethereum.call_contract(
                    contract_address=pool_contract.address,
                    abi=pool_contract.abi,
                    method_name=method_name,
                    block_identifier=block_identifier,
                )
                for method_name in methods
            }
        return output

    def can_query_history(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
            seconds: int | None = None,
    ) -> bool:
        """Here to comply with price historian interface."""
        return self.is_before_contract_creation(self.ethereum.get_blocknumber_by_time(timestamp))

    def query_historical_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Price:
        to_asset, from_asset = self._replace_fiat_with_stablecoin([
            to_asset.resolve_to_asset_with_oracles(),
            from_asset.resolve_to_asset_with_oracles(),
        ])
        return self.get_price(
            from_asset=from_asset.resolve_to_asset_with_oracles(),
            to_asset=to_asset.resolve_to_asset_with_oracles(),
            block_identifier=self.ethereum.get_blocknumber_by_time(timestamp),
            timestamp=timestamp,
        )


class UniswapV3Oracle(UniswapOracle):

    def __init__(self, ethereum_inquirer: 'EthereumInquirer'):
        super().__init__(ethereum_inquirer=ethereum_inquirer, version=3)
        self.uniswap_v3_pool_abi = self.ethereum.contracts.abi('UNISWAP_V3_POOL')
        self.uniswap_v3_factory = self.ethereum.contracts.contract(string_to_evm_address('0x1F98431c8aD98523631AE4a59f267346ea31F984'))  # noqa: E501

    @cache_response_timewise()
    def get_pool(
            self,
            token_0: EvmToken,
            token_1: EvmToken,
    ) -> list[str]:
        result = self.ethereum.multicall_specific(
            contract=self.uniswap_v3_factory,
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
                abi=self.uniswap_v3_pool_abi,
                deployed_block=UNISWAPV3_FACTORY_DEPLOYED_BLOCK,
            )
            pool_liquidity = pool_contract.call(
                node_inquirer=self.ethereum,
                method_name='liquidity',
                arguments=[],
                call_order=None,
            )
            if pool_liquidity > max_liquidity:
                best_pool = pool_address
                max_liquidity = pool_liquidity

        if max_liquidity == 0:
            # if there is no pool with assets don't return any pool
            return []
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
            abi=self.uniswap_v3_pool_abi,
            deployed_block=UNISWAPV3_FACTORY_DEPLOYED_BLOCK,
        )
        output = self._call_methods(
            pool_contract=pool_contract,
            methods=['slot0', 'token0', 'token1'],
            block_identifier=block_identifier,
        )
        token_0_address = output['token0']
        token_1_address = output['token1']
        try:
            token_0 = EvmToken(
                ethaddress_to_identifier(to_checksum_address(token_0_address)),
            )
            token_1 = EvmToken(
                ethaddress_to_identifier(to_checksum_address(token_1_address)),
            )
        except (UnknownAsset, WrongAssetType) as e:
            raise DefiPoolError(f'Failed to read token from address {token_0_address} or {token_1_address} as ERC-20 token') from e  # noqa: E501

        sqrt_price_x96, _, _, _, _, _, _ = output['slot0']
        if token_0.decimals is None:
            raise DefiPoolError(f'Token {token_0} has None as decimals')
        if token_1.decimals is None:
            raise DefiPoolError(f'Token {token_1} has None as decimals')
        decimals_constant = 10 ** (token_0.decimals - token_1.decimals)

        price = FVal((sqrt_price_x96 * sqrt_price_x96) / 2 ** (192) * decimals_constant)

        if price == ZERO:
            raise DefiPoolError(f'Uniswap pool for {token_0}/{token_1} has price 0')

        return PoolPrice(price=price, token_0=token_0, token_1=token_1)

    def is_before_contract_creation(self, block_identifier: BlockIdentifier) -> bool:
        """Check if block_identifier is before creation of uniswap v3 factory contract"""
        return block_identifier < UNISWAPV3_FACTORY_DEPLOYED_BLOCK if isinstance(block_identifier, int) else False  # noqa: E501


class UniswapV2Oracle(UniswapOracle):

    def __init__(self, ethereum_inquirer: 'EthereumInquirer'):
        super().__init__(ethereum_inquirer=ethereum_inquirer, version=2)
        self.uniswap_v2_lp_abi = self.ethereum.contracts.abi('UNISWAP_V2_LP')
        self.uniswap_v2_factory = self.ethereum.contracts.contract(string_to_evm_address('0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f'))  # noqa: E501

    @cache_response_timewise()
    def get_pool(
            self,
            token_0: EvmToken,
            token_1: EvmToken,
    ) -> list[str]:
        result = self.uniswap_v2_factory.call(
            node_inquirer=self.ethereum,
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
            abi=self.uniswap_v2_lp_abi,
            deployed_block=UNISWAPV2_FACTORY_DEPLOYED_BLOCK,
        )
        output = self._call_methods(
            pool_contract=pool_contract,
            methods=['getReserves', 'token0', 'token1'],
            block_identifier=block_identifier,
        )
        token_0_address = output['token0']
        token_1_address = output['token1']

        try:
            token_0 = EvmToken(
                ethaddress_to_identifier(to_checksum_address(token_0_address)),
            )
        except (UnknownAsset, WrongAssetType) as e:
            raise DefiPoolError(f'Failed to read token from address {token_0_address} as ERC-20 token') from e  # noqa: E501

        try:
            token_1 = EvmToken(
                ethaddress_to_identifier(to_checksum_address(token_1_address)),
            )
        except (UnknownAsset, WrongAssetType) as e:
            raise DefiPoolError(f'Failed to read token from address {token_1_address} as ERC-20 token') from e  # noqa: E501

        if token_0.decimals is None:
            raise DefiPoolError(f'Token {token_0} has None as decimals')
        if token_1.decimals is None:
            raise DefiPoolError(f'Token {token_1} has None as decimals')
        reserve_0, reserve_1, _ = output['getReserves']
        decimals_constant = 10**(token_0.decimals - token_1.decimals)

        if ZERO in (reserve_0, reserve_1):
            raise DefiPoolError(f'Uniswap pool for {token_0}/{token_1} has asset with no reserves')

        # Ignore pools with too low single side-liquidity. Imperfect approach to avoid spam
        # pylint: disable=unexpected-keyword-arg  # no idea why pylint sees this here
        price_0 = Inquirer.find_usd_price(token_0, skip_onchain=True)
        price_1 = Inquirer.find_usd_price(token_1, skip_onchain=True)
        if price_0 != ZERO and price_0 * asset_normalized_value(amount=reserve_0, asset=token_0) < SINGLE_SIDE_USD_POOL_LIMIT:  # noqa: E501
            raise DefiPoolError(f'Uniswap pool for {token_0}/{token_1} has too low reserves')
        if price_1 != ZERO and price_1 * asset_normalized_value(amount=reserve_1, asset=token_1) < SINGLE_SIDE_USD_POOL_LIMIT:  # noqa: E501
            raise DefiPoolError(f'Uniswap pool for {token_0}/{token_1} has too low reserves')

        price = FVal((reserve_1 / reserve_0) * decimals_constant)
        return PoolPrice(price=price, token_0=token_0, token_1=token_1)

    def is_before_contract_creation(self, block_identifier: BlockIdentifier) -> bool:
        """Check if block_identifier is before creation of uniswap v2 factory contract"""
        return block_identifier < UNISWAPV2_FACTORY_DEPLOYED_BLOCK if isinstance(block_identifier, int) else False  # noqa: E501
