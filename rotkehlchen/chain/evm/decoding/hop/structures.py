
from typing import NamedTuple

from rotkehlchen.types import ChecksumEvmAddress


class HopBridgeEventData(NamedTuple):
    """
    A dataclass representing a bridge in the Hop protocol for cross-chain transactions.
    https://github.com/hop-protocol/hop/blob/d842c19bacff7dbe0b2fda71763f5462a943a146/packages/sdk/src/addresses/mainnet.ts

    Attributes:
        asset (Asset): The asset identifier that is being transferred using this Hop bridge.
        hop_asset (Asset): The intermediate asset identifer that represents the real asset
            being transferred. It will be swapped to the real asset at the end of the bridge.
        amm_wrapper (ChecksumEvmAddress | None): The address of the AMM wrapper used for
            asset bridging. This field is optional and can be None if no AMM wrapper is used.
        saddle_swap (ChecksumEvmAddress | None): The address of the Token Swap used for
            swaping bridging assets to native assets.
    """
    identifier: str
    hop_identifier: str | None = None
    amm_wrapper: ChecksumEvmAddress | None = None
    saddle_swap: ChecksumEvmAddress | None = None
