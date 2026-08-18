from typing import TYPE_CHECKING, Final, NamedTuple

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID

if TYPE_CHECKING:
    from eth_typing import ABI

    from rotkehlchen.types import ChecksumEvmAddress


class FlyingTulipFtusdDeployment(NamedTuple):
    """Addresses of the ftUSD contracts on one chain."""
    mint_and_redeem: ChecksumEvmAddress
    staking_vault: ChecksumEvmAddress  # EpochRewardsVault, the sftUSD ERC-4626 vault
    ftusd_token: ChecksumEvmAddress
    ft_token: ChecksumEvmAddress  # staking rewards are paid in FT
    # The collateral wrappers pay redemptions and unstaked funds directly to
    # the user, so they are valid counterparties of payout transfers. This
    # list has to track the protocol's deployments.
    wrappers: frozenset[ChecksumEvmAddress]
    # CircuitBreakerV2: rate-limited payouts are queued here and paid out to
    # the recipient in a later transaction.
    circuit_breaker: ChecksumEvmAddress


FLYING_TULIP_FTUSD_DEPLOYMENTS: Final[dict[ChainID, FlyingTulipFtusdDeployment]] = {
    ChainID.ETHEREUM: FlyingTulipFtusdDeployment(
        mint_and_redeem=string_to_evm_address('0xAa48EcBC843cF7E9A29155D112b8Cb27902bD23C'),
        staking_vault=string_to_evm_address('0xeb48218a4c35C814C7678cBcae88C6Ee037F7625'),
        ftusd_token=string_to_evm_address('0xF7D85EC4E7710f71992752eac2111312e73E9C9C'),
        ft_token=string_to_evm_address('0x5DD1A7A369e8273371d2DBf9d83356057088082c'),
        wrappers=frozenset((
            string_to_evm_address('0xB44a9C40EFc05Eb014EfFEac3CBed6A31F8cB87f'),  # WrapperFtUSD
            string_to_evm_address('0x6aaf84563Cdb03a22Cd92EE2553698beE87E837D'),  # WrapperUSDC
            string_to_evm_address('0x28CCa8eEA2cD0498cE91A9da15772A1ce42347D6'),  # WrapperUSDT
        )),
        circuit_breaker=string_to_evm_address('0xCB210509F5AE2b3843B7Fb8Bb90bAFF9cE4f7355'),
    ),
}

# Minted(address caller, address indexed from, address indexed to, bytes32 ref, address indexed collateralToken, uint256 collateralAmount, uint256 ftUSDAmount, uint256 feeFtUSDAmount, uint256 wrapperPrincipalAfter)  # noqa: E501
# 0x454c9ef91f9a4bdcc1548f5513404ba456b13a463573701c2087c1e5a5a03b04
MINTED_TOPIC: Final = b'EL\x9e\xf9\x1f\x9aK\xdc\xc1T\x8fU\x13@K\xa4V\xb1:F5sp\x1c \x87\xc1\xe5\xa5\xa0;\x04'  # noqa: E501
# Redeemed(address caller, address indexed from, address indexed to, bytes32 ref, address indexed collateralToken, uint256 ftUSDAmount, uint256 feeFtUSDAmount, uint256 collateralAmount, uint256 wrapperPrincipalAfter)  # noqa: E501
# 0x1c68c6a3f8da24e8a1966d3ce59c0b469a1270d6435af45796ec91456bb1e0e2
REDEEMED_TOPIC: Final = b'\x1ch\xc6\xa3\xf8\xda$\xe8\xa1\x96m<\xe5\x9c\x0bF\x9a\x12p\xd6CZ\xf4W\x96\xec\x91Ek\xb1\xe0\xe2'  # noqa: E501
# Claimed(address indexed user, address indexed to, uint256 paid, uint256 remaining)
# 0x2f6639d24651730c7bf57c95ddbf96d66d11477e4ec626876f92c22e5f365e68
CLAIMED_TOPIC: Final = b'/f9\xd2FQs\x0c{\xf5|\x95\xdd\xbf\x96\xd6m\x11G~N\xc6&\x87o\x92\xc2._6^h'
# RelayerFeePaid(address indexed user, address indexed executor, address token, uint256 amount)
# 0x8e42ca3aac5a530592fc918a1c73f7a155aa98df7379ecb1148b885792035f6e
VAULT_RELAYER_FEE_PAID_TOPIC: Final = b'\x8eB\xca:\xacZS\x05\x92\xfc\x91\x8a\x1cs\xf7\xa1U\xaa\x98\xdfsy\xec\xb1\x14\x8b\x88W\x92\x03_n'  # noqa: E501

STAKING_VAULT_ABI: Final[ABI] = [
    {
        'inputs': [{'name': 'u', 'type': 'address'}],
        'name': 'previewClaimable',
        'outputs': [{'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
]

# OutflowQueued(uint256 indexed queueId, address indexed asset, address indexed recipient, uint256 amount, uint256 settlesAt)  # noqa: E501
# 0x78aaf104c48223418f804d51391e35441b7277ff72b42187446efb7469b6383b
OUTFLOW_QUEUED_TOPIC: Final = b'x\xaa\xf1\x04\xc4\x82#A\x8f\x80MQ9\x1e5D\x1brw\xffr\xb4!\x87Dn\xfbti\xb68;'  # noqa: E501
# OutflowExecuted(uint256 indexed queueId, address indexed recipient, address indexed asset, uint256 amount)  # noqa: E501
# 0x6683eb3425d0fa38df2efe81ecf86f2a2d421bbdcc1cc63afad4f6ca9c796cdd
OUTFLOW_EXECUTED_TOPIC: Final = b'f\x83\xeb4%\xd0\xfa8\xdf.\xfe\x81\xec\xf8o*-B\x1b\xbd\xcc\x1c\xc6:\xfa\xd4\xf6\xca\x9cyl\xdd'  # noqa: E501
