from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.manager import EvmManager

from .accountant import SonicAccountingAggregator
from .decoding.decoder import SonicTransactionDecoder
from .tokens import SonicTokens
from .transactions import SonicTransactions

if TYPE_CHECKING:
    from rotkehlchen.premium.premium import Premium

    from .node_inquirer import SonicInquirer


class SonicManager(EvmManager):

    def __init__(self, node_inquirer: SonicInquirer, premium: Premium | None = None) -> None:
        super().__init__(
            node_inquirer=node_inquirer,
            transactions=(transactions := SonicTransactions(
                evm_inquirer=node_inquirer,
                database=node_inquirer.database,
            )),
            tokens=SonicTokens(
                database=node_inquirer.database,
                evm_inquirer=node_inquirer,
            ),
            transactions_decoder=SonicTransactionDecoder(
                database=node_inquirer.database,
                sonic_inquirer=node_inquirer,
                transactions=transactions,
                premium=premium,
            ),
            accounting_aggregator=SonicAccountingAggregator(
                node_inquirer=node_inquirer,
                msg_aggregator=transactions.msg_aggregator,
            ),
        )
        self.node_inquirer: SonicInquirer  # just to make the type specific
