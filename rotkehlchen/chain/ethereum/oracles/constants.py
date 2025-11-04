from typing import Final

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import (
    A_BSC_BNB,
    A_DAI,
    A_ETH,
    A_ETH_EURE,
    A_EUR,
    A_OP,
    A_POL,
    A_USD,
    A_USDC,
    A_USDT,
    A_WBNB,
    A_WETH,
    A_WETH_ARB,
    A_WETH_BASE,
    A_WETH_OPT,
    A_WETH_POLYGON,
    A_WPOL,
)
from rotkehlchen.types import ChainID

SINGLE_SIDE_USD_POOL_LIMIT: Final = 5000
UNISWAP_ASSET_TO_EVM_ASSET: Final = {
    A_USD: A_USDC,
    A_EUR: A_ETH_EURE,
    A_ETH: A_WETH,
    A_BSC_BNB: A_WBNB,
    A_POL: A_WPOL,
}

A_POLYGON_USDC: Final = Asset('eip155:137/erc20:0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174')
A_POLYGON_POS_USDT: Final = Asset('eip155:137/erc20:0xc2132D05D31c914a87C6611C10748AEb04B58e8F')
A_ARBITRUM_USDC: Final = Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831')
A_ARBITRUM_USDT: Final = Asset('eip155:42161/erc20:0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9')
A_OPTIMISM_USDC: Final = Asset('eip155:10/erc20:0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85')
A_OPTIMISM_USDT: Final = Asset('eip155:10/erc20:0x94b008aA00579c1307B0EF2c499aD98a8ce58e58')
A_BASE_USDC: Final = Asset('eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913')
A_BSC_USDC: Final = Asset('eip155:56/erc20:0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d')
A_BSC_USDT: Final = Asset('eip155:56/erc20:0x55d398326f99059fF775485246999027B3197955')
A_BSC_ETH: Final = Asset('eip155:56/erc20:0x2170Ed0880ac9A755fd29B2688956BD959F933F8')

UNISWAP_ETH_ASSETS: Final = {
    ChainID.ETHEREUM: A_WETH,
    ChainID.POLYGON_POS: A_WETH_POLYGON,
    ChainID.ARBITRUM_ONE: A_WETH_ARB,
    ChainID.OPTIMISM: A_WETH_OPT,
    ChainID.BASE: A_WETH_BASE,
    ChainID.BINANCE_SC: A_BSC_ETH,
}
UNISWAP_ROUTING_ASSETS: Final = {
    ChainID.ETHEREUM: [A_WETH, A_DAI, A_USDT],
    ChainID.POLYGON_POS: [A_POL, A_WETH_POLYGON, A_POLYGON_USDC, A_POLYGON_POS_USDT],
    ChainID.ARBITRUM_ONE: [A_WETH_ARB, A_ARBITRUM_USDC, A_ARBITRUM_USDT],
    ChainID.OPTIMISM: [A_OP, A_WETH_OPT, A_OPTIMISM_USDC, A_OPTIMISM_USDT],
    ChainID.BASE: [A_WETH_BASE, A_BASE_USDC],
    ChainID.BINANCE_SC: [A_WBNB, A_BSC_USDC, A_BSC_USDT],
}
UNISWAP_FACTORY_ADDRESSES: Final = {
    2: {  # V2 factories
        ChainID.ETHEREUM: string_to_evm_address('0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f'),
        ChainID.POLYGON_POS: string_to_evm_address('0x9e5A52f57b3038F1B8EeE45F28b3C1967e22799C'),
        ChainID.ARBITRUM_ONE: string_to_evm_address('0xf1D7CC64Fb4452F05c498126312eBE29f30Fbcf9'),
        ChainID.OPTIMISM: string_to_evm_address('0x0c3c1c532F1e39EdF36BE9Fe0bE1410313E074Bf'),
        ChainID.BASE: string_to_evm_address('0x8909Dc15e40173Ff4699343b6eB8132c65e18eC6'),
        ChainID.BINANCE_SC: string_to_evm_address('0x8909Dc15e40173Ff4699343b6eB8132c65e18eC6'),
    },
    3: {  # V3 factories
        ChainID.ETHEREUM: string_to_evm_address('0x1F98431c8aD98523631AE4a59f267346ea31F984'),
        ChainID.POLYGON_POS: string_to_evm_address('0x1F98431c8aD98523631AE4a59f267346ea31F984'),
        ChainID.ARBITRUM_ONE: string_to_evm_address('0x1F98431c8aD98523631AE4a59f267346ea31F984'),
        ChainID.OPTIMISM: string_to_evm_address('0x1F98431c8aD98523631AE4a59f267346ea31F984'),
        ChainID.BASE: string_to_evm_address('0x33128a8fC17869897dcE68Ed026d694621f6FDfD'),
        ChainID.BINANCE_SC: string_to_evm_address('0xdB1d10011AD0Ff90774D0C6Bb92e5C5c8b4461F7'),
    },
}
UNISWAP_SUPPORTED_CHAINS: Final = {
    ChainID.ETHEREUM,
    ChainID.POLYGON_POS,
    ChainID.ARBITRUM_ONE,
    ChainID.OPTIMISM,
    ChainID.BASE,
    ChainID.BINANCE_SC,
}
