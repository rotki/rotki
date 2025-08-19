from typing import Final

from eth_typing.abi import ABI

from rotkehlchen.chain.evm.decoding.uniswap.constants import CPT_UNISWAP_V4

V4_SWAP_TOPIC: Final = b'@\xe9\xce\xcb\x9f_\x1f\x1c[\x9c\x97\xde\xc2\x91{~\xe9.W\xbaUcp\x8d\xac\xa9M\xd8J\xd7\x11/'  # noqa: E501
MODIFY_LIQUIDITY: Final = b"\xf2\x08\xf4\x91'\x82\xfd%\xc7\xf1\x14\xca7#\xa2\xd5\xddo;\xcc:\xc8\xdbZ\xf6;\xaa\x85\xf7\x11\xd5\xec"  # noqa: E501

POSITION_MANAGER_ABI: Final[ABI] = [{'inputs': [{'name': 'poolId', 'type': 'bytes25'}], 'name': 'poolKeys', 'outputs': [{'name': 'currency0', 'type': 'address'}, {'name': 'currency1', 'type': 'address'}, {'name': 'fee', 'type': 'uint24'}, {'name': 'tickSpacing', 'type': 'int24'}, {'name': 'hooks', 'type': 'address'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501

# Counterparty used exclusively for triggering a separate post decoding rule
# for LP deposit/withdrawals versus for swaps.
CPT_UNISWAP_V4_LP: Final = f'{CPT_UNISWAP_V4}-LP'
