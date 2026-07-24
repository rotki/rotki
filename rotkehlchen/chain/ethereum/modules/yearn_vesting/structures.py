import json
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Literal

from rotkehlchen.serialization.deserialize import deserialize_evm_address

if TYPE_CHECKING:
    from rotkehlchen.types import ChecksumEvmAddress

VestingEscrowVersion = Literal['v0.1.0', 'v0.2.0', 'v0.3.0', 'llamapay-v2', 'v0.4.0']
VestingEscrowKind = Literal['token', 'erc4626']


@dataclass(frozen=True)
class VestingEscrowData:
    """Persistent data emitted when a Yearn vesting escrow is created."""

    escrow: ChecksumEvmAddress
    factory: ChecksumEvmAddress
    version: VestingEscrowVersion
    kind: VestingEscrowKind
    token: ChecksumEvmAddress
    recipient: ChecksumEvmAddress
    funder: ChecksumEvmAddress
    amount: int
    funded_amount: int
    start_time: int
    end_time: int
    cliff_length: int
    revoker: ChecksumEvmAddress | None = None
    yield_recipient: ChecksumEvmAddress | None = None
    asset_token: ChecksumEvmAddress | None = None

    def serialize(self) -> str:
        return json.dumps(asdict(self), separators=(',', ':'), sort_keys=True)

    @classmethod
    def deserialize(cls, value: str) -> VestingEscrowData:
        data = json.loads(value)
        for field_name in (
            'escrow',
            'factory',
            'token',
            'recipient',
            'funder',
            'revoker',
            'yield_recipient',
            'asset_token',
        ):
            if (address := data[field_name]) is not None:
                data[field_name] = deserialize_evm_address(address)

        return cls(**data)
