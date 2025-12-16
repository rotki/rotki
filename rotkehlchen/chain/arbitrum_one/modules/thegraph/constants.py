from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from eth_typing import ABI

CONTRACT_STAKING: Final = string_to_evm_address('0x00669A4CF01450B64E8A2A20E9b1FCB71E61eF03')
# Default verifier address (subgraph data service) for pre-Horizon delegations
# https://github.com/graphprotocol/contracts/blob/b91017dc1e3492d768d0df377a27f4b15606950e/packages/horizon/contracts/staking/HorizonStakingBase.sol#L259-L268
SUBGRAPH_DATA_SERVICE_ADDRESS: Final = string_to_evm_address('0xb2Bb92d0DE618878E438b55D5846cfecD9301105')  # noqa: E501
HORIZON_STAKING_ABI: Final['ABI'] = [{'inputs': [{'name': 'serviceProvider', 'type': 'address'}, {'name': 'verifier', 'type': 'address'}, {'name': 'delegator', 'type': 'address'}], 'name': 'getDelegation', 'outputs': [{'components': [{'name': 'shares', 'type': 'uint256'}], 'name': '', 'type': 'tuple'}], 'stateMutability': 'view', 'type': 'function'}, {'inputs': [{'name': 'serviceProvider', 'type': 'address'}, {'name': 'verifier', 'type': 'address'}], 'name': 'getDelegationPool', 'outputs': [{'components': [{'name': 'tokens', 'type': 'uint256'}, {'name': 'shares', 'type': 'uint256'}, {'name': 'tokensThawing', 'type': 'uint256'}, {'name': 'sharesThawing', 'type': 'uint256'}, {'name': 'thawingNonce', 'type': 'uint256'}], 'name': '', 'type': 'tuple'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501
