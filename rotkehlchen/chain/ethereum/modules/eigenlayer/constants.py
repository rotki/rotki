from typing import Final

from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_EIGENLAYER: Final = 'eigenlayer'
EIGENPOD_MANAGER: Final = string_to_evm_address('0x91E677b07F7AF907ec9a428aafA9fc14a0d3A338')
EIGENPOD_DELAYED_WITHDRAWAL_ROUTER: Final = string_to_evm_address('0x7Fe7E9CC0F274d2435AD5d56D5fa73E47F6A23D8')  # noqa: E501
EIGENLAYER_STRATEGY_MANAGER: Final = string_to_evm_address('0x858646372CC42E1A627fcE94aa7A7033e7CF075A')  # noqa: E501
EIGENLAYER_AIRDROP_DISTRIBUTOR: Final = string_to_evm_address('0x035bdAeaB85E47710C27EdA7FD754bA80aD4ad02')  # noqa: E501
EIGENLAYER_DELEGATION: Final = string_to_evm_address('0x39053D51B77DC0d36036Fc1fCc8Cb819df8Ef37A')
DEPOSIT_TOPIC: Final = b'|\xff\xf9\x08\xa4\xb5\x83\xf3d0\xb2]u\x96LE\x8d\x8e\xde\x8a\x99\xbda\xbeu\x0e\x97\xee\x1b/:\x96'  # noqa: E501
WITHDRAWAL_COMPLETE_TOPIC: Final = b"\xe7\xeb\x0c\xa1\x1b\x83tN\xce=x\xe9\xbe\x01\xb9\x13B_\xba\xe7\x0c2\xce'rm\x0e\xcd\xe9.\xf8\xd2"  # noqa: E501
POD_DEPLOYED: Final = b'!\xc9\x9d\r\xb0"\x13\xc3/\xff[\x05\xcf\nq\x8a\xb5\xf8X\x80+\x91I\x8f\x80\xd8"p(\x9d\x85j'  # noqa: E501
DELAYED_WITHDRAWALS_CREATED: Final = b'\xb8\xf1\xb1L|\xaft\x15\x08\x01\xdc\xc9\xbc\x18\xd5u\xcb\xea\xf5\xb4!\x944\x97\xe4\t\xdf\x92\xc9.\x0fY'  # noqa: E501
DELAYED_WITHDRAWALS_CLAIMED: Final = b'kqQP\x0b\xd0\xb5\xcc!\x1b\xccG\xb3\x02\x981\xb7i\x00M\xf4T\x9e\x8e\x1c\x9ai\xda\x05\xbb\tC'  # noqa: E501
PARTIAL_WITHDRAWAL_REDEEMED: Final = b'\x8as5qB1\xdb\xd5Q\xaa\xbac\x14\xf4\xa9z\x14\xc2\x01\xe5:>%\xe1\x14\x03%\xcd\xf6}zN'  # noqa: E501
FULL_WITHDRAWAL_REDEEMED: Final = b'\xb7j\x93\xbbd\x9e\xceRF\x88\xf1\xa0\x1d\x18N\x0b\xbe\xbc\xdaX\xea\xe8\x0c(\xa8\x98\xbe\xc3\xfbZ\tc'  # noqa: E501
OPERATOR_SHARES_INCREASED: Final = b'\x1e\xc0B\xc9e\xe2\xed\xd7\x10{Q\x18\x8e\xe0\xf3\x83\xe2.v\x17\x90A\xab:\x9d\x18\xff\x15\x14\x05\x16l'  # noqa: E501
POD_SHARES_UPDATED: Final = b'N+y\x1d\xed\xcc\xd9\xfb0\x14\x1b\x08\x8c\xab\xf5\xc1J\x89\x12\xb5/Y7\\\x95\xc0\x10p\x0b\x8ca\x93'  # noqa: E501
EIGENLAYER_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_EIGENLAYER,
    label='EigenLayer',
    image='eigenlayer.png',
)
EIGEN_TOKEN_ID: Final = 'eip155:1/erc20:0xec53bF9167f50cDEB3Ae105f56099aaaB9061F83'

# not the full ABI, just the one function we call
EIGENPOD_DELAYED_WITHDRAWAL_ROUTER_ABI: Final = [{'inputs': [{'internalType': 'address', 'name': 'user', 'type': 'address'}], 'name': 'getUserDelayedWithdrawals', 'outputs': [{'components': [{'internalType': 'uint224', 'name': 'amount', 'type': 'uint224'}, {'internalType': 'uint32', 'name': 'blockCreated', 'type': 'uint32'}], 'internalType': 'struct IDelayedWithdrawalRouter.DelayedWithdrawal[]', 'name': '', 'type': 'tuple[]'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501
