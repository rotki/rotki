from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.tokens import EvmTokens
from rotkehlchen.chain.polygon_pos.modules.monerium.constants import (
    POLYGON_MONERIUM_LEGACY_ADDRESSES,
)
from rotkehlchen.constants.assets import A_POL

if TYPE_CHECKING:
    from rotkehlchen.types import ChecksumEvmAddress


class PolygonPOSTokens(EvmTokens):

    # -- methods that need to be implemented per chain
    def _per_chain_token_exceptions(self) -> set['ChecksumEvmAddress']:
        """
        Polygon MATIC ERC20 token mirrors the user's balance on the chain.
        To avoid double counting, we exclude the token from the balance query.
        """
        return (
                POLYGON_MONERIUM_LEGACY_ADDRESSES |
                super()._per_chain_token_exceptions() |
                {A_POL.resolve_to_evm_token().evm_address}
        )
