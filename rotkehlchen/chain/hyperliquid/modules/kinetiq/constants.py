from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_KINETIQ: Final = 'kinetiq'
KINETIQ_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_KINETIQ,
    label='Kinetiq',
    image='kinetiq.svg',
    darkmode_image='kinetiq_dark.svg',
)
KINETIQ_STAKING_MANAGER: Final = string_to_evm_address('0x393D0B87Ed38fc779FD9611144aE649BA6082109')  # noqa: E501
KHYPE_TOKEN_ID: Final = 'eip155:999/erc20:0xfD739d4e423301CE9385c1fb8850539D657C296D'

STAKE_RECEIVED_TOPIC: Final = b'\xf4\x03S\xee\x0e\x00\xd0\x04\xd0Z\xf8\\b\x1c\xb1\x7f\x88H]$Fc\xa0\xb1\x00\xa1LvZ>\x86\xf7'  # noqa: E501
WITHDRAWAL_QUEUED_TOPIC: Final = b'\xbf\x9e\x91|\x1f\x92\xe3\x1f\xa4[)\x7f\x9a\x8c"\x99:V\x04x\xbb\xb7e\xb3\xfcC\r\x7f\xa6.\x08<'  # noqa: E501
WITHDRAWAL_CONFIRMED_TOPIC: Final = b"z\t\x91`\x98i\x16TkV\xe2\x8a _\xfdlF\xad\xbe\xdd';\xea\xc7(\xfc\x0eo\xaf-\xfbL"  # noqa: E501
INSTANT_UNSTAKE_EXECUTED_TOPIC: Final = b'\x17\x01\x9b;\xe6=\xd0\xe3\xa8\xa8\xf0\x82\xd3\x12\xa7\xd0\xc3\xfe\xdf\x98\x99"P\xf3\x9d\xcc\xb0\xf8\x02\tlW'  # noqa: E501
REDELEGATION_REQUESTED_TOPIC: Final = b'\xa0V-\xa8\xc9}\x80\x11\xe7i\rb\xb3\xf0\xaf\xed\x08\x8f\xa6\x1ce(\x8dkj\xb6\xc0-@\xd8\x05\x1a'  # noqa: E501
