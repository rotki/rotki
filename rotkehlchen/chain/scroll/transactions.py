from typing import TYPE_CHECKING

from rotkehlchen.chain.optimism_superchain.transactions import OptimismSuperchainTransactions

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

    from .node_inquirer import ScrollInquirer


class ScrollTransactions(OptimismSuperchainTransactions):

    def __init__(
            self,
            scroll_inquirer: 'ScrollInquirer',
            database: 'DBHandler',
    ) -> None:
        super().__init__(node_inquirer=scroll_inquirer, database=database)
