from enum import Enum
from typing import NamedTuple, NewType, Union

from substrateinterface import SubstrateInterface

SubstrateAddress = NewType('SubstrateAddress', str)
SubstratePublicKey = NewType('SubstratePublicKey', str)

SubstrateChainId = NewType('SubstrateChainId', str)
BlockNumber = NewType('BlockNumber', int)


# TODO: This is an idiotic design. KusamaNodeName and PolkadotName need to be combined or go away

class KusamaNodeName(Enum):
    """Public nodes for Kusama.

    Taken from: https://github.com/polkadot-js/apps/blob/master/packages/apps-config/src/endpoints/production.ts#L34
    """
    OWN = 0  # make sure it's always 0 to match PolkadotNodeName
    PARITY = 1
    ONFINALITY = 2
    ELARA = 3

    def __str__(self) -> str:
        if self == KusamaNodeName.OWN:
            return 'own node'
        if self == KusamaNodeName.PARITY:
            return 'parity'
        if self == KusamaNodeName.ONFINALITY:
            return 'onfinality'
        if self == KusamaNodeName.ELARA:
            return 'elara'

        raise AssertionError(f'Unexpected KusamaNodeName: {self}')

    def endpoint(self) -> str:
        if self == KusamaNodeName.OWN:
            raise NotImplementedError(
                'The endpoint url for a substrate own node must be got either '
                'via "own_rpc_endpoint" or the specific db setting',
            )
        if self == KusamaNodeName.PARITY:
            return 'https://kusama-rpc.polkadot.io/'
        if self == KusamaNodeName.ONFINALITY:
            return 'https://kusama.api.onfinality.io/public-https'
        if self == KusamaNodeName.ELARA:
            return 'https://kusama.elara.patract.io'
        raise AssertionError(f'Unexpected KusamaNodeName: {self}')


class PolkadotNodeName(Enum):
    """Public nodes for Polkadot.

    Taken from: https://github.com/polkadot-js/apps/blob/master/packages/apps-config/src/endpoints/production.ts#L34
    """
    OWN = 0  # make sure it's always 0 to match KusamaNodeName
    PARITY = 1
    ONFINALITY = 2
    ELARA = 3

    def __str__(self) -> str:
        if self == PolkadotNodeName.OWN:
            return 'own node'
        if self == PolkadotNodeName.PARITY:
            return 'parity'
        if self == PolkadotNodeName.ONFINALITY:
            return 'onfinality'
        if self == PolkadotNodeName.ELARA:
            return 'elara'

        raise AssertionError(f'Unexpected PolkadotNodeName: {self}')

    def endpoint(self) -> str:
        if self == PolkadotNodeName.OWN:
            raise NotImplementedError(
                'The endpoint url for a substrate own node must be got either '
                'via "own_rpc_endpoint" or the specific db setting',
            )
        if self == PolkadotNodeName.PARITY:
            return 'https://rpc.polkadot.io/'
        if self == PolkadotNodeName.ONFINALITY:
            return 'https://polkadot.api.onfinality.io/public-ws'
        if self == PolkadotNodeName.ELARA:
            return 'https://polkadot.elara.patract.io'
        raise AssertionError(f'Unexpected PolkadotNodeName: {self}')


NodeName = Union[KusamaNodeName, PolkadotNodeName]


class NodeNameAttributes(NamedTuple):
    node_interface: SubstrateInterface
    weight_block: BlockNumber


DictNodeNameNodeAttributes = dict[NodeName, NodeNameAttributes]
NodesCallOrder = list[tuple[NodeName, NodeNameAttributes]]
