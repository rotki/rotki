from typing import Any, Dict, List, NamedTuple, Tuple, Type, Union

from eth_typing import HexAddress, HexStr
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

    @classmethod
    def deserialize_from_db(
        cls: Type['NodeName'],
        node_name: str,
        endpoint: str,
        owned: bool,
    ) -> 'NodeName':
        return cls(
            name=node_name,
            endpoint=endpoint,
            owned=owned,
        )

    def serialize_for_db(self) -> Tuple[str, str, bool]:
        return (self.name, self.endpoint, self.owned)

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
    weight: FVal

    def serialize(self) -> Dict[str, Union[str, Union[str, int]]]:
        return {
            'node': self.node_info.name,
            'endpoint': self.node_info.endpoint,
            'weight': (self.weight * 100).to_int(exact=False),
            'owned': self.node_info.owned,
        }

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
        )
