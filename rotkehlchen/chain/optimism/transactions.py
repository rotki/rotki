from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.transactions import EvmTransactions

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

    from .node_inquirer import OptimismInquirer


class OptimismTransactions(EvmTransactions):

    def __init__(
            self,
            optimism_inquirer: 'OptimismInquirer',
            database: 'DBHandler',
    ) -> None:
        super().__init__(evm_inquirer=optimism_inquirer, database=database)
