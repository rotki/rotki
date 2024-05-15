from typing import Final
from rotkehlchen.chain.evm.types import string_to_evm_address

GRAPH_L1_LOCK_TRANSFER_TOOL: Final = string_to_evm_address('0xCa82c7Ce3388b0B5d307574099aC57d7a00d509F')  # noqa: E501
CONTRACT_STAKING: Final = string_to_evm_address('0xF55041E37E12cD407ad00CE2910B8269B01263b9')
DELEGATION_TRANSFERRED_TO_L2: Final = b'#\x1e\\\xfe\xffwY\xa4h$\x1d\x93\x9a\xb0J`\xd6\x03\xb1~5\x90W\xab\xbb\x8fR\xaf\xc3\xe4\x98k'  # noqa: E501
TOKEN_DESTINATIONS_APPROVED: Final = b"\xb87\xfdQPk\xa3\xccb:7\xc7\x8e\xd2/\xd5!\xf2\xf6\xe9\xf6\x9a4\xd5\xc2\xa4\xa9GO'W\x93"  # noqa: E501

# Method signatures on the vested contract
APPROVE_PROTOCOL: Final = b'*bx\x14'
