from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.l2_with_l1_fees.transactions import L2WithL1FeesTransactions

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

    from .node_inquirer import LineaInquirer


class LineaTransactions(L2WithL1FeesTransactions):

    def __init__(
            self,
            linea_inquirer: LineaInquirer,
            database: DBHandler,
    ) -> None:
        super().__init__(node_inquirer=linea_inquirer, database=database)
