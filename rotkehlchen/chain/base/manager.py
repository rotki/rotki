from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.manager import EvmManager

from .accountant import BaseAccountingAggregator
from .decoding.decoder import BaseTransactionDecoder
from .tokens import BaseTokens
from .transactions import BaseTransactions

if TYPE_CHECKING:

    from .node_inquirer import BaseInquirer


class BaseManager(EvmManager):

    def __init__(
            self,
            node_inquirer: 'BaseInquirer',
    ) -> None:
        transactions = BaseTransactions(
            base_inquirer=node_inquirer,
            database=node_inquirer.database,
        )
        super().__init__(
            node_inquirer=node_inquirer,
            transactions=transactions,
            tokens=BaseTokens(
                database=node_inquirer.database,
                base_inquirer=node_inquirer,
            ),
            transactions_decoder=BaseTransactionDecoder(
                database=node_inquirer.database,
                base_inquirer=node_inquirer,
                transactions=transactions,
            ),
            accounting_aggregator=BaseAccountingAggregator(
                node_inquirer=node_inquirer,
                msg_aggregator=transactions.msg_aggregator,
            ),
        )
        self.node_inquirer: BaseInquirer
