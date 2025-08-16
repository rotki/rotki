from typing import Final

from eth_typing import ABI

from rotkehlchen.types import ChainID

CPT_STAKEDAO: Final = 'stakedao'

CLAIMED_WITH_BOUNTY: Final = b'o\x9c\x98&\xbeYv\xf3\xf8*4\x90\xc5*\x832\x8c\xe2\xec{\xe9\xe6-\xcb9\xc2m\xa5\x14\x8d|v'  # noqa: E501
REWARDS_CLAIMED_TOPIC: Final = b'j\xa3w*l6\x03\x99\xa9J=\xa6$\x8e~\x99\xe0)\xbc\xe1\xa1\xf5|{\x90\xb2\xbf\xa3\xc1\xaa\x7f5'  # noqa: E501
CLAIMED_WITH_BRIBE: Final = b'\xd7\x95\x91St\x02K\xe1\xf02\x04\xe0R\xbdXK3\xbb\x85\xc9\x12\x8e\xde\x9cT\xad\xbe\x0b\xbd\xc2 \x95'  # noqa: E501

STAKEDAO_GAUGE_ABI: Final[ABI] = [{'stateMutability': 'view', 'type': 'function', 'name': 'vault', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}]  # noqa: E501
STAKEDAO_VAULT_ABI: Final[ABI] = [{'inputs': [], 'name': 'token', 'outputs': [{'name': '_token', 'type': 'address'}], 'stateMutability': 'pure', 'type': 'function'}]  # noqa: E501

STAKEDAO_SUPPORTED_CHAINS_WITHOUT_CLAIMS = (ChainID.BASE, ChainID.BINANCE_SC, ChainID.POLYGON_POS)
