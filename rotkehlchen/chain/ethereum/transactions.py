from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.transactions import EvmTransactions

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

    from .node_inquirer import EthereumInquirer


class EthereumTransactions(EvmTransactions):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            database: 'DBHandler',
    ) -> None:
        super().__init__(evm_inquirer=ethereum_inquirer, database=database)
