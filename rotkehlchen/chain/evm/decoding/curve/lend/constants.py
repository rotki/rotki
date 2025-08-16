from typing import Final

from eth_typing import ABI

CURVE_VAULT_ABI: ABI = [{'stateMutability': 'view', 'type': 'function', 'name': 'pricePerShare', 'inputs': [], 'outputs': [{'name': '', 'type': 'uint256'}]}, {'stateMutability': 'view', 'type': 'function', 'name': 'borrowed_token', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}, {'stateMutability': 'view', 'type': 'function', 'name': 'collateral_token', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}, {'stateMutability': 'view', 'type': 'function', 'name': 'amm', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}, {'stateMutability': 'view', 'type': 'function', 'name': 'controller', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}]  # noqa: E501
CURVE_VAULT_CONTROLLER_ABI: ABI = [{'stateMutability': 'pure', 'type': 'function', 'name': 'collateral_token', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}, {'stateMutability': 'pure', 'type': 'function', 'name': 'borrowed_token', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}, {'stateMutability': 'view', 'type': 'function', 'name': 'user_state', 'inputs': [{'name': 'user', 'type': 'address'}], 'outputs': [{'name': '', 'type': 'uint256[4]'}]}]  # noqa: E501
BORROW_TOPIC: Final = b"\xe1\x97\x9f\xe4\xc3^\x0c\xef4/\xefVh\xe2\xc8\xe7\xa7\xe9\xf5\xd5\xd1\xca\x8f\xee\n\xc6\xc4'\xfaAS\xaf"  # noqa: E501
REPAY_TOPIC: Final = b'w\xc6\x87\x12\'\xe5\xd2\xde\xc8\xda\xddST\xf7\x84S >"\xe6i\xcd\x0e\xc4\xc1\x9d\x9a\x8c^\xdb1\xd0'  # noqa: E501
REMOVE_COLLATERAL_TOPIC: Final = b'\xe2T\x10\xa4\x05\x96\x19\xc9YM\xc6\xf0"\xfe#\x1b\x02\xaa\xeas?h\x9ez\xb0\xcd!\xb3\xd4\xd0\xebT'  # noqa: E501
CURVE_LEND_VAULT_SYMBOL: Final = 'cvcrvUSD'
