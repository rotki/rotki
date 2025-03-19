from typing import Final

from eth_typing import ABI

CURVE_VAULT_ABI: ABI = [{'stateMutability': 'view', 'type': 'function', 'name': 'pricePerShare', 'inputs': [], 'outputs': [{'name': '', 'type': 'uint256'}]}, {'stateMutability': 'view', 'type': 'function', 'name': 'borrowed_token', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}, {'stateMutability': 'view', 'type': 'function', 'name': 'collateral_token', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}, {'stateMutability': 'view', 'type': 'function', 'name': 'amm', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}, {'stateMutability': 'view', 'type': 'function', 'name': 'controller', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}]  # noqa: E501
CURVE_VAULT_CONTROLLER_ABI: ABI = [{'stateMutability': 'pure', 'type': 'function', 'name': 'collateral_token', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}, {'stateMutability': 'pure', 'type': 'function', 'name': 'borrowed_token', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}, {'stateMutability': 'view', 'type': 'function', 'name': 'user_state', 'inputs': [{'name': 'user', 'type': 'address'}], 'outputs': [{'name': '', 'type': 'uint256[4]'}]}]  # noqa: E501
CURVE_VAULT_GAUGE_WITHDRAW: Final = b'\x88N\xda\xd9\xceo\xa2D\r\x8aT\xcc\x124\x90\xeb\x96\xd2v\x84y\xd4\x9f\xf9\xc76a%\xa9BCd'  # noqa: E501
