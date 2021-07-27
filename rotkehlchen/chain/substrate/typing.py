from enum import Enum
from typing import Dict, List, NamedTuple, NewType, Tuple, Type, TypeVar, Union

from substrateinterface import SubstrateInterface

KusamaAddress = NewType('KusamaAddress', str)
PolkadotAddress = NewType('PolkadotAddress', str)
# SubstrateAddress = Union[KusamaAddress, PolkadotAddress]
SubstrateAddress = TypeVar('SubstrateAddress', KusamaAddress, PolkadotAddress)
SubstratePublicKey = NewType('SubstratePublicKey', str)

SubstrateChainId = NewType('SubstrateChainId', str)
BlockNumber = NewType('BlockNumber', int)


class KusamaNodeName(Enum):
    """Public nodes for Kusama.

    Taken from: https://github.com/polkadot-js/apps/blob/master/packages/apps-config/src/endpoints/production.ts#L34
    """  # noqa: E501
    OWN = 0
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
    """  # noqa: E501
    OWN = 0
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


class SubstrateInterfaceAttributes(NamedTuple):
    type_registry_preset: str


class SubstrateChain(Enum):
    """Supported Substrate chains.
    """
    KUSAMA = 1
    POLKADOT = 2

    def __str__(self) -> SubstrateChainId:
        """Return the official chain identifier/name"""
        if self == SubstrateChain.KUSAMA:
            return SubstrateChainId('Kusama')
        if self == SubstrateChain.POLKADOT:
            return SubstrateChainId('Polkadot')

        raise AssertionError(f'Unexpected Chain: {self}')

    def chain_explorer_api(self) -> str:
        """Return the explorer API.

        NB: this simplified implementation relies on Subscan API supporting all
        the chains we introduce.
        """
        if self == SubstrateChain.KUSAMA:
            return 'https://kusama.api.subscan.io/api'
        if self == SubstrateChain.POLKADOT:
            return 'https://polkadot.api.subscan.io/api'

        raise AssertionError(f'Unexpected Chain: {self}')

    def substrate_interface_attributes(self) -> SubstrateInterfaceAttributes:
        """Return the attributes for instantiating SubstrateInterface.
        """
        if self == SubstrateChain.KUSAMA:
            return SubstrateInterfaceAttributes(type_registry_preset='kusama')
        if self == SubstrateChain.POLKADOT:
            return SubstrateInterfaceAttributes(type_registry_preset='polkadot')

        raise AssertionError(f'Unexpected Chain: {self}')

    def blocks_threshold(self) -> BlockNumber:
        """Return the blocks difference that marks a node as unsynced.
        """
        if self in (SubstrateChain.KUSAMA, SubstrateChain.POLKADOT):
            return BlockNumber(10)

        raise AssertionError(f'Unexpected Chain: {self}')

    def node_name_type(self) -> Union[Type[KusamaNodeName], Type[PolkadotNodeName]]:
        """Return the NodeName enum.
        """
        if self == SubstrateChain.KUSAMA:
            return KusamaNodeName
        if self == SubstrateChain.POLKADOT:
            return PolkadotNodeName
        raise AssertionError(f'Unexpected Chain: {self}')


class NodeNameAttributes(NamedTuple):
    node_interface: SubstrateInterface
    weight_block: BlockNumber


DictNodeNameNodeAttributes = Dict[NodeName, NodeNameAttributes]
NodesCallOrder = List[Tuple[NodeName, NodeNameAttributes]]
