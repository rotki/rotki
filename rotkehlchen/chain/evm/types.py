from dataclasses import dataclass
from typing import Any, Literal, NamedTuple, Optional

from eth_typing import HexAddress, HexStr
from web3 import Web3

from rotkehlchen.fval import FVal
from rotkehlchen.types import SUPPORTED_CHAIN_IDS, ChecksumEvmAddress, SupportedBlockchain


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
    blockchain: Literal[SupportedBlockchain.ETHEREUM, SupportedBlockchain.KUSAMA, SupportedBlockchain.POLKADOT, SupportedBlockchain.AVALANCHE, SupportedBlockchain.OPTIMISM]  # noqa: E501

    def serialize(self) -> dict[str, Any]:
        return {
            'name': self.name,
            'endpoint': self.endpoint,
            'owned': self.owned,
            'blockchain': self.blockchain.value,
        }


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class WeightedNode:
    node_info: NodeName
    active: bool
    weight: FVal
    identifier: int = 0

    def serialize(self) -> dict[str, Any]:
        return {
            'identifier': self.identifier,
            'name': self.node_info.name,
            'endpoint': self.node_info.endpoint,
            'weight': self.weight.to_percentage(precision=2, with_perc_sign=False),
            'owned': self.node_info.owned,
            'active': self.active,
            'blockchain': self.node_info.blockchain.value,
        }

    def serialize_for_db(self) -> tuple[str, str, bool, bool, str, str]:
        return (
            self.node_info.name,
            self.node_info.endpoint,
            self.node_info.owned,
            self.active,
            str(self.weight),
            self.node_info.blockchain.value,
        )

    @classmethod
    def deserialize(
            cls: type['WeightedNode'],
            data: dict[str, str],
    ) -> 'WeightedNode':
        return WeightedNode(
            identifier=int(data['identifier']),
            node_info=NodeName(
                name=data['node'],
                endpoint=data['endpoint'],
                owned=bool(data['owned']),
                blockchain=SupportedBlockchain(data['blockchain']),  # type: ignore
            ),
            weight=FVal(data['weight']) / 100,
            active=bool(data['active']),
        )


class EvmAccount(NamedTuple):
    address: ChecksumEvmAddress
    chain_id: Optional[SUPPORTED_CHAIN_IDS] = None


class Web3Node(NamedTuple):
    """This represents an EVM node with its capabilities."""
    web3_instance: Web3
    is_pruned: bool
    is_archive: bool
