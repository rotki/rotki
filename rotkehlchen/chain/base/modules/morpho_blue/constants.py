from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChecksumEvmAddress

CPT_MORPHO_BLUE: Final = 'morpho_blue'
MORPHO_BLUE_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_MORPHO_BLUE,
    label='Morpho Blue',
    image='morpho.svg',
)
MORPHO_BLUE: Final[ChecksumEvmAddress] = string_to_evm_address('0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb')  # noqa: E501

# Supply(bytes32 indexed id, address indexed caller, address indexed onBehalf,
# uint256 assets, uint256 shares)
MORPHO_BLUE_SUPPLY: Final = b'\xed\xf8\x87\x043\xc88#\xeb\x07\x1d=\xf1\xca\xa8\xd0\x08\xf1/d@\x91\x8c \xd7Z6\x02\xcd\xa3\x0f\xe0'  # noqa: E501

# Withdraw(bytes32 indexed id, address indexed caller, address indexed onBehalf,
# address receiver, uint256 assets, uint256 shares)
MORPHO_BLUE_WITHDRAW: Final = b'\xa5o\xc0\xadW\x02\xec\x05\xcecfb!\xf7\x96\xfbbC|2\xdb\x1a\xa1\xaa\x07_\xc6HL\xf5\x8f\xbf'  # noqa: E501

# Borrow(bytes32 indexed id, address caller, address indexed onBehalf,
# address indexed receiver, uint256 assets, uint256 shares)
MORPHO_BLUE_BORROW: Final = b'W\tTT\x0b\xedk\x13\x04\xa8}\xfe\x81Z^\xdaJd\x8fp\x97\xa1b@\xdc\xd8\\\x9b_\xd4*C'  # noqa: E501

# Repay(bytes32 indexed id, address indexed caller, address indexed onBehalf,
# uint256 assets, uint256 shares)
MORPHO_BLUE_REPAY: Final = b'R\xac\xb0\\\xeb\xbd<\xd3\x97\x15F\x9f"\xaf\xbfZ\x17Ib\x95\xef;\xc9\xbbYD\x05lc\xcc\xaa\t'  # noqa: E501

# SupplyCollateral(bytes32 indexed id, address indexed caller, address indexed onBehalf,
# uint256 assets)
MORPHO_BLUE_SUPPLY_COLLATERAL: Final = b'\xa3\xb9G*\x13\x99\xe1~\x12?<.e\x86\xc2>PA\x84\xd5\x04\xdeY\xcd\xaa+7^\x88\x0ca\x84'  # noqa: E501

# WithdrawCollateral(bytes32 indexed id, address caller, address indexed onBehalf,
# address indexed receiver, uint256 assets)
MORPHO_BLUE_WITHDRAW_COLLATERAL: Final = b'\xe8\x0e\xbd|\xc9"=s\x82\xaa\xb2\xe0\xd1\xd6\x15\\ee\x1f\x83\xd5<\x8b\x9b\x06\x90\x1d\x16~2\x11B'  # noqa: E501
