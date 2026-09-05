from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.manager import EvmManager

from .accountant import RobinhoodAccountingAggregator
from .decoding.decoder import RobinhoodTransactionDecoder
from .tokens import RobinhoodTokens
from .transactions import RobinhoodTransactions

if TYPE_CHECKING:
    from rotkehlchen.premium.premium import Premium

    from .node_inquirer import RobinhoodInquirer


class RobinhoodManager(EvmManager):

    def __init__(self, node_inquirer: RobinhoodInquirer, premium: Premium | None = None) -> None:
        super().__init__(
            node_inquirer=node_inquirer,
            transactions=(transactions := RobinhoodTransactions(
                evm_inquirer=node_inquirer,
                database=node_inquirer.database,
            )),
            tokens=RobinhoodTokens(
                database=node_inquirer.database,
                evm_inquirer=node_inquirer,
            ),
            transactions_decoder=RobinhoodTransactionDecoder(
                database=node_inquirer.database,
                robinhood_inquirer=node_inquirer,
                transactions=transactions,
                premium=premium,
            ),
            accounting_aggregator=RobinhoodAccountingAggregator(
                node_inquirer=node_inquirer,
                msg_aggregator=transactions.msg_aggregator,
            ),
        )
        self.node_inquirer: RobinhoodInquirer  # just to make the type specific
