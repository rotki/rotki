from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.types import ChainID

CPT_COWSWAP: Final = 'cowswap'
COWSWAP_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_COWSWAP,
    label='Cowswap',
    image='cowswap.jpg',
)
COWSWAP_SUPPORTED_CHAINS_WITHOUT_VCOW: Final = {
    ChainID.ARBITRUM_ONE,
    ChainID.BASE,
    ChainID.BINANCE_SC,
    ChainID.POLYGON_POS,
}
