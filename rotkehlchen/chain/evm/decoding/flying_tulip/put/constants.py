from typing import TYPE_CHECKING, Final, NamedTuple

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID

if TYPE_CHECKING:
    from rotkehlchen.types import ChecksumEvmAddress


class FlyingTulipPutDeployment(NamedTuple):
    """Addresses of the ftPUT contracts on one chain."""
    put_manager: ChecksumEvmAddress
    ft_token: ChecksumEvmAddress
    # The ERC-721 collection whose token id is the position id: investing mints
    # one of these to the position recipient and closing a position burns it.
    position_nft: ChecksumEvmAddress
    # The collateral wrappers pay out divested capital directly to the user,
    # so they are valid counterparties of divest payout transfers. This list
    # has to track the protocol's deployments.
    collateral_wrappers: frozenset[ChecksumEvmAddress]


FLYING_TULIP_PUT_DEPLOYMENTS: Final[dict[ChainID, FlyingTulipPutDeployment]] = {
    ChainID.ETHEREUM: FlyingTulipPutDeployment(
        put_manager=string_to_evm_address('0xbA49d0AC42f4fBA4e24A8677a22218a4dF75ebaA'),
        ft_token=string_to_evm_address('0x5DD1A7A369e8273371d2DBf9d83356057088082c'),
        position_nft=string_to_evm_address('0xa4215Daaf3745E14E96E169E0E7706c479Ce04F2'),
        collateral_wrappers=frozenset((
            string_to_evm_address('0x095d8B8D4503D590F647343F7cD880Fa2abbbf59'),  # USDC
            string_to_evm_address('0x9d96bac8a4E9A5b51b5b262F316C4e648E44E305'),  # WNative
            string_to_evm_address('0x267dF6b637DdCaa7763d94b64eBe09F01b07cB36'),  # USDT
            string_to_evm_address('0xA143a9C486a1A4aaf54FAEFF7252CECe2d337573'),  # USDS
            string_to_evm_address('0xE5270E0458f58b83dB3d90Aa6A616173c98C97b6'),  # USDTb
            string_to_evm_address('0xe6880Fc961b1235c46552E391358A270281b5625'),  # USDe
        )),
    ),
}

# Invested(address investor, address recipient, uint256 id, uint256 amount, uint256 strike, address token, uint256 amountInvested)  # noqa: E501
# 0x6b378ba7b8aee8cdec625cbd9a7da8c6b707fff554bb1861cfde6741325be6d1
INVESTED_TOPIC: Final = b'k7\x8b\xa7\xb8\xae\xe8\xcd\xecb\\\xbd\x9a}\xa8\xc6\xb7\x07\xff\xf5T\xbb\x18a\xcf\xdegA2[\xe6\xd1'  # noqa: E501
# Divested(address divestor, uint256 id, uint256 amount, uint256 strike, address token, uint256 amountDivested)  # noqa: E501
# 0x4ad9503b7764b141ca283f7a7aa34fc52a3ba953b692db4f46a25ff846b4ef8b
DIVESTED_TOPIC: Final = b'J\xd9P;wd\xb1A\xca(?zz\xa3O\xc5*;\xa9S\xb6\x92\xdbOF\xa2_\xf8F\xb4\xef\x8b'  # noqa: E501
