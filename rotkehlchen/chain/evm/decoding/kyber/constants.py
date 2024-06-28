from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_KYBER: Final = 'kyber'
KYBER_CPT_DETAILS: Final = {'label': 'Kyber', 'image': 'kyber.svg'}
KYBER_AGGREGATOR_CONTRACT: Final = string_to_evm_address('0x6131B5fae19EA4f9D964eAc0408E4408b66337b5')  # noqa: E501
KYBER_AGGREGATOR_SWAPPED: Final = b'\xd6\xd4\xf5h\x1c$l\x9fB\xc2\x03\xe2\x87\x97Z\xf1`\x1f\x8d\xf8\x03Z\x92Q\xf7\x9a\xab\\\x8f\t\xe2\xf8'  # noqa: E501
