from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_MINTCLUB: Final = 'mintclub'
MINTCLUB_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_MINTCLUB,
    label='MintClub',
    image='mintclub.svg',
    darkmode_image='mintclub-dark.svg',
)
MINTCLUB_DISTRIBUTOR_ADDRESS: Final = string_to_evm_address('0x1349A9DdEe26Fe16D0D44E35B3CB9B0CA18213a4')  # noqa: E501
MINTCLUB_CLAIMED_TOPIC: Final = b'j\xa3\xea\xc9=\x07\x9e^\x10\x0b\x10)\xbeql\xaa3Xl\x96\xaaK\xaa\xc3\x90f\x9f\xb5\xc2\xa2\x12\x12'  # noqa: E501
