from enum import auto
from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple

from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.mixins.serializableenum import SerializableEnumMixin

if TYPE_CHECKING:
    from rotkehlchen.externalapis.opensea import NFT


class NftLpHandling(SerializableEnumMixin):
    ALL_NFTS = auto()
    ONLY_LPS = auto()
    EXCLUDE_LPS = auto()


class NFTResult(NamedTuple):
    addresses: Dict[ChecksumEvmAddress, List['NFT']]
    entries_found: int
    entries_limit: int

    def serialize(self) -> Dict[str, Any]:
        return {
            'addresses': {address: [x.serialize() for x in nfts] for address, nfts in self.addresses.items()},  # noqa: E501
            'entries_found': self.entries_found,
            'entries_limit': self.entries_limit,
        }
