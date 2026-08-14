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
    # The engine whose leverage fill events are decoded into informational
    # history entries, which also seed the balance discovery for users whose
    # position was opened purely engine-side.
    leverage_engine: ChecksumEvmAddress
    # Entry points for direct and session (relayed) lending actions, used to
    # trigger the post-decoding rule when a transaction is sent through them
    # and to recognize relayed transfers that carry a relayer fee. This list
    # has to track the protocol's deployments: positions manager events in a
    # transaction routed through an entry point missing here are not decoded.
    meta_actions: frozenset[ChecksumEvmAddress]
    # The per-asset yield wrappers the positions manager routes funds through.
    # They can be the direct counterparty of a payout transfer, so they both
    # qualify transfers for matching and trigger the post-decoding rule.
    yield_wrappers: frozenset[ChecksumEvmAddress]


FLYING_TULIP_LEND_DEPLOYMENTS: Final[dict[ChainID, FlyingTulipLendDeployment]] = {
    ChainID.ETHEREUM: FlyingTulipLendDeployment(
        positions_manager=string_to_evm_address('0xbe4050a73a7Fb384c65E885a15C33461A4B20055'),
        lending_lens=string_to_evm_address('0x3682168023E6bA8D1F995FdA1D920827C5A8A43E'),
        engines=frozenset((
            string_to_evm_address('0x8263a07504d93cB95e0a74f3627bb15faaf140e2'),  # LeverageRfqEngine  # noqa: E501
            string_to_evm_address('0xEB00B335Ca52216Fb60fdFFA361397367C39Dc32'),  # RfqEngine
        )),
        leverage_engine=string_to_evm_address('0x8263a07504d93cB95e0a74f3627bb15faaf140e2'),
        meta_actions=frozenset((
            string_to_evm_address('0x3633EB60D08756674472e2D34d6fFb5f4c1c29f2'),  # MetaActions
            string_to_evm_address('0x4f83aC5c8A79986D0916a8849730d9CEF63a3497'),  # MetaSessionActions  # noqa: E501
        )),
        yield_wrappers=frozenset((
            string_to_evm_address('0xD2e4A5ac4B4Da102317cF7C9A1289aDF082639E2'),  # USDC
            string_to_evm_address('0x460494aF61BcB92B59797B4e09C26A5ADecb2da2'),  # wNative
            string_to_evm_address('0x01980BD1B58313bD3767f6adc75Af8b6464f3db7'),  # stakedNative
            string_to_evm_address('0x28b0905d83BCe5FFA6c54651F25858828A38123B'),  # USDT
            string_to_evm_address('0x7127BB9d9ad0f47B8dA9087e634D67F3946F840E'),  # FT
            string_to_evm_address('0xc67D966f761e8cf13Faa0a1E774425290c8453d9'),  # ftUSD
            string_to_evm_address('0x1A5730c71576D77048E9FdC79DD40e4B1E8Fe042'),  # wBTC
        )),
    ),
    ChainID.BINANCE_SC: FlyingTulipLendDeployment(
        positions_manager=string_to_evm_address('0xB36d39C72d66153B7f32E1320BEe3280657353Bd'),
        lending_lens=string_to_evm_address('0xc374d2aE274f31bf53C561d0b4024136cC692f48'),
        engines=frozenset((
            string_to_evm_address('0x01916c31dEF593cD94D707724FAcdf7add121Bf1'),  # LeverageRfqEngine  # noqa: E501
            string_to_evm_address('0xa0DBD53aEeC3F5acD16c69C3001114eE51813E58'),  # RfqEngine
        )),
        leverage_engine=string_to_evm_address('0x01916c31dEF593cD94D707724FAcdf7add121Bf1'),
        meta_actions=frozenset((
            string_to_evm_address('0xdbF637ec1400Eeb020e862D6aB6B8914D1931AbB'),  # MetaActions
            string_to_evm_address('0x97fa3B5A531f4E2Fa84CcaF1B53F5c4e512c4077'),  # MetaSessionActions  # noqa: E501
        )),
        yield_wrappers=frozenset((
            string_to_evm_address('0x39285FA9992A3A87e1C2e1476C1404E2cfdD1931'),  # USDC
            string_to_evm_address('0xa07adCaFc7709685836CF357Fa537AE2B3061156'),  # WBNB
            string_to_evm_address('0x2D3587Fbd9A8fD4d4dD76e0102BC0063776E5BF6'),  # asBNB
            string_to_evm_address('0xFe040BEeF432FB924f871e9C76180b557a13533c'),  # USDT
            string_to_evm_address('0x41CB54680d1Baa26b85bc97641854E59964dBe38'),  # FDUSD
            string_to_evm_address('0xdfFD30B2595044e16c5EDf193A746D582783793d'),  # FT
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

# The leverage fill events all share the layout (address indexed filler, address indexed user, address indexed receiver, address sellToken, address buyToken, uint256 sellAmount, ...)  # noqa: E501
# OpenLeverageFilled(address indexed filler, address indexed user, address indexed receiver, address sellToken, address buyToken, uint256 sellAmount, uint256 buyAmountIn, uint256 buyAmountMin, uint256 feeAmount, bytes32 digest)  # noqa: E501
# 0xf10165a5b14f33e30ae647cf5eb988c5ce7122a13fba12e6fb5b9586278c3d09
OPEN_LEVERAGE_FILLED_TOPIC: Final = b'\xf1\x01e\xa5\xb1O3\xe3\n\xe6G\xcf^\xb9\x88\xc5\xceq"\xa1?\xba\x12\xe6\xfb[\x95\x86\'\x8c=\t'  # noqa: E501
# OpenLeverageFlashFilled(address indexed filler, address indexed user, address indexed receiver, address sellToken, address buyToken, uint256 sellAmount, uint256 buyAmountMin, uint256 feeAmount, address fillTarget, bytes32 digest)  # noqa: E501
# 0xcc26eea29ec6f7d5c4ff51f3c9b3ff6bd4b0575e7e2ab99e25b3f07613a4832f
OPEN_LEVERAGE_FLASH_FILLED_TOPIC: Final = b'\xcc&\xee\xa2\x9e\xc6\xf7\xd5\xc4\xffQ\xf3\xc9\xb3\xffk\xd4\xb0W^~*\xb9\x9e%\xb3\xf0v\x13\xa4\x83/'  # noqa: E501
# CloseLeverageFilled(address indexed filler, address indexed user, address indexed receiver, address sellToken, address buyToken, uint256 sellAmount, uint256 buyAmountIn, uint256 buyAmountMin, uint256 feeAmount, bytes32 digest)  # noqa: E501
# 0x22f41c76561b0c426efdb1355e73725b3c1b63ae56d743cdafa06b3572b65971
CLOSE_LEVERAGE_FILLED_TOPIC: Final = b'"\xf4\x1cvV\x1b\x0cBn\xfd\xb15^sr[<\x1bc\xaeV\xd7C\xcd\xaf\xa0k5r\xb6Yq'  # noqa: E501
# CloseLeverageFlashFilled(address indexed filler, address indexed user, address indexed receiver, address sellToken, address buyToken, uint256 sellAmount, uint256 buyAmountMin, uint256 feeAmount, address fillTarget, bytes32 digest)  # noqa: E501
# 0xa9d270f97b84471fed88da0dd9e0936a7dcb3ebfc6de1b1943d58d16ce6d6be8
CLOSE_LEVERAGE_FLASH_FILLED_TOPIC: Final = b'\xa9\xd2p\xf9{\x84G\x1f\xed\x88\xda\r\xd9\xe0\x93j}\xcb>\xbf\xc6\xde\x1b\x19C\xd5\x8d\x16\xcemk\xe8'  # noqa: E501
# CollateralSwapFilled(address indexed filler, address indexed user, address indexed receiver, address sellToken, address buyToken, uint256 sellAmount, uint256 buyAmountIn, uint256 buyAmountMin, uint256 feeAmount, bytes32 digest)  # noqa: E501
# 0x71674d065a34912f8c1f16e8ef1274486beba4d0349ccf209b5989ff3c3892ec
COLLATERAL_SWAP_FILLED_TOPIC: Final = b'qgM\x06Z4\x91/\x8c\x1f\x16\xe8\xef\x12tHk\xeb\xa4\xd04\x9c\xcf \x9bY\x89\xff<8\x92\xec'  # noqa: E501
# CollateralSwapFlashFilled(address indexed filler, address indexed user, address indexed receiver, address sellToken, address buyToken, uint256 sellAmount, uint256 buyAmountMin, uint256 feeAmount, address fillTarget, bytes32 digest)  # noqa: E501
# 0xb4a8c723294d64215bd89bb6f8d10809a1af3373f7fea1b4b65d9455b1ab6876
COLLATERAL_SWAP_FLASH_FILLED_TOPIC: Final = b'\xb4\xa8\xc7#)Md![\xd8\x9b\xb6\xf8\xd1\x08\t\xa1\xaf3s\xf7\xfe\xa1\xb4\xb6]\x94U\xb1\xabhv'  # noqa: E501
