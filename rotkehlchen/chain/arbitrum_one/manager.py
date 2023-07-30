from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.manager import EvmManager

from .decoding.decoder import ArbitrumOneTransactionDecoder
from .tokens import ArbitrumOneTokens
from .transactions import ArbitrumOneTransactions

if TYPE_CHECKING:

    from .node_inquirer import ArbitrumOneInquirer


class ArbitrumOneManager(EvmManager):

    def __init__(
            self,
            node_inquirer: 'ArbitrumOneInquirer',
    ) -> None:
        transactions = ArbitrumOneTransactions(
            arbitrum_one_inquirer=node_inquirer,
            database=node_inquirer.database,
        )
        super().__init__(
            node_inquirer=node_inquirer,
            transactions=transactions,
            tokens=ArbitrumOneTokens(
                database=node_inquirer.database,
                arbitrum_one_inquirer=node_inquirer,
            ),
            transactions_decoder=ArbitrumOneTransactionDecoder(
                database=node_inquirer.database,
                arbitrum_inquirer=node_inquirer,
                transactions=transactions,
            ),
        )
        self.node_inquirer: ArbitrumOneInquirer  # just to make the type specific
