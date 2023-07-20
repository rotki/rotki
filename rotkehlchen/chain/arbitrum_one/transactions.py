from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.transactions import EvmTransactions

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

    from .node_inquirer import ArbitrumOneInquirer


class ArbitrumOneTransactions(EvmTransactions):

    def __init__(
            self,
            arbitrum_one_inquirer: 'ArbitrumOneInquirer',
            database: 'DBHandler',
    ) -> None:
        super().__init__(evm_inquirer=arbitrum_one_inquirer, database=database)
