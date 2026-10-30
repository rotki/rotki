from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.evm.types import ChecksumEvmAddress, string_to_evm_address

if TYPE_CHECKING:
    from eth_typing.abi import ABI

LIDO_STETH_DEPLOYED_BLOCK: Final[int] = 11473216


class LidoCsmStakingModule(IntEnum):
    """Community staking modules rotki tracks, by their Lido StakingRouter module id."""
    CSM = 3
    CSM_0X02 = 5


@dataclass(frozen=True, slots=True)
class LidoCsmModuleContracts:
    """Mainnet proxies of one community staking module. All of them are deployed together."""
    module: ChecksumEvmAddress
    accounting: ChecksumEvmAddress
    fee_distributor: ChecksumEvmAddress
    deployed_block: int


LIDO_CSM_MODULE_CONTRACTS: Final[dict[LidoCsmStakingModule, LidoCsmModuleContracts]] = {
    LidoCsmStakingModule.CSM: LidoCsmModuleContracts(
        module=string_to_evm_address('0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F'),
        accounting=string_to_evm_address('0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da'),
        fee_distributor=string_to_evm_address('0xD99CC66fEC647E68294C6477B40fC7E0F6F618D0'),
        deployed_block=20935462,
    ),
    LidoCsmStakingModule.CSM_0X02: LidoCsmModuleContracts(
        module=string_to_evm_address('0x792Cd25e4aE3578375031FB55e048E163A804F7B'),
        accounting=string_to_evm_address('0x3696dDd942A9e156F5D4728505D1b9a32dCef900'),
        fee_distributor=string_to_evm_address('0x122CdeDD0da630B555050976052C262EA25f8335'),
        deployed_block=26103487,
    ),
}

ACCOUNTING_ABI: Final[ABI] = [{'inputs': [{'name': 'nodeOperatorId', 'type': 'uint256'}], 'name': 'getBondShares', 'outputs': [{'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}, {'inputs': [{'name': 'nodeOperatorId', 'type': 'uint256'}], 'name': 'getBondCurveId', 'outputs': [{'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}, {'inputs': [{'name': 'nodeOperatorId', 'type': 'uint256'}], 'name': 'getBondSummaryShares', 'outputs': [{'name': 'current', 'type': 'uint256'}, {'name': 'required', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}, {'inputs': [{'name': 'nodeOperatorId', 'type': 'uint256'}], 'name': 'getClaimableBondShares', 'outputs': [{'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501

STETH_ABI: Final[ABI] = [{'inputs': [{'name': 'sharesAmount', 'type': 'uint256'}], 'name': 'getPooledEthByShares', 'outputs': [{'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501

CSM_MODULE_ABI: Final[ABI] = [{'inputs': [{'name': 'nodeOperatorId', 'type': 'uint256'}], 'name': 'getNodeOperatorSummary', 'outputs': [{'name': 'targetLimitMode', 'type': 'uint256'}, {'name': 'targetValidatorsCount', 'type': 'uint256'}, {'name': 'stuckValidatorsCount', 'type': 'uint256'}, {'name': 'refundedValidatorsCount', 'type': 'uint256'}, {'name': 'stuckPenaltyEndTimestamp', 'type': 'uint256'}, {'name': 'totalExitedValidators', 'type': 'uint256'}, {'name': 'totalDepositedValidators', 'type': 'uint256'}, {'name': 'depositableValidatorsCount', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501


class LidoCsmOperatorType(IntEnum):
    """Operator categories of the Lido community staking modules.

    The values are rotki's own ids, stored in the DB and returned by the API. They
    match the original CSM's bond curve ids, which are immutable once deployed.
    Other modules number their curves independently, see from_curve_id.
    """
    UNKNOWN = -1
    PERMISSIONLESS = 0
    EARLY_ADOPTER = 1
    ICS = 2
    IDENTIFIED_DVT_CLUSTER = 3

    @property
    def label(self) -> str:
        if self is LidoCsmOperatorType.ICS:
            return 'ICS'
        if self is LidoCsmOperatorType.IDENTIFIED_DVT_CLUSTER:
            return 'Identified DVT Cluster'
        if self is LidoCsmOperatorType.UNKNOWN:
            return 'Unknown'
        return self.name.replace('_', ' ').title()

    @classmethod
    def from_curve_id(
            cls,
            staking_module: LidoCsmStakingModule,
            curve_id: int,
    ) -> LidoCsmOperatorType:
        """Resolve the operator type a bond curve id stands for in the given module.

        Curve ids are numbered per module, so the same id can mean a different operator
        type in each. A curve missing from LIDO_CSM_CURVE_OPERATOR_TYPES is UNKNOWN.
        """
        return LIDO_CSM_CURVE_OPERATOR_TYPES[staking_module].get(curve_id, cls.UNKNOWN)


# Bond curve id -> operator type, per module, as assigned by each module's gates on-chain.
# A new curve is supported by mapping it here, to a new LidoCsmOperatorType if needed.
LIDO_CSM_CURVE_OPERATOR_TYPES: Final[dict[LidoCsmStakingModule, dict[int, LidoCsmOperatorType]]] = {  # noqa: E501
    LidoCsmStakingModule.CSM: {
        0: LidoCsmOperatorType.PERMISSIONLESS,
        1: LidoCsmOperatorType.EARLY_ADOPTER,
        2: LidoCsmOperatorType.ICS,
        3: LidoCsmOperatorType.IDENTIFIED_DVT_CLUSTER,
    },
    LidoCsmStakingModule.CSM_0X02: {
        0: LidoCsmOperatorType.PERMISSIONLESS,
    },
}


FEE_DISTRIBUTOR_ABI: Final[ABI] = [{'inputs': [], 'name': 'treeCid', 'outputs': [{'name': '', 'type': 'string'}], 'stateMutability': 'view', 'type': 'function'}, {'inputs': [{'name': 'nodeOperatorId', 'type': 'uint256'}], 'name': 'distributedShares', 'outputs': [{'name': 'distributed', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501

# Public IPFS gateway used to fetch treeCid documents
LIDO_CSM_IPFS_GATEWAY: Final = 'https://gateway.pinata.cloud/ipfs/'

# Counterparty identifier for Lido CSM
CPT_LIDO_CSM: Final = 'lido-csm'
