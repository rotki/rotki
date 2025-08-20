from typing import Final

from eth_typing.abi import ABI

from rotkehlchen.chain.evm.decoding.uniswap.constants import CPT_UNISWAP_V4
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID

V4_SWAP_TOPIC: Final = b'@\xe9\xce\xcb\x9f_\x1f\x1c[\x9c\x97\xde\xc2\x91{~\xe9.W\xbaUcp\x8d\xac\xa9M\xd8J\xd7\x11/'  # noqa: E501
MODIFY_LIQUIDITY: Final = b"\xf2\x08\xf4\x91'\x82\xfd%\xc7\xf1\x14\xca7#\xa2\xd5\xddo;\xcc:\xc8\xdbZ\xf6;\xaa\x85\xf7\x11\xd5\xec"  # noqa: E501

POSITION_MANAGER_ABI: Final[ABI] = [{'inputs': [{'name': 'poolId', 'type': 'bytes25'}], 'name': 'poolKeys', 'outputs': [{'name': 'currency0', 'type': 'address'}, {'name': 'currency1', 'type': 'address'}, {'name': 'fee', 'type': 'uint24'}, {'name': 'tickSpacing', 'type': 'int24'}, {'name': 'hooks', 'type': 'address'}], 'stateMutability': 'view', 'type': 'function'}, {'inputs': [{'name': 'tokenId', 'type': 'uint256'}], 'name': 'getPoolAndPositionInfo', 'outputs': [{'components': [{'name': 'currency0', 'type': 'address'}, {'name': 'currency1', 'type': 'address'}, {'name': 'fee', 'type': 'uint24'}, {'name': 'tickSpacing', 'type': 'int24'}, {'name': 'hooks', 'type': 'address'}], 'name': 'poolKey', 'type': 'tuple'}, {'name': 'info', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}, {'inputs': [{'name': 'tokenId', 'type': 'uint256'}], 'name': 'getPositionLiquidity', 'outputs': [{'name': 'liquidity', 'type': 'uint128'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501
STATE_VIEW_ABI: Final[ABI] = [{'inputs': [{'name': 'poolId', 'type': 'bytes32'}], 'name': 'getSlot0', 'outputs': [{'name': 'sqrtPriceX96', 'type': 'uint160'}, {'name': 'tick', 'type': 'int24'}, {'name': 'protocolFee', 'type': 'uint24'}, {'name': 'lpFee', 'type': 'uint24'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501

# Counterparty used exclusively for triggering a separate post decoding rule
# for LP deposit/withdrawals versus for swaps.
CPT_UNISWAP_V4_LP: Final = f'{CPT_UNISWAP_V4}-LP'

UNISWAP_V4_STATE_VIEW_CONTRACTS: Final = {
    ChainID.ETHEREUM: string_to_evm_address('0x7fFE42C4a5DEeA5b0feC41C94C136Cf115597227'),
    ChainID.OPTIMISM: string_to_evm_address('0xc18a3169788F4F75A170290584ECA6395C75Ecdb'),
    ChainID.BASE: string_to_evm_address('0xA3c0c9b65baD0b08107Aa264b0f3dB444b867A71'),
    ChainID.ARBITRUM_ONE: string_to_evm_address('0x76Fd297e2D437cd7f76d50F01AfE6160f86e9990'),
    ChainID.POLYGON_POS: string_to_evm_address('0x5eA1bD7974c8A611cBAB0bDCAFcB1D9CC9b3BA5a'),
    ChainID.BINANCE_SC: string_to_evm_address('0xd13Dd3D6E93f276FAfc9Db9E6BB47C1180aeE0c4'),
}  # See https://docs.uniswap.org/contracts/v4/deployments
