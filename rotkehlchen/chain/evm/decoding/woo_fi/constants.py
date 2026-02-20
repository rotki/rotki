from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID

CPT_WOO_FI: Final = 'woo-fi'
CPT_WOO_FI_LABEL: Final = 'WOOFi'

WOO_FI_SUPPORTED_CHAINS: Final = {
    ChainID.ARBITRUM_ONE,
    ChainID.BASE,
    ChainID.BINANCE_SC,
    ChainID.ETHEREUM,
    ChainID.OPTIMISM,
    ChainID.POLYGON_POS,
}

WOO_ROUTER_V2: Final = string_to_evm_address('0x4c4AF8DBc524681930a27b2F1Af5bcC8062E6fB7')
WOO_CROSS_SWAP_ROUTER_V5: Final = string_to_evm_address('0xB84aEfEF2DDDE628d5c7F1fba320dE63e3f4757c')  # noqa: E501
WOO_ROUTER_SWAP_TOPIC: Final = b"'\xc9\x8e\x91\x1e\xfd\xd2$\xf4\x00/l\xd81\xc3\xad\r'Y\xee\x17o\x9e\xe8Fm\x95\x82j\xf2*\x1c"  # noqa: E501
WOO_CROSS_SWAP_ON_SRC_CHAIN_TOPIC: Final = b'\x8d\xbfa\xe7L\x14\xd5\xd85\x81jk\xda\xf0\x87K\xd5\xf7\xbf\xf3\xeeM\x8cL\x83\xd0\xe6\xbf\x8d\xa4\xcfr'  # noqa: E501
WOO_CROSS_SWAP_ON_DEST_CHAIN_TOPIC: Final = b'\x96\xdd\xa4\xec\xb8m8\xbc\x80nC\xde }m`"IG\xe1$J#\x08\x9bV\x8fhV\xeb\xa6\xb5'  # noqa: E501

# For WOOFi cross-chain swaps, the only way to tell what chain it is from/to is by the LayerZero
# endpoint id. These ids are not directly correlated to chain ids, so we need to map them here.
# https://docs.layerzero.network/v2/faq#whats-the-difference-between-endpoint-id-eid-and-chain-id
# Also see https://docs.layerzero.network/v2/deployments/deployed-contracts for mappings list
LAYER_ZERO_EID_TO_CHAIN_ID: Final = {
    30101: ChainID.ETHEREUM,
    30111: ChainID.OPTIMISM,
    30102: ChainID.BINANCE_SC,
    30145: ChainID.GNOSIS,
    30109: ChainID.POLYGON_POS,
    30112: ChainID.FANTOM,
    30184: ChainID.BASE,
    30110: ChainID.ARBITRUM_ONE,
    30106: ChainID.AVALANCHE,
    30125: ChainID.CELO,
    30175: ChainID.ARBITRUM_NOVA,
    30359: ChainID.CRONOS,
    30158: ChainID.POLYGON_ZKEVM,
    30165: ChainID.ZKSYNC_ERA,
    30214: ChainID.SCROLL,
    30332: ChainID.SONIC,
    30183: ChainID.LINEA,
}
