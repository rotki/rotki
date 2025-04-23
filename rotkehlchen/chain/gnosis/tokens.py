from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.tokens import EvmTokens
from rotkehlchen.chain.gnosis.modules.giveth.constants import (
    GIVPOW_ADDRESS,
    GNOSIS_GIVPOWERSTAKING_WRAPPER,
)
from rotkehlchen.chain.gnosis.modules.monerium.constants import GNOSIS_MONERIUM_LEGACY_ADDRESSES

if TYPE_CHECKING:
    from rotkehlchen.types import ChecksumEvmAddress


class GnosisTokens(EvmTokens):

    # -- methods that need to be implemented per chain
    def _per_chain_token_exceptions(self) -> set['ChecksumEvmAddress']:
        return super()._per_chain_token_exceptions() | GNOSIS_MONERIUM_LEGACY_ADDRESSES | {
            GIVPOW_ADDRESS, GNOSIS_GIVPOWERSTAKING_WRAPPER,
        }
