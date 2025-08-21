import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Literal, NamedTuple

from eth_typing import HexAddress, HexStr

from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.types import (
    EVM_CHAINS_WITH_CHAIN_MANAGER,
    SUPPORTED_CHAIN_IDS,
    SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE,
    ChainID,
    ChecksumEvmAddress,
    SupportedBlockchain,
)


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
    blockchain: EVM_CHAINS_WITH_CHAIN_MANAGER | Literal[SupportedBlockchain.SOLANA]

    def serialize(self) -> dict[str, Any]:
        return {
            'name': self.name,
            'endpoint': self.endpoint,
            'owned': self.owned,
            'blockchain': self.blockchain.serialize(),
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
            'blockchain': self.node_info.blockchain.serialize(),
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
    chain_id: SUPPORTED_CHAIN_IDS | None = None


class EvmlikeAccount(NamedTuple):
    address: ChecksumEvmAddress
    chain: SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE | None = None


ASSET_ID_RE = re.compile(r'eip155:(.*?)/(.*?):(.*)')


def asset_id_is_evm_token(asset_id: str) -> tuple[ChainID, ChecksumEvmAddress] | None:
    """Takes an asset identifier and checks if it's an evm token.

    If it is, returns chain ID and token address. If not it returns None

    **Note**: The address is not deserialized properly here. If it's an invalid address
    this function won't catch it. The caller has to make sure addresses are valid and
    checksummed in the identifier (which they should be).The reason for this is
    to have a "lightweight" function that does not need to convert to checksummed address.
    """
    match = ASSET_ID_RE.search(asset_id)
    if match is None:
        return None

    try:
        chain_id = ChainID.deserialize_from_db(int(match.group(1)))
    except DeserializationError:
        return None

    address = string_to_evm_address(match.group(3))
    return chain_id, address


class RemoteDataQueryStatus(Enum):
    FAILED = auto()
    NEW_DATA = auto()
    NO_UPDATE = auto()
