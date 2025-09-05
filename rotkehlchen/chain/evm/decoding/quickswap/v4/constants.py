from typing import Final

from eth_typing.abi import ABI

QUICKSWAP_SWAP_TOPIC: Final = b'\x12\x1c\xb4N\xe5@\x98\xb1\xa0GC\xc4\x87\xe7F\r\x8d\xd4)\xb2\x7f\x88\xb1\xf4\xd4vs\x96\xe1\xa5\x9fy'  # noqa: E501

QUICKSWAP_NFT_MANAGER_V4_ABI: Final[ABI] = [{'inputs': [{'name': 'tokenId', 'type': 'uint256'}], 'name': 'positions', 'outputs': [{'name': 'nonce', 'type': 'uint88'}, {'name': 'operator', 'type': 'address'}, {'name': 'token0', 'type': 'address'}, {'name': 'token1', 'type': 'address'}, {'name': 'deployer', 'type': 'address'}, {'name': 'tickLower', 'type': 'int24'}, {'name': 'tickUpper', 'type': 'int24'}, {'name': 'liquidity', 'type': 'uint128'}, {'name': 'feeGrowthInside0LastX128', 'type': 'uint256'}, {'name': 'feeGrowthInside1LastX128', 'type': 'uint256'}, {'name': 'tokensOwed0', 'type': 'uint128'}, {'name': 'tokensOwed1', 'type': 'uint128'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501

CPT_QUICKSWAP_V4_ROUTER: Final = 'quickswap-v4-router'
