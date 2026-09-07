from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.manager import EvmManager

from .accountant import InkAccountingAggregator
from .decoding.decoder import InkTransactionDecoder
from .tokens import InkTokens
from .transactions import InkTransactions

if TYPE_CHECKING:
    from rotkehlchen.premium.premium import Premium

    from .node_inquirer import InkInquirer


class InkManager(EvmManager):

    def __init__(self, node_inquirer: InkInquirer, premium: Premium | None = None) -> None:
        super().__init__(
            node_inquirer=node_inquirer,
            transactions=(transactions := InkTransactions(
                ink_inquirer=node_inquirer,
                database=node_inquirer.database,
            )),
            tokens=InkTokens(
                database=node_inquirer.database,
                evm_inquirer=node_inquirer,
            ),
            transactions_decoder=InkTransactionDecoder(
                database=node_inquirer.database,
                ink_inquirer=node_inquirer,
                transactions=transactions,
                premium=premium,
            ),
            accounting_aggregator=InkAccountingAggregator(
                node_inquirer=node_inquirer,
                msg_aggregator=transactions.msg_aggregator,
            ),
        )
        self.node_inquirer: InkInquirer  # just to make the type specific
