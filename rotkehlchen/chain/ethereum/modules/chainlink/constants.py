from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from eth_typing.abi import ABI

CPT_CHAINLINK: Final = 'chainlink'

# Staking v0.1, which was concluded once v0.2 launched. Stakers either migrate their stake and
# rewards to the v0.2 community pool or unstake them.
STAKING_V01: Final = string_to_evm_address('0x3feB1e09b4bb0E7f0387CeE092a52e85797ab889')
COMMUNITY_POOL: Final = string_to_evm_address('0xBc10f2E862ED4502144c7d632a3459F49DFCDB5e')
OPERATOR_POOL: Final = string_to_evm_address('0xA1d76A7cA72128541E9FCAcafBdA3a92EF94fDc5')
STAKING_V02_POOLS: Final = {COMMUNITY_POOL: 'community', OPERATOR_POOL: 'operator'}
REWARD_VAULT: Final = string_to_evm_address('0x996913c8c08472f584ab8834e925b06D0eb1D813')

# Unstaked(address staker, uint256 principal, uint256 baseReward, uint256 delegationReward) of
# v0.1 and Unstaked(address indexed staker, uint256 amount, uint256 newStake,
# uint256 newTotalPrincipal) of v0.2 have the same signature.
UNSTAKED: Final = b' O\xcc\xf0\xd9.\xd8\xd4\x8f J\xdb9\xb2\xe8\x1e\x92\xba\xd0\xde\xdb\x93\xf5ql\xa9G\x8c\xfbW\xde\x00'  # noqa: E501
# Migrated(address staker, uint256 principal, uint256 baseReward, uint256 delegationReward,
# bytes data) of v0.1
MIGRATED_V01: Final = b'fx8\xb3;\xdc\x89\x84p\xde\t\xe0\xe7F\x99\x0f*\xdc\x11\xb9e\xb7\xfeh(\xe5\x02\xeb\xc3\x9e\x044'  # noqa: E501
# Staked(address indexed staker, uint256 amount, uint256 newStake, uint256 newTotalPrincipal)
STAKED_V02: Final = b'\xb4\xca\xaf)\xad\xda>\xef\xee:\xd5R\xa8\xe8PXX\x9b\xf84\xc7Fl\xaeN\xe5\x87\x87\xf7\x05\x89\xed'  # noqa: E501
# UnbondingPeriodStarted(address indexed staker)
UNBONDING_PERIOD_STARTED: Final = b'[\x9c\xd1\xc6\xf2KAm#T\xb7\xb7\xad\x07\xd9+\xc1\xc6b\xa4\x03\x18\x0e\x84\xfa\xc2x$\x14\xa5\xf4\xed'  # noqa: E501
# RewardClaimed(address indexed staker, uint256 claimedRewards)
REWARD_CLAIMED: Final = b'\x10o\x92?\x99<!I\xd4\x9bBU\xffr:\xca\xfa\x1f-\x949?V\x1d>\xda2\xae4\x8frA'  # noqa: E501

CHAINLINK_STAKING_ABI: Final[ABI] = [
    {'inputs': [{'name': 'staker', 'type': 'address'}], 'name': 'getStake', 'outputs': [{'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'},  # noqa: E501
    {'inputs': [{'name': 'staker', 'type': 'address'}], 'name': 'getBaseReward', 'outputs': [{'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'},  # noqa: E501
    {'inputs': [{'name': 'staker', 'type': 'address'}], 'name': 'getDelegationReward', 'outputs': [{'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'},  # noqa: E501
    {'inputs': [{'name': 'staker', 'type': 'address'}], 'name': 'getStakerPrincipal', 'outputs': [{'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'},  # noqa: E501
    {'inputs': [{'name': 'staker', 'type': 'address'}], 'name': 'getReward', 'outputs': [{'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'},  # noqa: E501
]
