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

    @property
    def label(self) -> str:
        if self is LidoCsmStakingModule.CSM:
            return 'Lido CSM'
        return 'Lido CSM 0x02'


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

# Counterparty identifier for Lido CSM
CPT_LIDO_CSM: Final = 'lido-csm'

# CSModule events. CSM v1 emitted NodeOperatorAdded without the extendedManagerPermissions flag
NODE_OPERATOR_ADDED: Final = b"\xf1{\xafs\xd4k\n\x80\x15|>\xa3\xdd\xa1\xbf\x08\x1ap'2\xd5?\xf1r\x0f\x85\xe5]\x9f\t\x97\xc0"  # noqa: E501
NODE_OPERATOR_ADDED_V1: Final = b'\xf3Y\x82\xc8O\xdc\x94\xf5\x8dH\xe9\x01\xc5LaX\x04\xcf}y9\xb9\xb8\xf7l\xe4\xd4Y5Ncc'  # noqa: E501
NODE_OPERATOR_MANAGER_ADDRESS_CHANGED: Final = b'\x86 !\xf24I\xd6\xe8Qhg\xbd\x83\x9b\xe1Z=\x86\x98\xa7V\x1c\\,5\x06\x90t\xb7\xe9\x1ea'  # noqa: E501
NODE_OPERATOR_REWARD_ADDRESS_CHANGED: Final = b'\x06\x9a\xc7\xcd\x820\xdb\x01[rP\xc8\xe5BQI\xcf\x1a>\x91-\x95i\xf4\x97\x16^U\xb3\xb6\xb7\xb2'  # noqa: E501
SIGNING_KEY_ADDED: Final = b'\xc7z\x17\xd6\xb8W\xab\xe6\xd6\xe6\xc3s\x01b\x1b\xc7,M\xd5/\xa8\x83\x0f\xb5M\xfaq\\\x04\x91\x1a\x89'  # noqa: E501

# CSAccounting events
BOND_DEPOSITED_ETH: Final = b'\x16\xecQ\x16)T$\xde\xc7\xfdR\xc8}\x99q\xa9c\xea\x7fY\xf7A\xad\x9a\xd4h\xf01 U\xdcI'  # noqa: E501
BOND_DEPOSITED_STETH: Final = b'\xee1\xeb\xba)\xfdTq"~B\xfd\x8c\xa6!\xa8\x92\xd6\x89\x90\x18\x92\xcb\x8f\xeb\xb0?\xe8\x02\xc3!K'  # noqa: E501
BOND_DEPOSITED_WSTETH: Final = b"ev\xbb\xc9\xc5\xb4x\xbf\x97\x17\xdc=+\xcbH^_\xf0r}\xf7|rU\x87'Y\x7f6\t\xd3\xf1"  # noqa: E501
BOND_CLAIMED_STETH: Final = b'>:\x13\x98\xfeqW^\xd0\xc1z\x80\xcd\x9dF\xadhL,u\xc2\xfa\xd7\xb0\xe7\xdd\xe1^x\xab"\xd3'  # noqa: E501
BOND_CLAIMED_WSTETH: Final = b'\xe6\xa8\xc0dG\xe0ZA.^\x95\x81\xe0\x88\x94\x1f9\x94\xdb=\x8a\x9b\xfd2u\xb3\x8dw\xac\xac\xaf\xac'  # noqa: E501
BOND_CLAIMED_UNSTETH: Final = b'&g:\x9d\x01\x8b!\x19-\x08\xee\x147{y\x8f\x11\xb9\xe5\xb1^\xa1U\x9c\x11\x02eqk\x89\x85\xb5'  # noqa: E501

# CSFeeDistributor events. CSM v1 emitted FeeDistributed instead of OperatorFeeDistributed
OPERATOR_FEE_DISTRIBUTED: Final = b'Kz\xb1\xc1\x92&~\x835\r\x06I\n\x85+\x8d\xbb\xb2[\xfa\x00\xfd\x06[\x18b\xcfz\xcc\xd2\xab\x90'  # noqa: E501
FEE_DISTRIBUTED_V1: Final = b'a\x93\nl\x15S\xea\xb5\x9dWf\xdan\x1b\xab\x8e\xba\x98*\xec\x84\x8a\xe7h4R\xf4\xa6B;nJ'  # noqa: E501
