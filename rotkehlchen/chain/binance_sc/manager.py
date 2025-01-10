from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.manager import CurveManagerMixin, EvmManager

from .accountant import BinanceSCAccountingAggregator
from .decoding.decoder import BinanceSCTransactionDecoder
from .tokens import BinanceSCTokens
from .transactions import BinanceSCTransactions

if TYPE_CHECKING:

    from .node_inquirer import BinanceSCInquirer


class BinanceSCManager(EvmManager, CurveManagerMixin):

    def __init__(self, node_inquirer: 'BinanceSCInquirer') -> None:
        super().__init__(
            node_inquirer=node_inquirer,
            transactions=(transactions := BinanceSCTransactions(
                evm_inquirer=node_inquirer,
                database=node_inquirer.database,
            )),
            tokens=BinanceSCTokens(
                database=node_inquirer.database,
                evm_inquirer=node_inquirer,
            ),
            transactions_decoder=BinanceSCTransactionDecoder(
                database=node_inquirer.database,
                binance_sc_inquirer=node_inquirer,
                transactions=transactions,
            ),
            accounting_aggregator=BinanceSCAccountingAggregator(
                node_inquirer=node_inquirer,
                msg_aggregator=transactions.msg_aggregator,
            ),
        )
        self.node_inquirer: BinanceSCInquirer  # just to make the type specific
