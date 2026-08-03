from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from eth_typing.abi import ABI

CPT_PROJECT_X: Final = 'project-x'
PROJECT_X_NFT_MANAGER: Final = string_to_evm_address('0xeaD19AE861c29bBb2101E834922B2FEee69B9091')
PROJECT_X_SWAP_ROUTER: Final = string_to_evm_address('0x1EbDFC75FfE3ba3de61E7138a3E8706aC841Af9B')

PROJECT_X_NFT_MANAGER_ABI: Final[ABI] = [{
    'inputs': [{'name': 'tokenId', 'type': 'uint256'}],
    'name': 'positions',
    'outputs': [
        {'name': 'nonce', 'type': 'uint96'},
        {'name': 'operator', 'type': 'address'},
        {'name': 'token0', 'type': 'address'},
        {'name': 'token1', 'type': 'address'},
        {'name': 'fee', 'type': 'uint24'},
        {'name': 'tickLower', 'type': 'int24'},
        {'name': 'tickUpper', 'type': 'int24'},
        {'name': 'liquidity', 'type': 'uint128'},
        {'name': 'feeGrowthInside0LastX128', 'type': 'uint256'},
        {'name': 'feeGrowthInside1LastX128', 'type': 'uint256'},
        {'name': 'tokensOwed0', 'type': 'uint128'},
        {'name': 'tokensOwed1', 'type': 'uint128'},
    ],
    'stateMutability': 'view',
    'type': 'function',
}]
