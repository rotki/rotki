from logging.handlers import RotatingFileHandler
from typing import Optional, TYPE_CHECKING, List, Tuple
from functools import reduce
from operator import mul

from eth_utils import to_checksum_address

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.contracts import EthereumContract
from rotkehlchen.chain.ethereum.utils import multicall, multicall_specific
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.constants.assets import A_ETH, A_WETH, A_DAI, A_USDT, A_USDC
from rotkehlchen.constants.ethereum import UNISWAP_V3_POOL_ABI, UNISWAP_V3_FACTORY, ZERO_ADDRESS
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.types import ChecksumEthAddress, Price, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager


def get_pool_price(
        pool_addr: ChecksumEthAddress,
        eth_manager: 'EthereumManager',
    ) -> FVal:
    """
    Returns the units of token1 that one token0 can buy
    """
    pool_contract = EthereumContract(
        address=pool_addr,
        abi=UNISWAP_V3_POOL_ABI,
        deployed_block=12369621,  # Factory deployment block
    )
    calls = [(
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
    output = multicall(eth_manager, calls, True)
    token_0 = EthereumToken(to_checksum_address(pool_contract.decode(output[1], 'token0')[0]))
    token_1 = EthereumToken(to_checksum_address(pool_contract.decode(output[2], 'token1')[0]))
    sqrtPriceX96, _, _, _, _, _, _ = pool_contract.decode(output[0], 'slot0')
    decimals_constant = 10**(token_0.decimals - token_1.decimals)

    price = ( sqrtPriceX96 * sqrtPriceX96 ) / 2 ** (192) * decimals_constant

    return [price, token_0, token_1]


class UniswapV3Oracle:

    def __init__(self, eth_manager: 'EthereumManager'):
        self.eth_manager = eth_manager
        self.routing_assets = [
            A_WETH
        ]

    def can_query_history(  # pylint: disable=no-self-use
            self,
            from_asset: Asset,  # pylint: disable=unused-argument
            to_asset: Asset,  # pylint: disable=unused-argument
            timestamp: Timestamp,  # pylint: disable=unused-argument
            seconds: Optional[int] = None,  # pylint: disable=unused-argument
    ) -> bool:
        return False  # noop for coingecko

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

    def find_route(self, from_asset: Asset, to_asset: Asset) -> List[str]:
        """
        Returns a list of the pools that will be needed to go from_asset to to_asset
        """
        output = []
        # If any of the assets is in the glue assets let's see if we find any path
        if to_asset in self.routing_assets or from_asset in self.routing_assets:
            pools = self.get_pool(from_asset, to_asset)
            for pool in pools:
                if pool != ZERO_ADDRESS:
                    return [pool]

        if from_asset == to_asset:
            return []

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

        pools = self.get_pool(link_asset, second_link_asset)
        for pool in pools:
            if pool != ZERO_ADDRESS:
                output.insert(1, pool)
                return output

        return []

    def query_current_price(self, from_asset: Asset, to_asset: Asset) -> Price:

        if not (from_asset.is_eth_token() or to_asset.is_eth_token()):
            return Price(ZERO)
        
        # Use weth internally
        if from_asset == A_ETH:
            from_asset == A_WETH
        if to_asset == A_ETH:
            to_asset == A_WETH

        if from_asset == to_asset:
            return Price(ONE)

        from_asset_aux, to_asset_aux = from_asset, to_asset
        if not from_asset.is_eth_token():
            from_asset_aux = A_WETH
        if not to_asset.is_eth_token():
            to_asset_aux = A_WETH

        route = self.find_route(from_asset_aux, to_asset_aux)

        prices_and_tokens = []
        for step in route:
            prices_and_tokens.append(
                get_pool_price(to_checksum_address(step), self.eth_manager),
            )

        if prices_and_tokens[0][2] != from_asset:
            prices_and_tokens[0][0] = 1/prices_and_tokens[0][0]
            prices_and_tokens[0][1], prices_and_tokens[0][2] = prices_and_tokens[0][2], prices_and_tokens[0][1]
        
        for pos, item in enumerate(prices_and_tokens[:-1]):
            if item[2] != prices_and_tokens[pos+1][1]:
                item[0] = 1/item[0]
                item[1], item[2] = item[2], item[1]

        if prices_and_tokens[-1][2] != to_asset:
            prices_and_tokens[-1][0] = 1/prices_and_tokens[-1][0]
            prices_and_tokens[-1][1], prices_and_tokens[-1][2] = prices_and_tokens[-1][2], prices_and_tokens[-1][1]

        for path in prices_and_tokens:
            print(f'{path[1]} <=> {path[2]}')


        price = FVal(reduce(mul, [item[0] for item in prices_and_tokens], 1))

        if not from_asset.is_eth_token():
            price = price * Inquirer().find_price(from_asset, A_ETH)
        
        if not to_asset.is_eth_token():
            price = price * Inquirer().find_price(A_ETH, to_asset)

        return price