from typing import Final
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address


CPT_EIGENLAYER: Final = 'eigenlayer'
EIGENLAYER_STRATEGY_MANAGER: Final = string_to_evm_address('0x858646372CC42E1A627fcE94aa7A7033e7CF075A')  # noqa: E501
EIGENLAYER_AIRDROP_DISTRIBUTOR: Final = string_to_evm_address('0x035bdAeaB85E47710C27EdA7FD754bA80aD4ad02')  # noqa: E501
DEPOSIT_TOPIC: Final = b'|\xff\xf9\x08\xa4\xb5\x83\xf3d0\xb2]u\x96LE\x8d\x8e\xde\x8a\x99\xbda\xbeu\x0e\x97\xee\x1b/:\x96'  # noqa: E501
WITHDRAWAL_COMPLETE_TOPIC: Final = b"\xe7\xeb\x0c\xa1\x1b\x83tN\xce=x\xe9\xbe\x01\xb9\x13B_\xba\xe7\x0c2\xce'rm\x0e\xcd\xe9.\xf8\xd2"  # noqa: E501
EIGENLAYER_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_EIGENLAYER,
    label='EigenLayer',
    image='eigenlayer.png',
)
EIGEN_TOKEN_ID: Final = 'eip155:1/erc20:0xec53bF9167f50cDEB3Ae105f56099aaaB9061F83'
