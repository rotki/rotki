from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID

CPT_ETHERFI: Final = 'etherfi'
ETHERFI_COUNTERPARTY_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_ETHERFI,
    label='ether.fi',
    image='etherfi.png',
)

# The ether.fi Cash event emitter has the same address on every chain the card has lived on
ETHERFI_CASH_EVENT_EMITTER: Final = string_to_evm_address('0x380B2e96799405be6e3D965f4044099891881acB')  # noqa: E501
ETHERFI_CASH_CHAINS: Final = {ChainID.SCROLL, ChainID.OPTIMISM}

CASHBACK: Final = b'\x89\xd3W\x1aI\x8b]=hY\x9f_\x00\xc3\x01o\x96\x04\xaa\xfaw\x01\xc5,\x1b\x04\x10\x9c\xd9\t\xa7\x98'  # noqa: E501
