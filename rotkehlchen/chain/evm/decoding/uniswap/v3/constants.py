from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID

SWAP_SIGNATURE: Final = b'\xc4 y\xf9JcP\xd7\xe6#_)\x17I$\xf9(\xcc*\xc8\x18\xebd\xfe\xd8\x00N\x11_\xbc\xcag'  # noqa: E501
DIRECT_SWAP_SIGNATURE: Final = b'\xd2\xd7=\xa2\xb5\xfdR\xcdeM\x8f\xd1\xb5\x14\xadW5[\xadt\x1d\xe69\xe3\xa1\xc3\xa2\r\xd9\xf1sG'  # noqa: E501

# https://www.4byte.directory/api/v1/event-signatures/?hex_signature=0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67  # noqa: E501
# https://docs.uniswap.org/protocol/reference/core/interfaces/pool/IUniswapV3PoolEvents#swap
INCREASE_LIQUIDITY_SIGNATURE: Final = b'0g\x04\x8b\xee\xe3\x1b%\xb2\xf1h\x1f\x88\xda\xc88\xc8\xbb\xa3j\xf2[\xfb+|\xf7G:XG\xe3_'  # noqa: E501
COLLECT_LIQUIDITY_SIGNATURE: Final = b"@\xd0\xef\xd1\xa5=`\xec\xbf@\x97\x1b\x9d\xaf}\xc9\x01x\xc3\xaa\xdcz\xab\x17ec'8\xfa\x8b\x8f\x01"  # noqa: E501

UNISWAP_V3_NFT_MANAGER_ADDRESSES: Final = {
    ChainID.ETHEREUM: string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
    ChainID.POLYGON_POS: string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
    ChainID.ARBITRUM_ONE: string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
    ChainID.OPTIMISM: string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
    ChainID.BASE: string_to_evm_address('0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1'),
    ChainID.BINANCE_SC: string_to_evm_address('0x7b8A01B39D58278b5DE7e48c8449c9f4F5170613'),
}

# Counterparty used to trigger router post decoding rules.
CPT_UNISWAP_V3_ROUTER: Final = 'uniswap-v3-router'
