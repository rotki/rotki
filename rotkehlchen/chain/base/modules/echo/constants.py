from typing import Final

from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_ECHO: Final = 'echo'
ECHO_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_ECHO,
    label='Echo',
    image='echo.png',
)

FUNDING_CONDUIT: Final = string_to_evm_address('0x29BEa561cb302FD2B85F5c0c6086BE8b1560F2df')

FEE_PAID: Final = b'jA\xf8k*\x18\xfe\x00\xe1\n\x9b\xd0x\xe7\x90\xae\x82\xc2bzo\x94\x01f\xbd\xdc-\xb4u\x19J_'
DEAL_FUNDED: Final = b'\x15y\xf1\x84ev\x11\x08z\x97\x17\xd1\x97\xffC\xf5\x8b\xadv,\x12\xa6\xcb\x07\xaa\xd8\xd8\rP\xe2C\xe1'
DEAL_REFUNDED: Final = b'\x0ei\xf2\xaa\xd75\x1e\x01\xae\x84\x83\n\x1a\xd3\xc6\x01\x84\x82\xe6\xe1\\\xfe\x9aM\rNr\xb7\x82\xfe\xb9z'
