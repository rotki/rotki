from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_KYBER: Final = 'kyber'
KYBER_CPT_DETAILS: Final = {'label': 'Kyber', 'image': 'kyber.svg'}
KYBER_AGGREGATOR_CONTRACT: Final = string_to_evm_address('0x6131B5fae19EA4f9D964eAc0408E4408b66337b5')  # noqa: E501
ENSO_ROUTER_V2: Final = string_to_evm_address('0xF75584eF6673aD213a685a1B58Cc0330B8eA22Cf')
