from typing import TYPE_CHECKING, Final, NamedTuple

from eth_utils import keccak

from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from eth_typing.abi import ABI

    from rotkehlchen.types import ChecksumEvmAddress

    from .structures import VestingEscrowKind, VestingEscrowVersion

CPT_YEARN_VESTING: Final = 'yearn-vesting'
YEARN_VESTING_LABEL: Final = 'Yearn Vesting'
YEARN_VESTING_ICON: Final = 'yearn_vaults.svg'

V1_FACTORY: Final = string_to_evm_address('0xF124534bfa6Ac7b89483B401B4115Ec0d27cad6A')
V2_FACTORY: Final = string_to_evm_address('0x98d3872b4025ABE58C4667216047Fe549378d90f')
V3_FACTORY: Final = string_to_evm_address('0x200C92Dd85730872Ab6A1e7d5E40A067066257cF')
LLAMAPAY_V2_FACTORY: Final = string_to_evm_address(
    '0xcf61782465Ff973638143d6492B51A85986aB347',
)
V4_FACTORY: Final = string_to_evm_address('0xFbd94e2D6942D5b4Ed0C5C9C43bded77a8f20215')

HISTORICAL_FACTORY_ABI: Final[ABI] = [{
    'anonymous': False,
    'inputs': [
        {'indexed': True, 'name': 'funder', 'type': 'address'},
        {'indexed': True, 'name': 'token', 'type': 'address'},
        {'indexed': True, 'name': 'recipient', 'type': 'address'},
        {'indexed': False, 'name': 'escrow', 'type': 'address'},
        {'indexed': False, 'name': 'amount', 'type': 'uint256'},
        {'indexed': False, 'name': 'vesting_start', 'type': 'uint256'},
        {'indexed': False, 'name': 'vesting_duration', 'type': 'uint256'},
        {'indexed': False, 'name': 'cliff_length', 'type': 'uint256'},
    ],
    'name': 'VestingEscrowCreated',
    'type': 'event',
}]

V3_FACTORY_ABI: Final[ABI] = [{
    'anonymous': False,
    'inputs': [
        {'indexed': True, 'name': 'funder', 'type': 'address'},
        {'indexed': True, 'name': 'token', 'type': 'address'},
        {'indexed': True, 'name': 'recipient', 'type': 'address'},
        {'indexed': False, 'name': 'escrow', 'type': 'address'},
        {'indexed': False, 'name': 'amount', 'type': 'uint256'},
        {'indexed': False, 'name': 'vesting_start', 'type': 'uint256'},
        {'indexed': False, 'name': 'vesting_duration', 'type': 'uint256'},
        {'indexed': False, 'name': 'cliff_length', 'type': 'uint256'},
        {'indexed': False, 'name': 'open_claim', 'type': 'bool'},
    ],
    'name': 'VestingEscrowCreated',
    'type': 'event',
}]

V4_FACTORY_ABI: Final[ABI] = [{
    'anonymous': False,
    'inputs': [
        {'indexed': True, 'name': 'escrow', 'type': 'address'},
        {'indexed': True, 'name': 'token', 'type': 'address'},
        {'indexed': True, 'name': 'recipient', 'type': 'address'},
        {'indexed': False, 'name': 'funder', 'type': 'address'},
        {'indexed': False, 'name': 'revoker', 'type': 'address'},
        {'indexed': False, 'name': 'amount', 'type': 'uint256'},
        {'indexed': False, 'name': 'vesting_start', 'type': 'uint256'},
        {'indexed': False, 'name': 'vesting_duration', 'type': 'uint256'},
        {'indexed': False, 'name': 'cliff_length', 'type': 'uint256'},
        {'indexed': False, 'name': 'permissionless_claims', 'type': 'bool'},
    ],
    'name': 'TokenVestingEscrowCreated',
    'type': 'event',
}, {
    'anonymous': False,
    'inputs': [
        {'indexed': True, 'name': 'escrow', 'type': 'address'},
        {'indexed': True, 'name': 'vault', 'type': 'address'},
        {'indexed': True, 'name': 'recipient', 'type': 'address'},
        {'indexed': False, 'name': 'funder', 'type': 'address'},
        {'indexed': False, 'name': 'revoker', 'type': 'address'},
        {'indexed': False, 'name': 'yield_recipient', 'type': 'address'},
        {'indexed': False, 'name': 'asset_token', 'type': 'address'},
        {'indexed': False, 'name': 'funded_shares', 'type': 'uint256'},
        {'indexed': False, 'name': 'principal_assets', 'type': 'uint256'},
        {'indexed': False, 'name': 'vesting_start', 'type': 'uint256'},
        {'indexed': False, 'name': 'vesting_duration', 'type': 'uint256'},
        {'indexed': False, 'name': 'cliff_length', 'type': 'uint256'},
        {'indexed': False, 'name': 'permissionless_claims', 'type': 'bool'},
    ],
    'name': 'ERC4626VestingEscrowCreated',
    'type': 'event',
}]

TOKEN_ESCROW_ABI: Final[ABI] = [
    {
        'inputs': [],
        'name': 'total_claimed',
        'outputs': [{'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    }, {
        'inputs': [],
        'name': 'disabled_at',
        'outputs': [{'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
]
ERC4626_ESCROW_ABI: Final[ABI] = [
    {
        'inputs': [],
        'name': 'claimed_principal_assets',
        'outputs': [{'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    }, {
        'inputs': [],
        'name': 'disabled_at',
        'outputs': [{'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    }, {
        'inputs': [],
        'name': 'claimable_yield_shares',
        'outputs': [{'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
]


class FactoryDeployment(NamedTuple):
    address: ChecksumEvmAddress
    deployed_block: int
    version: VestingEscrowVersion
    kind: VestingEscrowKind
    event_name: str
    abi: ABI


FACTORY_DEPLOYMENTS: Final = (
    FactoryDeployment(
        address=V1_FACTORY,
        deployed_block=11868366,
        version='v0.1.0',
        kind='token',
        event_name='VestingEscrowCreated',
        abi=HISTORICAL_FACTORY_ABI,
    ),
    FactoryDeployment(
        address=V2_FACTORY,
        deployed_block=13373452,
        version='v0.2.0',
        kind='token',
        event_name='VestingEscrowCreated',
        abi=HISTORICAL_FACTORY_ABI,
    ),
    FactoryDeployment(
        address=V3_FACTORY,
        deployed_block=18291969,
        version='v0.3.0',
        kind='token',
        event_name='VestingEscrowCreated',
        abi=V3_FACTORY_ABI,
    ),
    FactoryDeployment(
        address=LLAMAPAY_V2_FACTORY,
        deployed_block=19739664,
        version='llamapay-v2',
        kind='token',
        event_name='VestingEscrowCreated',
        abi=V3_FACTORY_ABI,
    ),
    FactoryDeployment(
        address=V4_FACTORY,
        deployed_block=25602335,
        version='v0.4.0',
        kind='token',
        event_name='TokenVestingEscrowCreated',
        abi=V4_FACTORY_ABI,
    ),
    FactoryDeployment(
        address=V4_FACTORY,
        deployed_block=25602335,
        version='v0.4.0',
        kind='erc4626',
        event_name='ERC4626VestingEscrowCreated',
        abi=V4_FACTORY_ABI,
    ),
)
FACTORIES: Final = {deployment.address for deployment in FACTORY_DEPLOYMENTS}
VESTING_ESCROW_CREATED: Final = keccak(
    text='VestingEscrowCreated(address,address,address,address,uint256,uint256,uint256,uint256)',
)
VESTING_ESCROW_CREATED_V3: Final = keccak(
    text='VestingEscrowCreated(address,address,address,address,uint256,uint256,uint256,uint256,bool)',
)
TOKEN_VESTING_ESCROW_CREATED: Final = keccak(
    text='TokenVestingEscrowCreated(address,address,address,address,address,uint256,uint256,uint256,uint256,bool)',
)
ERC4626_VESTING_ESCROW_CREATED: Final = keccak(
    text='ERC4626VestingEscrowCreated(address,address,address,address,address,address,address,uint256,uint256,uint256,uint256,uint256,bool)',
)

CLAIM: Final = keccak(text='Claim(address,uint256)')
PRINCIPAL_CLAIM: Final = keccak(text='PrincipalClaim(address,uint256,uint256)')
YIELD_CLAIM: Final = keccak(text='YieldClaim(address,uint256)')
RUG_PULL: Final = keccak(text='RugPull(address,uint256)')
REVOKED_V3: Final = keccak(text='Revoked(address,address,uint256,uint256)')
REVOKED_V4_TOKEN: Final = keccak(text='Revoked(address,address,address,uint256,uint256)')
REVOKED_V4_ERC4626: Final = keccak(
    text='Revoked(address,address,address,uint256,uint256,uint256)',
)
DISOWNED: Final = keccak(text='Disowned(address)')
SET_OPEN_CLAIM: Final = keccak(text='SetOpenClaim(bool)')
REVOCATION_RENOUNCED: Final = keccak(text='RevocationRenounced(address)')
PERMISSIONLESS_CLAIMS_SET: Final = keccak(text='PermissionlessClaimsSet(bool)')
