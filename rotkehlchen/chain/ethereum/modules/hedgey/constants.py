from typing import Final

from eth_typing.abi import ABI

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_HEDGEY: Final = 'hedgey'
VOTING_TOKEN_LOCKUPS: Final = string_to_evm_address('0x73cD8626b3cD47B009E68380720CFE6679A3Ec3D')

# partial ABI of only the used functions atm
VOTING_TOKEN_LOCKUPS_ABI: Final[ABI] = [{'inputs': [{'name': 'holder', 'type': 'address'}, {'name': 'token', 'type': 'address'}], 'name': 'lockedBalances', 'outputs': [{'name': 'lockedBalance', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}, {'inputs': [{'name': 'tokenId', 'type': 'uint256'}], 'name': 'ownerOf', 'outputs': [{'name': '', 'type': 'address'}], 'type': 'function'}, {'inputs': [{'name': 'planIds', 'type': 'uint256[]'}, {'name': 'delegatees', 'type': 'address[]'}], 'name': 'delegatePlans', 'outputs': [], 'stateMutability': 'nonpayable', 'type': 'function'}, {'inputs': [{'name': '', 'type': 'uint256'}], 'name': 'plans', 'outputs': [{'name': 'token', 'type': 'address'}, {'name': 'amount', 'type': 'uint256'}, {'name': 'start', 'type': 'uint256'}, {'name': 'cliff', 'type': 'uint256'}, {'name': 'rate', 'type': 'uint256'}, {'name': 'period', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa:E501
