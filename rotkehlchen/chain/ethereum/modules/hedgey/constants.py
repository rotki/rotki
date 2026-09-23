from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from eth_typing.abi import ABI

CPT_HEDGEY: Final = 'hedgey'
TOKEN_VESTING_PLANS: Final = string_to_evm_address('0x2CDE9919e81b20B4B33DD562a48a84b54C48F00C')
VOTING_TOKEN_VESTING_PLANS: Final = string_to_evm_address('0x1bb64AF7FE05fc69c740609267d2AbE3e119Ef82')  # noqa: E501
TOKEN_LOCKUPS: Final = string_to_evm_address('0x1961A23409CA59EEDCA6a99c97E4087DaD752486')
VOTING_TOKEN_LOCKUPS: Final = string_to_evm_address('0x73cD8626b3cD47B009E68380720CFE6679A3Ec3D')
BOUND_TOKEN_LOCKUPS: Final = string_to_evm_address('0xA600EC7Db69DFCD21f19face5B209a55EAb7a7C0')
BOUND_VOTING_TOKEN_LOCKUPS: Final = string_to_evm_address('0xdE8465D44eBfC761Ee3525740E06C916886E1aEB')  # noqa: E501
HEDGEY_PLAN_CONTRACTS: Final = {
    TOKEN_VESTING_PLANS: 'vesting plan',
    VOTING_TOKEN_VESTING_PLANS: 'vesting plan',
    TOKEN_LOCKUPS: 'token lockup',
    VOTING_TOKEN_LOCKUPS: 'token lockup',
    BOUND_TOKEN_LOCKUPS: 'token lockup',
    BOUND_VOTING_TOKEN_LOCKUPS: 'token lockup',
}

# partial ABI of only the used functions atm
VOTING_TOKEN_LOCKUPS_ABI: Final[ABI] = [{'inputs': [{'name': 'holder', 'type': 'address'}, {'name': 'token', 'type': 'address'}], 'name': 'lockedBalances', 'outputs': [{'name': 'lockedBalance', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}, {'inputs': [{'name': 'tokenId', 'type': 'uint256'}], 'name': 'ownerOf', 'outputs': [{'name': '', 'type': 'address'}], 'type': 'function'}, {'inputs': [{'name': 'planIds', 'type': 'uint256[]'}, {'name': 'delegatees', 'type': 'address[]'}], 'name': 'delegatePlans', 'outputs': [], 'stateMutability': 'nonpayable', 'type': 'function'}, {'inputs': [{'name': '', 'type': 'uint256'}], 'name': 'plans', 'outputs': [{'name': 'token', 'type': 'address'}, {'name': 'amount', 'type': 'uint256'}, {'name': 'start', 'type': 'uint256'}, {'name': 'cliff', 'type': 'uint256'}, {'name': 'rate', 'type': 'uint256'}, {'name': 'period', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa:E501
