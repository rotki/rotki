from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.tokens import EvmTokens
from rotkehlchen.chain.optimism.modules.giveth.constants import GIVPOW_ADDRESS
from rotkehlchen.constants.assets import A_OPTIMISM_ETH

if TYPE_CHECKING:
    from rotkehlchen.types import ChecksumEvmAddress


class OptimismTokens(EvmTokens):

    # -- methods that need to be implemented per chain
    def _per_chain_token_exceptions(self) -> set['ChecksumEvmAddress']:
        """
        Optimism ETH ERC20 token mirrors the user's balance on the chain.
        To avoid double counting, we exclude the token from the balance query.
        """
        return super()._per_chain_token_exceptions() | {
            A_OPTIMISM_ETH.resolve_to_evm_token().evm_address,
            GIVPOW_ADDRESS,
        }
