from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address

BASENAMES_L2_RESOLVER: Final = string_to_evm_address('0xC6d566A56A1aFf6508b41f6c90ff131615583BCD')
BASENAMES_REGISTRAR_CONTROLLER: Final = string_to_evm_address('0x4cCb0BB02FCABA27e82a56646E81d8c5bC4119a5')  # noqa: E501
BASENAMES_REGISTRY: Final = string_to_evm_address('0xB94704422c2a1E396835A571837Aa5AE53285a95')
BASENAMES_BASE_REGISTRAR: Final = string_to_evm_address('0x03c4738Ee98aE44591e1A4A4F3CaB6641d95DD9a')  # noqa: E501

CPT_BASENAMES: Final = 'basenames'
BASENAMES_CPT_DETAILS = CounterpartyDetails(
    identifier=CPT_BASENAMES,
    label='Basenames',
    image='base.svg',
)
