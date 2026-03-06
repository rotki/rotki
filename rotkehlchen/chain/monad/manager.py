from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.manager import EvmManager

from .accountant import MonadAccountingAggregator
from .decoding.decoder import MonadTransactionDecoder
from .tokens import MonadTokens
from .transactions import MonadTransactions

if TYPE_CHECKING:
    from rotkehlchen.premium.premium import Premium

    from .node_inquirer import MonadInquirer


class MonadManager(EvmManager):

    def __init__(self, node_inquirer: 'MonadInquirer', premium: 'Premium | None' = None) -> None:
        super().__init__(
            node_inquirer=node_inquirer,
            transactions=(transactions := MonadTransactions(
                evm_inquirer=node_inquirer,
                database=node_inquirer.database,
            )),
            tokens=MonadTokens(
                database=node_inquirer.database,
                evm_inquirer=node_inquirer,
            ),
            transactions_decoder=MonadTransactionDecoder(
                database=node_inquirer.database,
                monad_inquirer=node_inquirer,
                transactions=transactions,
                premium=premium,
            ),
            accounting_aggregator=MonadAccountingAggregator(
                node_inquirer=node_inquirer,
                msg_aggregator=transactions.msg_aggregator,
            ),
        )
        self.node_inquirer: MonadInquirer  # just to make the type specific
