from typing import Final

from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address

GNOSIS_PAY_CASHBACK_ADDRESS: Final = string_to_evm_address('0xCdF50be9061086e2eCfE6e4a1BF9164d43568EEC')  # noqa: E501

CPT_GNOSIS_PAY: Final = 'gnosis pay'
GNOSIS_PAY_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_GNOSIS_PAY,
    label='Gnosis Pay',
    image='gnosis_pay.png',
)
