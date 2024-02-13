from typing import Final
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails


CPT_ENS: Final = 'ens'
ENS_CPT_DETAILS: Final = CounterpartyDetails(identifier=CPT_ENS, label='ens', image='ens.svg')
