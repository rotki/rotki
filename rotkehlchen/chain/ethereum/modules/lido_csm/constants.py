from typing import Final

from eth_utils import to_checksum_address

from rotkehlchen.types import ChecksumEvmAddress

LIDO_CSM_ACCOUNTING_CONTRACT: Final[ChecksumEvmAddress] = ChecksumEvmAddress(
    to_checksum_address('0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da'),
)

LIDO_CSM_MODULE_CONTRACT: Final[ChecksumEvmAddress] = ChecksumEvmAddress(
    to_checksum_address('0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F'),
)

ACCOUNTING_ABI: Final = [
    {
        'inputs': [{'internalType': 'uint256', 'name': 'nodeOperatorId', 'type': 'uint256'}],
        'name': 'getBondShares',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'uint256', 'name': 'nodeOperatorId', 'type': 'uint256'}],
        'name': 'getBondCurveId',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'uint256', 'name': 'nodeOperatorId', 'type': 'uint256'}],
        'name': 'getBondSummaryShares',
        'outputs': [
            {'internalType': 'uint256', 'name': 'current', 'type': 'uint256'},
            {'internalType': 'uint256', 'name': 'required', 'type': 'uint256'},
        ],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'uint256', 'name': 'nodeOperatorId', 'type': 'uint256'}],
        'name': 'getClaimableBondShares',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
]

STETH_ABI: Final = [
    {
        'inputs': [{'internalType': 'uint256', 'name': 'sharesAmount', 'type': 'uint256'}],
        'name': 'getPooledEthByShares',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
]

CSM_MODULE_ABI: Final = [
    {
        'inputs': [{'internalType': 'uint256', 'name': 'nodeOperatorId', 'type': 'uint256'}],
        'name': 'getNodeOperatorTotalDepositedKeys',
        'outputs': [{'internalType': 'uint256', 'name': 'totalDepositedKeys', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
]

BOND_CURVE_TYPE_LABELS: Final[dict[int, str]] = {
    0: 'Early Adopter',
    1: 'Permissionless',
    2: 'ICS',
}

# ICS Fee Distributor contract (mainnet) for operator rewards
LIDO_CSM_FEE_DISTRIBUTOR_CONTRACT: Final[ChecksumEvmAddress] = ChecksumEvmAddress(
    to_checksum_address('0xD99CC66fEC647E68294C6477B40fC7E0F6F618D0'),
)

FEE_DISTRIBUTOR_ABI: Final = [
    {
        'inputs': [],
        'name': 'treeCid',
        'outputs': [{'internalType': 'string', 'name': '', 'type': 'string'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'uint256', 'name': 'nodeOperatorId', 'type': 'uint256'}],
        'name': 'distributedShares',
        'outputs': [{'internalType': 'uint256', 'name': 'distributed', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
]

# Public IPFS gateway used to fetch treeCid documents
LIDO_CSM_IPFS_GATEWAY: Final = 'https://ipfs.io/ipfs/'

# Counterparty identifier for Lido CSM
CPT_LIDO_CSM: Final = 'lido-csm'
