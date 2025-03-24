from typing import Final

from eth_typing import ABI

from rotkehlchen.chain.evm.types import string_to_evm_address

CRVUSD_MINTER: Final = string_to_evm_address('0xC9332fdCB1C491Dcc683bAe86Fe3cb70360738BC')
CRVUSD_MINTER_ABI: Final[ABI] = [{'stateMutability': 'view', 'type': 'function', 'name': 'controllers', 'inputs': [{'name': 'arg0', 'type': 'uint256'}], 'outputs': [{'name': '', 'type': 'address'}]}, {'stateMutability': 'view', 'type': 'function', 'name': 'n_collaterals', 'inputs': [], 'outputs': [{'name': '', 'type': 'uint256'}]}]  # noqa: E501
CURVE_CRVUSD_CONTROLLER_ABI: Final[ABI] = [{'stateMutability': 'view', 'type': 'function', 'name': 'amm', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}, {'stateMutability': 'view', 'type': 'function', 'name': 'collateral_token', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}]  # noqa: E501
