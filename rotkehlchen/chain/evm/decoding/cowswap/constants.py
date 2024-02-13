from typing import Final

from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails

CPT_COWSWAP: Final = 'cowswap'
COWSWAP_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_COWSWAP,
    label='Cowswap',
    image='cowswap.jpg',
)
