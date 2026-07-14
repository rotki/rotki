from typing import TYPE_CHECKING, Literal, NamedTuple

if TYPE_CHECKING:
    from rotkehlchen.types import ChecksumEvmAddress


class TimestampOrBlockRange(NamedTuple):
    range_type: Literal['timestamps', 'blocks']
    from_value: int
    to_value: int


class EvmTokenDetectionData(NamedTuple):
    """Data structure to hold only the information required from evm tokens for
    token detection.
    """
    identifier: str
    address: ChecksumEvmAddress
    decimals: int
