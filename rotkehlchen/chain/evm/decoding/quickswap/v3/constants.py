from typing import Final

from eth_typing.abi import ABI

QUICKSWAP_INCREASE_LIQUIDITY_TOPIC: Final = b'\x8a\x82\xde\x7f\xe9\xb3>\x0ek\xca\x0e&\xf5\xbd\x14\xa7O\x11d\xff\xe26\xd5\x0e\n6\xc3\xeap\xf2\xb8\x14'  # noqa: E501
QUICKSWAP_COLLECT_LIQUIDITY_TOPIC: Final = b"@\xd0\xef\xd1\xa5=`\xec\xbf@\x97\x1b\x9d\xaf}\xc9\x01x\xc3\xaa\xdcz\xab\x17ec'8\xfa\x8b\x8f\x01"  # noqa: E501

QUICKSWAP_NFT_MANAGER_ABI: Final[ABI] = [{'inputs': [{'name': 'tokenId', 'type': 'uint256'}], 'name': 'positions', 'outputs': [{'name': 'nonce', 'type': 'uint96'}, {'name': 'operator', 'type': 'address'}, {'name': 'token0', 'type': 'address'}, {'name': 'token1', 'type': 'address'}, {'name': 'tickLower', 'type': 'int24'}, {'name': 'tickUpper', 'type': 'int24'}, {'name': 'liquidity', 'type': 'uint128'}, {'name': 'feeGrowthInside0LastX128', 'type': 'uint256'}, {'name': 'feeGrowthInside1LastX128', 'type': 'uint256'}, {'name': 'tokensOwed0', 'type': 'uint128'}, {'name': 'tokensOwed1', 'type': 'uint128'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501

# Counterparty used to trigger router post decoding rules.
CPT_QUICKSWAP_V3_ROUTER: Final = 'quickswap-v3-router'
