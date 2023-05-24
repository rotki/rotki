from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.tokens import EvmTokens
from rotkehlchen.constants.assets import A_OPTIMISM_ETH
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

    from .node_inquirer import OptimismInquirer


class OptimismTokens(EvmTokens):

    def __init__(self, database: 'DBHandler', optimism_inquirer: 'OptimismInquirer') -> None:
        super().__init__(database=database, evm_inquirer=optimism_inquirer)

    # -- methods that need to be implemented per chain
    def _per_chain_token_exceptions(self) -> set[ChecksumEvmAddress]:
        """
        Optimism ETH ERC20 token mirrors the user's balance on the chain.
        To avoid double counting, we exclude the token from the balance query.
        """
        return {A_OPTIMISM_ETH.resolve_to_evm_token().evm_address}
