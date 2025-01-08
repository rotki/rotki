from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.tokens import EvmTokens

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

    from .node_inquirer import ScrollInquirer


class ScrollTokens(EvmTokens):

    def __init__(self, database: 'DBHandler', scroll_inquirer: 'ScrollInquirer') -> None:
        super().__init__(database=database, evm_inquirer=scroll_inquirer)
