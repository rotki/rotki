from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.manager import CurveManagerMixin, EvmManager
from rotkehlchen.chain.evm.types import string_to_evm_address

from .accountant import ArbitrumOneAccountingAggregator
from .decoding.decoder import ArbitrumOneTransactionDecoder
from .tokens import ArbitrumOneTokens
from .transactions import ArbitrumOneTransactions

if TYPE_CHECKING:

    from .node_inquirer import ArbitrumOneInquirer


class ArbitrumOneManager(EvmManager, CurveManagerMixin):

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
                evm_inquirer=node_inquirer,
                token_exceptions={
                    string_to_evm_address('0x0043d7c85C8b96a49A72A92C0B48CdC4720437d7'),  # Constant Inflow Token  # noqa: E501
                    string_to_evm_address('0x051e766e2d8dc65ae2bFCF084A50AD0447634227'),  # Constant Outflow Token  # noqa: E501
                },
            ),
            transactions_decoder=ArbitrumOneTransactionDecoder(
                database=node_inquirer.database,
                arbitrum_inquirer=node_inquirer,
                transactions=transactions,
            ),
            accounting_aggregator=ArbitrumOneAccountingAggregator(
                node_inquirer=node_inquirer,
                msg_aggregator=transactions.msg_aggregator,
            ),
        )
        self.node_inquirer: ArbitrumOneInquirer  # just to make the type specific
