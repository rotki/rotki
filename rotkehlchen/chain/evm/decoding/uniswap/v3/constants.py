from typing import Final

SWAP_SIGNATURE: Final = b'\xc4 y\xf9JcP\xd7\xe6#_)\x17I$\xf9(\xcc*\xc8\x18\xebd\xfe\xd8\x00N\x11_\xbc\xcag'  # noqa: E501
DIRECT_SWAP_SIGNATURE: Final = b'\xd2\xd7=\xa2\xb5\xfdR\xcdeM\x8f\xd1\xb5\x14\xadW5[\xadt\x1d\xe69\xe3\xa1\xc3\xa2\r\xd9\xf1sG'  # noqa: E501

# https://www.4byte.directory/api/v1/event-signatures/?hex_signature=0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67  # noqa: E501
# https://docs.uniswap.org/protocol/reference/core/interfaces/pool/IUniswapV3PoolEvents#swap
INCREASE_LIQUIDITY_SIGNATURE: Final = b'0g\x04\x8b\xee\xe3\x1b%\xb2\xf1h\x1f\x88\xda\xc88\xc8\xbb\xa3j\xf2[\xfb+|\xf7G:XG\xe3_'  # noqa: E501
COLLECT_LIQUIDITY_SIGNATURE: Final = b"@\xd0\xef\xd1\xa5=`\xec\xbf@\x97\x1b\x9d\xaf}\xc9\x01x\xc3\xaa\xdcz\xab\x17ec'8\xfa\x8b\x8f\x01"  # noqa: E501
