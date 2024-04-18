from typing import Final
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails

CPT_THEGRAPH: Final = 'thegraph'
THEGRAPH_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_THEGRAPH,
    label='The Graph',
    image='thegraph.svg',
)
