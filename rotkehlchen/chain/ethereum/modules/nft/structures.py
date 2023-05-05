from enum import auto
from typing import TYPE_CHECKING, Any, NamedTuple

from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.mixins.enums import SerializableEnumNameMixin

if TYPE_CHECKING:
    from rotkehlchen.externalapis.opensea import NFT


class NftLpHandling(SerializableEnumNameMixin):
    ALL_NFTS = auto()
    ONLY_LPS = auto()
    EXCLUDE_LPS = auto()


class NFTResult(NamedTuple):
    addresses: dict[ChecksumEvmAddress, list['NFT']]
    entries_found: int
    entries_limit: int

    def serialize(self) -> dict[str, Any]:
        return {
            'addresses': {address: [x.serialize() for x in nfts] for address, nfts in self.addresses.items()},  # noqa: E501
            'entries_found': self.entries_found,
            'entries_limit': self.entries_limit,
        }
