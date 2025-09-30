from dataclasses import dataclass
from typing import Any

from rotkehlchen.types import SolanaAddress


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class SolanaDecodingRules:
    address_mappings: dict[SolanaAddress, tuple[Any, ...]]

    def __add__(self, other: 'SolanaDecodingRules') -> 'SolanaDecodingRules':
        if not isinstance(other, SolanaDecodingRules):
            raise TypeError(
                f'Can only add SolanaDecodingRules to SolanaDecodingRules. Got {type(other)}',
            )

        return SolanaDecodingRules(
            address_mappings=self.address_mappings | other.address_mappings,
        )
