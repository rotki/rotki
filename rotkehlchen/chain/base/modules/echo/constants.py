from typing import Final

from eth_typing.abi import ABI

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_ECHO: Final = 'echo'
ECHO_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_ECHO,
    label='Echo',
    image='echo.png',
)

FUNDING_CONDUIT: Final = string_to_evm_address('0x29BEa561cb302FD2B85F5c0c6086BE8b1560F2df')
FUNDER_REGISTRY: Final = string_to_evm_address('0xbe1b65519d6B6C86Ab5B9f3B2BFF7Db9846D899F')

FEE_PAID: Final = b'jA\xf8k*\x18\xfe\x00\xe1\n\x9b\xd0x\xe7\x90\xae\x82\xc2bzo\x94\x01f\xbd\xdc-\xb4u\x19J_'  # noqa: E501
DEAL_FUNDED: Final = b'\x15y\xf1\x84ev\x11\x08z\x97\x17\xd1\x97\xffC\xf5\x8b\xadv,\x12\xa6\xcb\x07\xaa\xd8\xd8\rP\xe2C\xe1'  # noqa: E501
FUNDER_DEREGISTERED: Final = b"\xa490\xe8\xb1\x02B\xcc\xa4\xf6\x03\xdej\xf6\xed\x9e\xb00}'s\x0c\x11\xb3\xb5\xbe@)\x06'\x04k"  # noqa: E501
POOL_REFUNDED: Final = b'1\xdf\x08\xdd\x1d\xb7%\xa8Hu3f\x8e\xee\xb1\xd8<\xa4\xb4WP\xe8\xed\xf5o\xa1\x03!\x14X\x9e\xa5'  # noqa: E501

DEAL_ABI: Final[ABI] = [{
    'inputs': [],
    'name': 'token',
    'outputs': [
        {
            'name': '',
            'type': 'address',
        },
    ],
    'stateMutability': 'view',
    'type': 'function',
}]
