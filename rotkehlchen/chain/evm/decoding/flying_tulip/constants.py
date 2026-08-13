from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails

CPT_FLYING_TULIP: Final = 'flying-tulip'
FLYING_TULIP_LABEL: Final = 'Flying Tulip'
FLYING_TULIP_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_FLYING_TULIP,
    label=FLYING_TULIP_LABEL,
    image='flying_tulip.svg',
)
