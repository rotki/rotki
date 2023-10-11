from typing import Final
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails

CPT_THEGRAPH: Final = 'thegraph'

THEGRAPH_CPT_DETAILS = CounterpartyDetails(
    identifier=CPT_THEGRAPH,
    label='The Graph',
    image='thegraph.svg',
)

CONTRACT_STAKING = '0xF55041E37E12cD407ad00CE2910B8269B01263b9'
