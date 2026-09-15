from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.manager import EvmManager

from .accountant import LineaAccountingAggregator
from .decoding.decoder import LineaTransactionDecoder
from .tokens import LineaTokens
from .transactions import LineaTransactions

if TYPE_CHECKING:
    from rotkehlchen.premium.premium import Premium

    from .node_inquirer import LineaInquirer


class LineaManager(EvmManager):

    def __init__(self, node_inquirer: LineaInquirer, premium: Premium | None = None) -> None:
        super().__init__(
            node_inquirer=node_inquirer,
            transactions=(transactions := LineaTransactions(
                linea_inquirer=node_inquirer,
                database=node_inquirer.database,
            )),
            tokens=LineaTokens(
                database=node_inquirer.database,
                evm_inquirer=node_inquirer,
            ),
            transactions_decoder=LineaTransactionDecoder(
                database=node_inquirer.database,
                linea_inquirer=node_inquirer,
                transactions=transactions,
                premium=premium,
            ),
            accounting_aggregator=LineaAccountingAggregator(
                node_inquirer=node_inquirer,
                msg_aggregator=transactions.msg_aggregator,
            ),
        )
        self.node_inquirer: LineaInquirer  # just to make the type specific
