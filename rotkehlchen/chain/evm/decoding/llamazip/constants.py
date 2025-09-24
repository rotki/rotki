from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails

CPT_LLAMAZIP: Final = 'llamazip'
LLAMAZIP_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_LLAMAZIP,
    label='LlamaZip',
    image='llamazip.png',
)
