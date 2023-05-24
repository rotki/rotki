from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.tokens import EvmTokens
from rotkehlchen.constants.assets import A_POLYGON_POS_MATIC
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

    from .node_inquirer import PolygonPOSInquirer


class PolygonPOSTokens(EvmTokens):

    def __init__(self, database: 'DBHandler', polygon_pos_inquirer: 'PolygonPOSInquirer') -> None:
        super().__init__(database=database, evm_inquirer=polygon_pos_inquirer)

    # -- methods that need to be implemented per chain
    def _per_chain_token_exceptions(self) -> set[ChecksumEvmAddress]:
        """
        Polygon MATIC ERC20 token mirrors the user's balance on the chain.
        To avoid double counting, we exclude the token from the balance query.
        """
        return {A_POLYGON_POS_MATIC.resolve_to_evm_token().evm_address}
