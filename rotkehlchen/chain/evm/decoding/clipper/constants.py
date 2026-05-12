from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails

CPT_CLIPPER: Final = 'clipper'
CLIPPER_LABEL: Final = 'Clipper'
CLIPPER_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_CLIPPER,
    label=CLIPPER_LABEL,
    image='clipper.svg',
)
# Event topic for Swapped(address,address,address,uint256,uint256,bytes).
CLIPPER_SWAPPED_TOPIC: Final = b'K\xe0\\\x8dT\xf5\xe0V\xab,\xfa\x03>\x9fX W\x00\x12h\xc3\xe2\x85a\xbb\x99\x9d5\xd2\xc8\xf2\xc8'  # noqa: E501
