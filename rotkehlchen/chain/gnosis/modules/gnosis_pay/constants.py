from typing import Final

from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address

GNOSIS_PAY_CASHBACK_ADDRESS: Final = string_to_evm_address('0xCdF50be9061086e2eCfE6e4a1BF9164d43568EEC')  # noqa: E501
GNOSIS_PAY_SPENDER_ADDRESS: Final = string_to_evm_address('0xcFF260bfbc199dC82717494299b1AcADe25F549b')  # noqa: E501

SPEND: Final = b'\xca\x8f\xbb\x9b\xda\x99\x84\x8fDyq\xea\xe6*\xd0\xad+\xc7\xca\xf9\xaf\xcc\r\x8eN\x8f\xfc\xf7\xe0k\xc2\x8f'  # noqa: E501

CPT_GNOSIS_PAY: Final = 'gnosis pay'
GNOSIS_PAY_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_GNOSIS_PAY,
    label='Gnosis Pay',
    image='gnosis_pay.png',
)
