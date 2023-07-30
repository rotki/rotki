from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.manager import EvmManager

from .decoding.decoder import OptimismTransactionDecoder
from .tokens import OptimismTokens
from .transactions import OptimismTransactions

if TYPE_CHECKING:

    from .node_inquirer import OptimismInquirer


class OptimismManager(EvmManager):

    def __init__(
            self,
            node_inquirer: 'OptimismInquirer',
    ) -> None:
        transactions = OptimismTransactions(
            optimism_inquirer=node_inquirer,
            database=node_inquirer.database,
        )
        super().__init__(
            node_inquirer=node_inquirer,
            transactions=transactions,
            tokens=OptimismTokens(
                database=node_inquirer.database,
                optimism_inquirer=node_inquirer,
            ),
            transactions_decoder=OptimismTransactionDecoder(
                database=node_inquirer.database,
                optimism_inquirer=node_inquirer,
                transactions=transactions,
            ),
        )
        self.node_inquirer: OptimismInquirer  # just to make the type specific
