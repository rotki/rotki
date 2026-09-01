from typing import Final

from rotkehlchen.types import SolanaAddress

CCTP_TOKEN_MESSENGER_V2: Final = SolanaAddress(
    'CCTPV2vPZJS2u2BBsUoscuikbYjnpFmbFsvVuJdgUMQe',
)
CCTP_MESSAGE_TRANSMITTER_V2: Final = SolanaAddress(
    'CCTPV2Sm4AdWt5296sk4P66VBZ7bEhcARwFaaS9YPbeC',
)
DEPOSIT_FOR_BURN_DISCRIMINATOR: Final = b'\xd7<=.r7\x80\xb0'
RECEIVE_MESSAGE_DISCRIMINATOR: Final = b'&\x90\x7f\xe1\x1f\xe1\xee\x19'
