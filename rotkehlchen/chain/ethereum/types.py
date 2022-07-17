from dataclasses import dataclass
from typing import Any, Dict, List, NamedTuple, Tuple, Type

from eth_typing import HexAddress, HexStr

from rotkehlchen.fval import FVal
from rotkehlchen.types import ChecksumEvmAddress

ETHERSCAN_NODE_NAME = 'etherscan'


def string_to_evm_address(value: str) -> ChecksumEvmAddress:
    """This is a conversion without any checks of a string to ethereum address

    Is only used for typing.
    """
    return ChecksumEvmAddress(HexAddress(HexStr(value)))


class NodeName(NamedTuple):
    """Various node types

    Some open nodes taken from here: https://ethereumnodes.com/
    Related issue: https://github.com/rotki/rotki/issues/1716
    """
    name: str
    endpoint: str
    owned: bool

    def serialize(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'endpoint': self.endpoint,
            'owned': self.owned,
        }


class EnsContractParams(NamedTuple):
    """Parameters for a contract"""

    address: ChecksumEvmAddress
    abi: List[Any]
    method_name: str
    arguments: List[Any]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class WeightedNode:
    node_info: NodeName
    active: bool
    weight: FVal
    identifier: int = 0

    def serialize(self) -> Dict[str, Any]:
        return {
            'identifier': self.identifier,
            'name': self.node_info.name,
            'endpoint': self.node_info.endpoint,
            'weight': self.weight.to_percentage(precision=2, with_perc_sign=False),
            'owned': self.node_info.owned,
            'active': self.active,
        }

    def serialize_for_db(self) -> Tuple[str, str, bool, bool, str]:
        return (
            self.node_info.name,
            self.node_info.endpoint,
            self.node_info.owned,
            self.active,
            str(self.weight),
        )

    @classmethod
    def deserialize(
        cls: Type['WeightedNode'],
        data: Dict[str, str],
    ) -> 'WeightedNode':
        return WeightedNode(
            identifier=int(data['identifier']),
            node_info=NodeName(
                name=data['node'],
                endpoint=data['endpoint'],
                owned=bool(data['owned']),
            ),
            weight=FVal(data['weight']) / 100,
            active=bool(data['active']),
        )
