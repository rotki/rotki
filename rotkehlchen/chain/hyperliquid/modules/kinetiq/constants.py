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
# All deployments run the same StakingManager contract. Besides the flagship kHYPE one
# there are the institutional partner deployments, each minting its own LST token.
KINETIQ_STAKING_MANAGERS: Final = {
    KINETIQ_STAKING_MANAGER: KHYPE_TOKEN_ID,
    string_to_evm_address('0xfdd35c5179E8594E237031dd945E0584Af29572b'): 'eip155:999/erc20:0x86d96fF0E78Dba9570b00f75807ce21213a19f3d',  # Flowdesk flowHYPE  # noqa: E501
    string_to_evm_address('0xaD492f9CADcccE9c3c213edd8aE55c152cD3A3ad'): 'eip155:999/erc20:0x4f322145aBedb2b39f69e7d4531AB4B2e6483154',  # Hyperion HiHYPE  # noqa: E501
    string_to_evm_address('0x0c5d890Cf52973aE4A7b10fA7EE18e146d13D87B'): 'eip155:999/erc20:0x8599F2eFA5064C666B920E71381b5aaBc7Bb27F6',  # ASXN asxnHYPE  # noqa: E501
    string_to_evm_address('0x09B4cdA849037D1717e91D201EE416bf1c113895'): 'eip155:999/erc20:0x498edC41Fa92530920a95483dea7a6CCe91F1C5c',  # HYLQ hylqHYPE  # noqa: E501
}

STAKE_RECEIVED_TOPIC: Final = b'\xf4\x03S\xee\x0e\x00\xd0\x04\xd0Z\xf8\\b\x1c\xb1\x7f\x88H]$Fc\xa0\xb1\x00\xa1LvZ>\x86\xf7'  # noqa: E501
WITHDRAWAL_QUEUED_TOPIC: Final = b'\xbf\x9e\x91|\x1f\x92\xe3\x1f\xa4[)\x7f\x9a\x8c"\x99:V\x04x\xbb\xb7e\xb3\xfcC\r\x7f\xa6.\x08<'  # noqa: E501
WITHDRAWAL_CONFIRMED_TOPIC: Final = b"z\t\x91`\x98i\x16TkV\xe2\x8a _\xfdlF\xad\xbe\xdd';\xea\xc7(\xfc\x0eo\xaf-\xfbL"  # noqa: E501
INSTANT_UNSTAKE_EXECUTED_TOPIC: Final = b'\x17\x01\x9b;\xe6=\xd0\xe3\xa8\xa8\xf0\x82\xd3\x12\xa7\xd0\xc3\xfe\xdf\x98\x99"P\xf3\x9d\xcc\xb0\xf8\x02\tlW'  # noqa: E501
REDELEGATION_REQUESTED_TOPIC: Final = b'\xa0V-\xa8\xc9}\x80\x11\xe7i\rb\xb3\xf0\xaf\xed\x08\x8f\xa6\x1ce(\x8dkj\xb6\xc0-@\xd8\x05\x1a'  # noqa: E501
