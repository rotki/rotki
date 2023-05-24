from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.transactions import EvmTransactions

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

    from .node_inquirer import PolygonPOSInquirer


class PolygonPOSTransactions(EvmTransactions):

    def __init__(
            self,
            polygon_pos_inquirer: 'PolygonPOSInquirer',
            database: 'DBHandler',
    ) -> None:
        super().__init__(evm_inquirer=polygon_pos_inquirer, database=database)
