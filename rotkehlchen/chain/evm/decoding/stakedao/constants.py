from typing import Final

from eth_typing import ABI

CPT_STAKEDAO: Final = 'stakedao'

STAKEDAO_DEPOSIT: Final = b'\xe1\xff\xfc\xc4\x92=\x04\xb5Y\xf4\xd2\x9a\x8b\xfcl\xda\x04\xeb[\r<F\x07Q\xc2@,\\\\\xc9\x10\x9c'  # noqa: E501
STAKEDAO_WITHDRAW: Final = b'\x88N\xda\xd9\xceo\xa2D\r\x8aT\xcc\x124\x90\xeb\x96\xd2v\x84y\xd4\x9f\xf9\xc76a%\xa9BCd'  # noqa: E501

CLAIMED_WITH_BOUNTY: Final = b'o\x9c\x98&\xbeYv\xf3\xf8*4\x90\xc5*\x832\x8c\xe2\xec{\xe9\xe6-\xcb9\xc2m\xa5\x14\x8d|v'  # noqa: E501
CLAIMED_WITH_BRIBE: Final = b'\xd7\x95\x91St\x02K\xe1\xf02\x04\xe0R\xbdXK3\xbb\x85\xc9\x12\x8e\xde\x9cT\xad\xbe\x0b\xbd\xc2 \x95'  # noqa: E501

STAKEDAO_GAUGE_ABI: Final[ABI] = [{'stateMutability': 'view', 'type': 'function', 'name': 'vault', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}]  # noqa: E501
STAKEDAO_VAULT_ABI: Final[ABI] = [{'inputs': [], 'name': 'token', 'outputs': [{'name': '_token', 'type': 'address'}], 'stateMutability': 'pure', 'type': 'function'}]  # noqa: E501
