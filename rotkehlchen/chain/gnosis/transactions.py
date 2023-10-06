from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.transactions import EvmTransactions

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

    from .node_inquirer import GnosisInquirer


class GnosisTransactions(EvmTransactions):

    def __init__(
            self,
            gnosis_inquirer: 'GnosisInquirer',
            database: 'DBHandler',
    ) -> None:
        super().__init__(evm_inquirer=gnosis_inquirer, database=database)
