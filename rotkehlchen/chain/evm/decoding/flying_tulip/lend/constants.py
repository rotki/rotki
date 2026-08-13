from typing import TYPE_CHECKING, Final, NamedTuple

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID

if TYPE_CHECKING:
    from eth_typing import ABI

    from rotkehlchen.types import ChecksumEvmAddress


class FlyingTulipLendDeployment(NamedTuple):
    """Addresses of the Flying Tulip lending contracts on one chain."""
    positions_manager: ChecksumEvmAddress
    lending_lens: ChecksumEvmAddress
    # RFQ engines move funds inside the positions manager on behalf of users
    # when filling leverage orders. Events they drive are position-internal
    # rebalancing, not wallet-level lending activity, and are skipped.
    engines: frozenset[ChecksumEvmAddress]
    # Entry points for direct and session (relayed) lending actions, used to
    # trigger the post-decoding rule when a transaction is sent through them
    # and to recognize relayed transfers that carry a relayer fee. This list
    # has to track the protocol's deployments: positions manager events in a
    # transaction routed through an entry point missing here are not decoded.
    meta_actions: frozenset[ChecksumEvmAddress]


FLYING_TULIP_LEND_DEPLOYMENTS: Final[dict[ChainID, FlyingTulipLendDeployment]] = {
    ChainID.ETHEREUM: FlyingTulipLendDeployment(
        positions_manager=string_to_evm_address('0xbe4050a73a7Fb384c65E885a15C33461A4B20055'),
        lending_lens=string_to_evm_address('0x3682168023E6bA8D1F995FdA1D920827C5A8A43E'),
        engines=frozenset((
            string_to_evm_address('0x8263a07504d93cB95e0a74f3627bb15faaf140e2'),  # LeverageRfqEngine  # noqa: E501
            string_to_evm_address('0xEB00B335Ca52216Fb60fdFFA361397367C39Dc32'),  # RfqEngine
        )),
        meta_actions=frozenset((
            string_to_evm_address('0x3633EB60D08756674472e2D34d6fFb5f4c1c29f2'),  # MetaActions
            string_to_evm_address('0x4f83aC5c8A79986D0916a8849730d9CEF63a3497'),  # MetaSessionActions  # noqa: E501
        )),
    ),
}

# DepositFor(address indexed from, address indexed beneficiary, address indexed asset, uint256 amount)  # noqa: E501
# 0x9b97b64e9cc6e815f094532deb9581a5b7daa7de9eecaf344c66d6e707b0b418
PM_DEPOSIT_FOR_TOPIC: Final = b'\x9b\x97\xb6N\x9c\xc6\xe8\x15\xf0\x94S-\xeb\x95\x81\xa5\xb7\xda\xa7\xde\x9e\xec\xaf4Lf\xd6\xe7\x07\xb0\xb4\x18'  # noqa: E501
# Borrow(address indexed u, address indexed a, uint256 amt)
# 0x312a5e5e1079f5dda4e95dbbd0b908b291fd5b992ef22073643ab691572c5b52
PM_BORROW_TOPIC: Final = b'1*^^\x10y\xf5\xdd\xa4\xe9]\xbb\xd0\xb9\x08\xb2\x91\xfd[\x99.\xf2 sd:\xb6\x91W,[R'  # noqa: E501
# Repay(address indexed u, address indexed a, uint256 amt, bool full)
# 0x32b9f192f046502437b65280a1ff8a435327a7bb3986b85db4a5e61b44e5d3b3
PM_REPAY_TOPIC: Final = b"2\xb9\xf1\x92\xf0FP$7\xb6R\x80\xa1\xff\x8aCS'\xa7\xbb9\x86\xb8]\xb4\xa5\xe6\x1bD\xe5\xd3\xb3"  # noqa: E501
# RepayFor(address indexed from, address indexed borrower, address indexed asset, uint256 amount, bool full)  # noqa: E501
# 0xfe1b46ad82b670225ffdad07a6c5d6c091daed088a1c049d9e4a3dc82124e137
PM_REPAY_FOR_TOPIC: Final = b'\xfe\x1bF\xad\x82\xb6p"_\xfd\xad\x07\xa6\xc5\xd6\xc0\x91\xda\xed\x08\x8a\x1c\x04\x9d\x9eJ=\xc8!$\xe17'  # noqa: E501

POSITIONS_MANAGER_ABI: Final[ABI] = [
    {
        'inputs': [{'name': 'user', 'type': 'address'}],
        'name': 'userCollateralAssets',
        'outputs': [{'name': '', 'type': 'address[]'}],
        'stateMutability': 'view',
        'type': 'function',
    }, {
        'inputs': [{'name': 'user', 'type': 'address'}],
        'name': 'userDebtAssets',
        'outputs': [{'name': '', 'type': 'address[]'}],
        'stateMutability': 'view',
        'type': 'function',
    }, {
        'inputs': [
            {'name': 'user', 'type': 'address'},
            {'name': 'token', 'type': 'address'},
        ],
        'name': 'getBalance',
        'outputs': [
            {'name': 'avail', 'type': 'uint256'},
            {'name': 'holdBal', 'type': 'uint256'},
        ],
        'stateMutability': 'view',
        'type': 'function',
    },
]

LENDING_LENS_ABI: Final[ABI] = [
    {
        'inputs': [
            {'name': 'user', 'type': 'address'},
            {'name': 'asset', 'type': 'address'},
        ],
        'name': 'debt',
        'outputs': [{'name': 'principal', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
]
