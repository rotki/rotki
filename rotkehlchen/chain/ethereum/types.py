from typing import Any, Dict, List, NamedTuple, Tuple, Type, Union

from eth_typing import HexAddress, HexStr
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal

from rotkehlchen.types import ChecksumEthAddress


ETHERSCAN_NODE_NAME = 'etherscan'


def string_to_ethereum_address(value: str) -> ChecksumEthAddress:
    """This is a conversion without any checks of a string to ethereum address

    Is only used for typing.
    """
    return ChecksumEthAddress(HexAddress(HexStr(value)))


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

    address: ChecksumEthAddress
    abi: List[Any]
    method_name: str
    arguments: List[Any]


class WeightedNode(NamedTuple):
    node_info: NodeName
    active: bool
    weight: FVal

    def serialize(self) -> Dict[str, Union[str, Union[str, int]]]:
        return {
            'node': self.node_info.name,
            'endpoint': self.node_info.endpoint,
            'weight': (self.weight * 100).to_int(exact=False),
            'owned': self.node_info.owned,
            'active': self.active,
        }

    def serialize_for_db(self):
        if self.weight == ZERO:
            weight_sring = '0.0'
        else:
            weight_sring = str(self.weight)
        return (
            self.node_info.name,
            self.node_info.endpoint,
            self.node_info.owned,
            self.active,
            weight_sring,
        )

    @classmethod
    def deserialize(
        cls: Type['WeightedNode'],
        data: Dict[str, str],
    ) -> 'WeightedNode':
        return WeightedNode(
            node_info=NodeName(
                name=data['node'],
                endpoint=data['endpoint'],
                owned=bool(data['owned']),
            ),
            weight=FVal(data['weight']) / 100,
            active=bool(data['active']),
        )
