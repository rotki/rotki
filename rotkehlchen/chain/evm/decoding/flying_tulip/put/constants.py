from typing import TYPE_CHECKING, Final, NamedTuple

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID

if TYPE_CHECKING:
    from rotkehlchen.types import ChecksumEvmAddress


class FlyingTulipPutDeployment(NamedTuple):
    """Addresses of the ftPUT contracts on one chain."""
    put_manager: 'ChecksumEvmAddress'
    ft_token: 'ChecksumEvmAddress'


FLYING_TULIP_PUT_DEPLOYMENTS: Final[dict[ChainID, FlyingTulipPutDeployment]] = {
    ChainID.ETHEREUM: FlyingTulipPutDeployment(
        put_manager=string_to_evm_address('0xbA49d0AC42f4fBA4e24A8677a22218a4dF75ebaA'),
        ft_token=string_to_evm_address('0x5DD1A7A369e8273371d2DBf9d83356057088082c'),
    ),
}

# Invested(address investor, address recipient, uint256 id, uint256 amount, uint256 strike, address token, uint256 amountInvested)  # noqa: E501
# 0x6b378ba7b8aee8cdec625cbd9a7da8c6b707fff554bb1861cfde6741325be6d1
INVESTED_TOPIC: Final = b'k7\x8b\xa7\xb8\xae\xe8\xcd\xecb\\\xbd\x9a}\xa8\xc6\xb7\x07\xff\xf5T\xbb\x18a\xcf\xdegA2[\xe6\xd1'  # noqa: E501
# Divested(address divestor, uint256 id, uint256 amount, uint256 strike, address token, uint256 amountDivested)  # noqa: E501
# 0x4ad9503b7764b141ca283f7a7aa34fc52a3ba953b692db4f46a25ff846b4ef8b
DIVESTED_TOPIC: Final = b'J\xd9P;wd\xb1A\xca(?zz\xa3O\xc5*;\xa9S\xb6\x92\xdbOF\xa2_\xf8F\xb4\xef\x8b'  # noqa: E501
# Withdraw(address owner, uint256 id, uint256 amount)
# 0xf279e6a1f5e320cca91135676d9cb6e44ca8a08c0b88342bcdb1144f6511b568
PUT_WITHDRAW_FT_TOPIC: Final = b'\xf2y\xe6\xa1\xf5\xe3 \xcc\xa9\x115gm\x9c\xb6\xe4L\xa8\xa0\x8c\x0b\x884+\xcd\xb1\x14Oe\x11\xb5h'  # noqa: E501
