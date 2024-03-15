from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.transactions import EvmTransactions

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

    from .node_inquirer import ScrollInquirer


class ScrollTransactions(EvmTransactions):

    def __init__(
            self,
            scroll_inquirer: 'ScrollInquirer',
            database: 'DBHandler',
    ) -> None:
        super().__init__(evm_inquirer=scroll_inquirer, database=database)
