from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID

if TYPE_CHECKING:
    from eth_typing.abi import ABI

    from rotkehlchen.types import ChecksumEvmAddress

CPT_KILN: Final = 'kiln'
KILN_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_KILN,
    label='Kiln',
    image='kiln.svg',
    darkmode_image='kiln_dark.svg',
)

# Kiln contracts are beacon proxies. The beacon a proxy uses is what identifies it as a
# Kiln contract, since the factories that deploy them get replaced over time.
EIP1967_BEACON_SLOT: Final = 0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50

# The VaultUpgradeableBeacon of the Kiln DeFi ERC4626 vaults on each chain.
# Every partner/protocol/asset combination gets its own vault behind this beacon.
KILN_DEFI_VAULT_BEACONS: Final[dict[ChainID, ChecksumEvmAddress]] = {
    ChainID.ETHEREUM: string_to_evm_address('0x15f7F910e5A8c86e609fd11C58F7342d86d3a25C'),
    ChainID.BINANCE_SC: string_to_evm_address('0x50006F2C5C914cEF560ceeD7686f038480199202'),
    ChainID.ARBITRUM_ONE: string_to_evm_address('0xB03DDF4375E879B8E3bc240527bc55988c975ac4'),
    ChainID.POLYGON_POS: string_to_evm_address('0x89312A13D978820F15bC9414ef6ec9cC004C5D1f'),
    ChainID.OPTIMISM: string_to_evm_address('0xE1CacE168150265E1b1bC6E9c1636B747928a1D8'),
    ChainID.BASE: string_to_evm_address('0x1D011ff40899e22fcBa7ac1DeDCf227a1B4974DB'),
}

KILN_VAULT_ABI: Final[ABI] = [{
    'inputs': [],
    'name': 'asset',
    'outputs': [{'name': '', 'type': 'address'}],
    'stateMutability': 'view',
    'type': 'function',
}, {
    'inputs': [{'name': 'shares', 'type': 'uint256'}],
    'name': 'convertToAssets',
    'outputs': [{'name': '', 'type': 'uint256'}],
    'stateMutability': 'view',
    'type': 'function',
}]
