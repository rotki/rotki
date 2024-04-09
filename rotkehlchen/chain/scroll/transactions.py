from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.l2_with_l1_fees.transactions import L2WithL1FeesTransactions

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

    from .node_inquirer import ScrollInquirer


class ScrollTransactions(L2WithL1FeesTransactions):

    def __init__(
            self,
            scroll_inquirer: 'ScrollInquirer',
            database: 'DBHandler',
    ) -> None:
        super().__init__(node_inquirer=scroll_inquirer, database=database)
