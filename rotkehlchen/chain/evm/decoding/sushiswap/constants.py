from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

SUSHISWAP_ICON: Final = 'sushiswap.svg'

# RedSnwapper (RP5/RP6) - deployed at the same address on all EVM chains
# https://docs.sushi.com/contracts/red-snwapper
REDSNWAP_ADDRESS: Final = string_to_evm_address('0xAC4c6e212A361c968F1725b4d055b47E63F80b75')
REDSNWAP_ROUTE_PROCESSOR_TOPIC: Final = b'\x84\xb5\x14\xc5\xb9&\x87\x9b\xf6j\x04\xe4\xbe\xcd\xc6\xf5!\xe9JD\x11\xe7\xdf\xa3\xdd%_!Dx\xf5X'  # noqa: E501

# Token Chomper - fee collector, same address on all chains
TOKEN_CHOMPER_ADDRESS: Final = string_to_evm_address('0xde7259893Af7cdbC9fD806c6ba61D22D581d5667')

# Route event topic used by older Route Processors (RP3/RP3.2/RP4)
ROUTE_PROCESSOR_TOPIC: Final = b'-\xb5\xdd\xd0\xb4+\xdb\xca\ri\xea\x16\xf24\xa8p\xa4\x85\x85J\xe0\xd9\x1f\x16d=o1}\x8b\x89\x94'  # noqa: E501
