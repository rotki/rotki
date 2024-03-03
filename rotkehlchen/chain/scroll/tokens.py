from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.tokens import EvmTokens
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

    from .node_inquirer import ScrollInquirer


class ScrollTokens(EvmTokens):

    def __init__(self, database: 'DBHandler', scroll_inquirer: 'ScrollInquirer') -> None:
        super().__init__(database=database, evm_inquirer=scroll_inquirer)

    # -- methods that need to be implemented per chain
    def _per_chain_token_exceptions(self) -> set[ChecksumEvmAddress]:
        return set()
