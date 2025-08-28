from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

GIVETH_DONATION_CONTRACT_ADDRESS: Final = string_to_evm_address('0x6e349C56F512cB4250276BF36335c8dd618944A1')  # noqa: E501
DONATION_MADE_TOPIC: Final = b'B\x8e\x11\x90\xdf\xef\x99\x7f:\xc8\xdaj\xfa\x80\xe30\xfcx[\xaf\xb1\xfe\xbe\xd9\x10\x95\x98\xbf\xee\xe4^\xc0'  # noqa: E501
