from enum import Enum
from typing import NamedTuple, NewType

from substrateinterface import SubstrateInterface

SubstrateAddress = NewType('SubstrateAddress', str)
SubstratePublicKey = NewType('SubstratePublicKey', str)
BlockNumber = NewType('BlockNumber', int)


# TODO: This is an idiotic design. KusamaNodeName and PolkadotName need to be combined or go away

class KusamaNodeName(Enum):
    """Public nodes for Kusama.

    Taken from: https://www.comparenodes.com/library/public-endpoints/assethub/
    """
    OWN = 0  # make sure it's always 0 to match PolkadotNodeName
    DWELLIR = 1
    ONFINALITY = 2
    STAKEWORLD = 3

    def __str__(self) -> str:
        if self == KusamaNodeName.OWN:
            return 'own node'
        if self == KusamaNodeName.DWELLIR:
            return 'dwellir'
        if self == KusamaNodeName.ONFINALITY:
            return 'onfinality'
        if self == KusamaNodeName.STAKEWORLD:
            return 'stakeworld'

        raise AssertionError(f'Unexpected KusamaNodeName: {self}')

    def endpoint(self) -> str:
        if self == KusamaNodeName.OWN:
            raise NotImplementedError(
                'The endpoint url for a substrate own node must be got either '
                'via "own_rpc_endpoint" or the specific db setting',
            )
        if self == KusamaNodeName.DWELLIR:
            return 'https://asset-hub-kusama-rpc.n.dwellir.com/'
        if self == KusamaNodeName.ONFINALITY:
            return 'https://assethub-kusama.api.onfinality.io/public'
        if self == KusamaNodeName.STAKEWORLD:
            return 'https://ksm-rpc.stakeworld.io/assethub'
        raise AssertionError(f'Unexpected KusamaNodeName: {self}')

    def is_owned(self) -> bool:
        return self.value == 0


class PolkadotNodeName(Enum):
    """Public nodes for Polkadot.

    Taken from: https://www.comparenodes.com/library/public-endpoints/assethub/
    """
    OWN = 0  # make sure it's always 0 to match KusamaNodeName
    DWELLIR = 1
    ONFINALITY = 2
    STAKEWORLD = 3

    def __str__(self) -> str:
        if self == PolkadotNodeName.OWN:
            return 'own node'
        if self == PolkadotNodeName.DWELLIR:
            return 'dwellir'
        if self == PolkadotNodeName.ONFINALITY:
            return 'onfinality'
        if self == PolkadotNodeName.STAKEWORLD:
            return 'stakeworld'

        raise AssertionError(f'Unexpected PolkadotNodeName: {self}')

    def endpoint(self) -> str:
        if self == PolkadotNodeName.OWN:
            raise NotImplementedError(
                'The endpoint url for a substrate own node must be got either '
                'via "own_rpc_endpoint" or the specific db setting',
            )
        if self == PolkadotNodeName.DWELLIR:
            return 'https://asset-hub-polkadot-rpc.n.dwellir.com/'
        if self == PolkadotNodeName.ONFINALITY:
            return 'https://statemint.api.onfinality.io/public'
        if self == PolkadotNodeName.STAKEWORLD:
            return 'https://dot-rpc.stakeworld.io/assethub'
        raise AssertionError(f'Unexpected PolkadotNodeName: {self}')

    def is_owned(self) -> bool:
        return self.value == 0


NodeName = KusamaNodeName | PolkadotNodeName


class NodeNameAttributes(NamedTuple):
    node_interface: SubstrateInterface
    weight_block: BlockNumber


DictNodeNameNodeAttributes = dict[NodeName, NodeNameAttributes]
NodesCallOrder = list[tuple[NodeName, NodeNameAttributes]]
