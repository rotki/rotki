from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails

CPT_GIVETH: Final = 'giveth'
CPT_DETAILS_GIVETH: Final = CounterpartyDetails(
    identifier=CPT_GIVETH,
    label='Giveth',
    image='giveth.jpg',
)

TOKEN_LOCKED: Final = b'yG{\x88\xdey~\x163\xf0\xb8\xb1\xd9p\xd4\xdfu\xbdK%\x84y}\xef\x16\x1f)\xabf}:w'  # noqa: E501
