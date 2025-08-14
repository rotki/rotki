from typing import Final

from eth_typing import ABI

CURVE_VAULT_ABI: ABI = [{'stateMutability': 'view', 'type': 'function', 'name': 'pricePerShare', 'inputs': [], 'outputs': [{'name': '', 'type': 'uint256'}]}, {'stateMutability': 'view', 'type': 'function', 'name': 'borrowed_token', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}, {'stateMutability': 'view', 'type': 'function', 'name': 'collateral_token', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}, {'stateMutability': 'view', 'type': 'function', 'name': 'amm', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}, {'stateMutability': 'view', 'type': 'function', 'name': 'controller', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}]  # noqa: E501
CURVE_VAULT_CONTROLLER_ABI: ABI = [{'stateMutability': 'pure', 'type': 'function', 'name': 'collateral_token', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}, {'stateMutability': 'pure', 'type': 'function', 'name': 'borrowed_token', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}, {'stateMutability': 'view', 'type': 'function', 'name': 'user_state', 'inputs': [{'name': 'user', 'type': 'address'}], 'outputs': [{'name': '', 'type': 'uint256[4]'}]}]  # noqa: E501
CURVE_VAULT_GAUGE_WITHDRAW: Final = b'\x88N\xda\xd9\xceo\xa2D\r\x8aT\xcc\x124\x90\xeb\x96\xd2v\x84y\xd4\x9f\xf9\xc76a%\xa9BCd'  # noqa: E501
DEPOSIT_TOPIC: Final = b'\xdc\xbc\x1c\x05$\x0f1\xff:\xd0g\xef\x1e\xe3\\\xe4\x99wbu.:\tR\x84uED\xf4\xc7\t\xd7'  # noqa: E501
WITHDRAW_TOPIC: Final = b'\xfb\xdey} \x1ch\x1b\x91\x05e)\x11\x9e\x0b\x02@|{\xb9jJ,u\xc0\x1f\xc9fr2\xc8\xdb'  # noqa: E501
BORROW_TOPIC: Final = b"\xe1\x97\x9f\xe4\xc3^\x0c\xef4/\xefVh\xe2\xc8\xe7\xa7\xe9\xf5\xd5\xd1\xca\x8f\xee\n\xc6\xc4'\xfaAS\xaf"  # noqa: E501
REPAY_TOPIC: Final = b'w\xc6\x87\x12\'\xe5\xd2\xde\xc8\xda\xddST\xf7\x84S >"\xe6i\xcd\x0e\xc4\xc1\x9d\x9a\x8c^\xdb1\xd0'  # noqa: E501
REMOVE_COLLATERAL_TOPIC: Final = b'\xe2T\x10\xa4\x05\x96\x19\xc9YM\xc6\xf0"\xfe#\x1b\x02\xaa\xeas?h\x9ez\xb0\xcd!\xb3\xd4\xd0\xebT'  # noqa: E501
LEVERAGE_ZAP_DEPOSIT_TOPIC: Final = b'\xf9C\xcf\x10\xefM\x1e29\xf4qm\xde\xcd\xf5F\xe8\xba\x8a\xb0\xe4\x1d\xea\xfd\x9aq\xa9\x996\x82~E'  # noqa: E501
CURVE_LEND_VAULT_SYMBOL: Final = 'cvcrvUSD'
