from typing import Final

from eth_typing.abi import ABI

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_EIGENLAYER: Final = 'eigenlayer'
EIGENPOD_MANAGER: Final = string_to_evm_address('0x91E677b07F7AF907ec9a428aafA9fc14a0d3A338')
EIGENPOD_DELAYED_WITHDRAWAL_ROUTER: Final = string_to_evm_address('0x7Fe7E9CC0F274d2435AD5d56D5fa73E47F6A23D8')  # noqa: E501
EIGENLAYER_STRATEGY_MANAGER: Final = string_to_evm_address('0x858646372CC42E1A627fcE94aa7A7033e7CF075A')  # noqa: E501
EIGENLAYER_AIRDROP_S1_PHASE1_DISTRIBUTOR: Final = string_to_evm_address('0x035bdAeaB85E47710C27EdA7FD754bA80aD4ad02')  # noqa: E501
EIGENLAYER_AIRDROP_S1_PHASE2_DISTRIBUTOR: Final = string_to_evm_address('0xF532a5A35007804A9cA79E7Fa15D8f648F6D7F28')  # noqa: E501
EIGENLAYER_AIRDROP_S2_DISTRIBUTOR: Final = string_to_evm_address('0xa105C3AbeDBAf4295AC6149BF24D5311F629934c')  # noqa: E501
EIGENLAYER_DELEGATION: Final = string_to_evm_address('0x39053D51B77DC0d36036Fc1fCc8Cb819df8Ef37A')
BEACON_ETH_STRATEGY: Final = string_to_evm_address('0xbeaC0eeEeeeeEEeEeEEEEeeEEeEeeeEeeEEBEaC0')
REWARDS_COORDINATOR: Final = string_to_evm_address('0x7750d328b314EfFa365A0402CcfD489B80B0adda')
DEPOSIT_TOPIC: Final = b'|\xff\xf9\x08\xa4\xb5\x83\xf3d0\xb2]u\x96LE\x8d\x8e\xde\x8a\x99\xbda\xbeu\x0e\x97\xee\x1b/:\x96'  # noqa: E501
STRATEGY_WITHDRAWAL_COMPLETE_TOPIC: Final = b"\xe7\xeb\x0c\xa1\x1b\x83tN\xce=x\xe9\xbe\x01\xb9\x13B_\xba\xe7\x0c2\xce'rm\x0e\xcd\xe9.\xf8\xd2"  # noqa: E501
POD_DEPLOYED: Final = b'!\xc9\x9d\r\xb0"\x13\xc3/\xff[\x05\xcf\nq\x8a\xb5\xf8X\x80+\x91I\x8f\x80\xd8"p(\x9d\x85j'  # noqa: E501
DELAYED_WITHDRAWALS_CREATED: Final = b'\xb8\xf1\xb1L|\xaft\x15\x08\x01\xdc\xc9\xbc\x18\xd5u\xcb\xea\xf5\xb4!\x944\x97\xe4\t\xdf\x92\xc9.\x0fY'  # noqa: E501
DELAYED_WITHDRAWALS_CLAIMED: Final = b'kqQP\x0b\xd0\xb5\xcc!\x1b\xccG\xb3\x02\x981\xb7i\x00M\xf4T\x9e\x8e\x1c\x9ai\xda\x05\xbb\tC'  # noqa: E501
PARTIAL_WITHDRAWAL_REDEEMED: Final = b'\x8as5qB1\xdb\xd5Q\xaa\xbac\x14\xf4\xa9z\x14\xc2\x01\xe5:>%\xe1\x14\x03%\xcd\xf6}zN'  # noqa: E501
FULL_WITHDRAWAL_REDEEMED: Final = b'\xb7j\x93\xbbd\x9e\xceRF\x88\xf1\xa0\x1d\x18N\x0b\xbe\xbc\xdaX\xea\xe8\x0c(\xa8\x98\xbe\xc3\xfbZ\tc'  # noqa: E501
OPERATOR_SHARES_INCREASED: Final = b'\x1e\xc0B\xc9e\xe2\xed\xd7\x10{Q\x18\x8e\xe0\xf3\x83\xe2.v\x17\x90A\xab:\x9d\x18\xff\x15\x14\x05\x16l'  # noqa: E501
OPERATOR_SHARES_DECREASED: Final = b'i\t`\x007\xb7]{G3\xae\xdd\x81TB\xb5\xec\x01\x8a\x82wQ\xc82\xaa\xffd\xeb\xa5\xd6\xd2\xdd'  # noqa: E501
WITHDRAWAL_QUEUED: Final = b'\x90\t\xab\x15>\x80\x14\xfb\xfb\x02\xf2!\x7f\\\xdez\xa7\xf9\xadsJ\xe8\\\xa3\xee?L\xa2\xfd\xd4\x99\xf9'  # noqa: E501
WITHDRAWAL_COMPLETED: Final = b'\xc9p\x98\xc2\xf6X\x80\x0bM\xf2\x90\x01R\x7fs$\xbc\xdf\xfc\xf6\xe8u\x1ai\x9a\xb9 \xa1\xec\xed[\x1d'  # noqa: E501
POD_SHARES_UPDATED: Final = b'N+y\x1d\xed\xcc\xd9\xfb0\x14\x1b\x08\x8c\xab\xf5\xc1J\x89\x12\xb5/Y7\\\x95\xc0\x10p\x0b\x8ca\x93'  # noqa: E501
CHECKPOINT_CREATED: Final = b'WW\x96\x13;\xbe\xd37\xe5\xb3\x9a\xa4\x9a0\xdc%V\xa9\x1e\x0cl*\xf4\xb7\xb8\x86\xaew\xeb\xef\x10v'  # noqa: E501
CHECKPOINT_FINALIZED: Final = b'RT\x08\xc2\x01\xbc\x15v\xebD\x11odx\xf1\xc2\xa5Gu\xb1\x9a\x04;\xcf\xdcp\x83d\xf7O\x8eD'  # noqa: E501
VALIDATOR_BALANCE_UPDATED = b'\x0e_\xac\x17[\x83\x17|\xc0G8\x1e\x03\r\x8f\xb3\xb4+7\xbd\x1c\x02^"\xc2\x80\xfa\xca\xd6,2\xdf'  # noqa: E501
REWARDS_CLAIMED: Final = b'\x95C\xdb\xd5U\x80\x84%\x86\xa9Q\xf08n$\xd6\x8a]\xf9\x9a\xe2\x9e;!e\x88\xb4_\xd6\x84\xce1'  # noqa: E501

EIGENLAYER_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_EIGENLAYER,
    label='EigenLayer',
    image='eigenlayer.png',
)
EIGEN_TOKEN_ID: Final = 'eip155:1/erc20:0xec53bF9167f50cDEB3Ae105f56099aaaB9061F83'

# not the full ABIs, just the functions we call for each contract
STRATEGY_ABI: Final[ABI] = [{'inputs': [{'name': 'amountShares', 'type': 'uint256'}], 'name': 'sharesToUnderlyingView', 'outputs': [{'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}, {'inputs': [], 'name': 'underlyingToken', 'outputs': [{'name': '', 'type': 'address'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501
