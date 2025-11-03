import abc
import logging
from collections.abc import Sequence
from functools import reduce
from operator import mul
from typing import TYPE_CHECKING, NamedTuple

from eth_utils import to_checksum_address
from web3.types import BlockIdentifier

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token, token_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_ETH, A_WETH
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.resolver import ChainID, evm_address_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.defi import DefiPoolError
from rotkehlchen.errors.misc import NotERC20Conformant, NotERC721Conformant, RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.interfaces import HistoricalPriceOracleInterface
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Price, Timestamp, TokenKind
from rotkehlchen.utils.mixins.cacheable import CacheableMixIn, cache_response_timewise

from .constants import (
    SINGLE_SIDE_USD_POOL_LIMIT,
    UNISWAP_ASSET_TO_EVM_ASSET,
    UNISWAP_ETH_ASSETS,
    UNISWAP_FACTORY_ADDRESSES,
    UNISWAP_ROUTING_ASSETS,
    UNISWAP_SUPPORTED_CHAINS,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer


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
    def __init__(self, version: int) -> None:
        CacheableMixIn.__init__(self)
        HistoricalPriceOracleInterface.__init__(self, oracle_name=f'Uniswap V{version} oracle')
        self.routing_assets: dict[ChainID, list[EvmToken]] = {}
        self.uniswap_factories = {
            chain_id: Inquirer().get_evm_manager(chain_id).node_inquirer.contracts.contract(UNISWAP_FACTORY_ADDRESSES[version][chain_id])  # noqa: E501
            for chain_id in UNISWAP_SUPPORTED_CHAINS
        }

    def resolve_routing_assets(self) -> None:
        """Resolve the uniswap routing assets to evm tokens.
        Attempt to create the token if it is missing.
        """
        for chain_id, assets in UNISWAP_ROUTING_ASSETS.items():
            self.routing_assets[chain_id] = []
            for asset in assets:
                try:
                    self.routing_assets[chain_id].append(asset.resolve_to_evm_token())
                except UnknownAsset:
                    try:
                        self.routing_assets[chain_id].append(get_or_create_evm_token(
                            userdb=(node_inquirer := Inquirer().get_evm_manager(chain_id).node_inquirer).database,  # noqa: E501
                            evm_address=string_to_evm_address(asset.identifier.split(':')[-1]),
                            chain_id=chain_id,
                            evm_inquirer=node_inquirer,
                        ))
                    except (NotERC20Conformant, NotERC721Conformant) as e:
                        log.error(f'Failed to create missing Uniswap routing asset {asset} due to {e!s}')  # noqa: E501
                        continue

    def resolve_assets(
            self,
            from_asset: Asset,
            to_asset: Asset,
    ) -> Sequence[EvmToken]:
        """Resolve assets to EvmTokens. Returns a tuple containing the from token and to token.
        May raise:
            - PriceQueryUnsupportedAsset
        """
        tokens: list[EvmToken] = []
        for asset in (from_asset, to_asset):
            try:
                token = UNISWAP_ASSET_TO_EVM_ASSET.get(asset, asset).resolve_to_evm_token()
            except WrongAssetType as e:
                raise PriceQueryUnsupportedAsset(e.identifier) from e

            if (
                token.token_kind != TokenKind.ERC20 or
                token.chain_id not in UNISWAP_SUPPORTED_CHAINS
            ):
                raise PriceQueryUnsupportedAsset(f'{self.name} oracle: {token} is not an ERC20 token in an EVM chain supported by Uniswap')  # noqa: E501

            tokens.append(token)

        # Convert A_WETH to the correct weth token from the chain of the other token
        from_token, to_token = tokens
        if from_token.chain_id != to_token.chain_id and A_WETH.resolve_to_evm_token() in tokens:
            if from_asset == A_ETH:
                from_token = UNISWAP_ETH_ASSETS[to_token.chain_id].resolve_to_evm_token()
            elif to_asset == A_ETH:
                to_token = UNISWAP_ETH_ASSETS[from_token.chain_id].resolve_to_evm_token()

        return from_token, to_token

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
            chain_id: ChainID,
            block_identifier: BlockIdentifier = 'latest',
    ) -> PoolPrice:
        """Returns the price for the tokens in the given pool and the token0 and
        token1 of the pool.
        May raise:
        - DefiPoolError
        """

    @abc.abstractmethod
    def is_before_factory_deployment(
            self,
            block_identifier: BlockIdentifier,
            chain_id: ChainID,
    ) -> bool:
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
        if len(self.routing_assets) == 0:
            self.resolve_routing_assets()  # May include external remote calls to add any missing assets  # noqa: E501

        routing_assets = self.routing_assets[from_asset.chain_id]
        output: list[str] = []
        # If any of the assets is in the glue assets let's see if we find any path
        # (avoids iterating the list of glue assets)
        if any(x in routing_assets for x in (to_asset, from_asset)):
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
        for asset in routing_assets:
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
        for asset in routing_assets:
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
            from_token: EvmToken,
            to_token: EvmToken,
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
        if from_token == to_token:
            return Price(ONE)

        log.debug(
            f'Searching price for {from_token} to {to_token} at '
            f'{block_identifier!r} with {self.name}',
        )

        if timestamp is not None and self.is_before_factory_deployment(
            block_identifier=block_identifier,
            chain_id=from_token.chain_id,
        ):
            raise NoPriceForGivenTimestamp(
                from_asset=from_token,
                to_asset=to_token,
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
                    chain_id=from_token.chain_id,
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

    def query_current_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
    ) -> Price:
        """
        This method gets the current price for two ethereum tokens finding a pool
        or a path of pools in the uniswap protocol.
        Returns:
        1. The price of from_asset at the current timestamp
        for the current oracle
        """
        from_token, to_token = self.resolve_assets(from_asset=from_asset, to_asset=to_asset)
        return self.get_price(
            from_token=from_token,
            to_token=to_token,
            block_identifier='latest',
        )

    def _call_methods(
            self,
            pool_contract: EvmContract,
            methods: list[str],
            block_identifier: BlockIdentifier,
            evm_inquirer: 'EvmNodeInquirer',
    ) -> dict:
        """Call methods on the pool contract using multicall if block_identifier
        is since the multicall contract creation, otherwise use individual calls.
        Returns a dict that maps method names to responses.
        """
        if (
            (isinstance(block_identifier, str) and block_identifier == 'latest') or
            (isinstance(block_identifier, int) and block_identifier > evm_inquirer.contract_multicall.deployed_block)  # noqa: E501
        ):
            response = evm_inquirer.multicall(
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
                method_name: evm_inquirer.call_contract(
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
        """Check if we can query the price of the given assets at the specified timestamp.
        Returns true if the assets are resolvable and if the timestamp is after the deployment
        of the uniswap factory contract in this chain. Otherwise, returns false.
        """
        try:
            token, _ = self.resolve_assets(from_asset=from_asset, to_asset=to_asset)
        except PriceQueryUnsupportedAsset:
            return False

        try:
            return self.is_before_factory_deployment(
                block_identifier=Inquirer().get_evm_manager(token.chain_id).node_inquirer.get_blocknumber_by_time(timestamp),
                chain_id=token.chain_id,
            )
        except RemoteError as e:  # can be raised by get_blocknumber_by_time
            log.error(f'Couldnt check if uniswap history could be queried due to {e}. Assuming no.')  # noqa: E501
            return False

    def query_historical_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Price:
        from_token, to_token = self.resolve_assets(from_asset=from_asset, to_asset=to_asset)
        return self.get_price(
            from_token=from_token,
            to_token=to_token,
            block_identifier=Inquirer().get_evm_manager(from_token.chain_id).node_inquirer.get_blocknumber_by_time(timestamp),
            timestamp=timestamp,
        )


class UniswapV3Oracle(UniswapOracle):

    def __init__(self) -> None:
        super().__init__(version=3)
        self.uniswap_v3_pool_abi = Inquirer().get_evm_manager(ChainID.ETHEREUM).node_inquirer.contracts.abi('UNISWAP_V3_POOL')  # noqa: E501

    @cache_response_timewise()
    def get_pool(
            self,
            token_0: EvmToken,
            token_1: EvmToken,
    ) -> list[str]:
        result = (evm_inquirer := Inquirer().get_evm_manager(token_0.chain_id).node_inquirer).multicall_specific(  # noqa: E501
            contract=(uniswap_factory := self.uniswap_factories[token_0.chain_id]),
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
                deployed_block=uniswap_factory.deployed_block,
            )
            pool_liquidity = pool_contract.call(
                node_inquirer=evm_inquirer,
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
            chain_id: ChainID,
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
            deployed_block=self.uniswap_factories[chain_id].deployed_block,
        )
        output = self._call_methods(
            pool_contract=pool_contract,
            methods=['slot0', 'token0', 'token1'],
            block_identifier=block_identifier,
            evm_inquirer=Inquirer().get_evm_manager(chain_id).node_inquirer,
        )
        token_0_address = output['token0']
        token_1_address = output['token1']
        try:
            token_0 = EvmToken(evm_address_to_identifier(
                address=to_checksum_address(token_0_address),
                chain_id=chain_id,
            ))
            token_1 = EvmToken(evm_address_to_identifier(
                address=to_checksum_address(token_1_address),
                chain_id=chain_id,
            ))
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

    def is_before_factory_deployment(
            self,
            block_identifier:
            BlockIdentifier,
            chain_id: ChainID,
    ) -> bool:
        """Check if block_identifier is before creation of uniswap v3 factory contract"""
        return block_identifier < self.uniswap_factories[chain_id].deployed_block if isinstance(block_identifier, int) else False  # noqa: E501


class UniswapV2Oracle(UniswapOracle):

    def __init__(self) -> None:
        super().__init__(version=2)
        self.uniswap_v2_lp_abi = Inquirer().get_evm_manager(ChainID.ETHEREUM).node_inquirer.contracts.abi('UNISWAP_V2_LP')  # noqa: E501

    @cache_response_timewise()
    def get_pool(
            self,
            token_0: EvmToken,
            token_1: EvmToken,
    ) -> list[str]:
        result = self.uniswap_factories[token_0.chain_id].call(
            node_inquirer=Inquirer().get_evm_manager(token_0.chain_id).node_inquirer,
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
            chain_id: ChainID,
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
            deployed_block=self.uniswap_factories[chain_id].deployed_block,
        )
        output = self._call_methods(
            pool_contract=pool_contract,
            methods=['getReserves', 'token0', 'token1'],
            block_identifier=block_identifier,
            evm_inquirer=Inquirer().get_evm_manager(chain_id).node_inquirer,
        )
        token_0_address = output['token0']
        token_1_address = output['token1']

        try:
            token_0 = EvmToken(evm_address_to_identifier(
                address=to_checksum_address(token_0_address),
                chain_id=chain_id,
            ))
        except (UnknownAsset, WrongAssetType) as e:
            raise DefiPoolError(f'Failed to read token from address {token_0_address} as ERC-20 token') from e  # noqa: E501

        try:
            token_1 = EvmToken(evm_address_to_identifier(
                address=to_checksum_address(token_1_address),
                chain_id=chain_id,
            ))
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
        if price_0 != ZERO and price_0 * token_normalized_value(token_amount=reserve_0, token=token_0) < SINGLE_SIDE_USD_POOL_LIMIT:  # noqa: E501
            raise DefiPoolError(f'Uniswap pool for {token_0}/{token_1} has too low reserves')
        if price_1 != ZERO and price_1 * token_normalized_value(token_amount=reserve_1, token=token_1) < SINGLE_SIDE_USD_POOL_LIMIT:  # noqa: E501
            raise DefiPoolError(f'Uniswap pool for {token_0}/{token_1} has too low reserves')

        price = FVal((reserve_1 / reserve_0) * decimals_constant)
        return PoolPrice(price=price, token_0=token_0, token_1=token_1)

    def is_before_factory_deployment(
            self,
            block_identifier: BlockIdentifier,
            chain_id: ChainID,
    ) -> bool:
        """Check if block_identifier is before creation of uniswap v2 factory contract"""
        return block_identifier < self.uniswap_factories[chain_id].deployed_block if isinstance(block_identifier, int) else False  # noqa: E501
