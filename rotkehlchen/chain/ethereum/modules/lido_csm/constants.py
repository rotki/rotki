from enum import IntEnum
from typing import Final

from eth_typing.abi import ABI

from rotkehlchen.chain.evm.types import ChecksumEvmAddress, string_to_evm_address

LIDO_STETH_DEPLOYED_BLOCK: Final[int] = 11473216

LIDO_CSM_ACCOUNTING_CONTRACT: Final[ChecksumEvmAddress] = string_to_evm_address('0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da')  # noqa: E501

LIDO_CSM_ACCOUNTING_CONTRACT_DEPLOYED_BLOCK: Final[int] = 20935462

LIDO_CSM_MODULE_CONTRACT: Final[ChecksumEvmAddress] = string_to_evm_address('0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F')  # noqa: E501

LIDO_CSM_MODULE_CONTRACT_DEPLOYED_BLOCK: Final[int] = 20935462

ACCOUNTING_ABI: ABI = [{'inputs': [{'name': 'nodeOperatorId', 'type': 'uint256'}], 'name': 'getBondShares', 'outputs': [{'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}, {'inputs': [{'name': 'nodeOperatorId', 'type': 'uint256'}], 'name': 'getBondCurveId', 'outputs': [{'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}, {'inputs': [{'name': 'nodeOperatorId', 'type': 'uint256'}], 'name': 'getBondSummaryShares', 'outputs': [{'name': 'current', 'type': 'uint256'}, {'name': 'required', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}, {'inputs': [{'name': 'nodeOperatorId', 'type': 'uint256'}], 'name': 'getClaimableBondShares', 'outputs': [{'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501

STETH_ABI: ABI = [{'inputs': [{'name': 'sharesAmount', 'type': 'uint256'}], 'name': 'getPooledEthByShares', 'outputs': [{'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501

CSM_MODULE_ABI: ABI = [{'inputs': [{'name': 'nodeOperatorId', 'type': 'uint256'}], 'name': 'getNodeOperatorTotalDepositedKeys', 'outputs': [{'name': 'totalDepositedKeys', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501


class LidoCsmOperatorType(IntEnum):
    EARLY_ADOPTER = 0
    PERMISSIONLESS = 1
    ICS = 2

    @property
    def label(self) -> str:
        if self is LidoCsmOperatorType.ICS:
            return 'ICS'
        return self.name.replace('_', ' ').title()


# ICS Fee Distributor contract (mainnet) for operator rewards
LIDO_CSM_FEE_DISTRIBUTOR_CONTRACT: Final[ChecksumEvmAddress] = string_to_evm_address('0xD99CC66fEC647E68294C6477B40fC7E0F6F618D0')  # noqa: E501

LIDO_CSM_FEE_DISTRIBUTOR_CONTRACT_DEPLOYED_BLOCK: Final[int] = 20935463

FEE_DISTRIBUTOR_ABI: ABI = [{'inputs': [], 'name': 'treeCid', 'outputs': [{'name': '', 'type': 'string'}], 'stateMutability': 'view', 'type': 'function'}, {'inputs': [{'name': 'nodeOperatorId', 'type': 'uint256'}], 'name': 'distributedShares', 'outputs': [{'name': 'distributed', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501

# Public IPFS gateway used to fetch treeCid documents
LIDO_CSM_IPFS_GATEWAY: Final = 'https://ipfs.io/ipfs/'

# Counterparty identifier for Lido CSM
CPT_LIDO_CSM: Final = 'lido-csm'
