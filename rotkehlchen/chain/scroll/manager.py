from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.manager import EvmManager
from rotkehlchen.chain.evm.types import string_to_evm_address

from .accountant import ScrollAccountingAggregator
from .decoding.decoder import ScrollTransactionDecoder
from .tokens import ScrollTokens
from .transactions import ScrollTransactions

if TYPE_CHECKING:
    from rotkehlchen.premium.premium import Premium

    from .node_inquirer import ScrollInquirer


class ScrollManager(EvmManager):

    def __init__(self, node_inquirer: 'ScrollInquirer', premium: 'Premium | None' = None) -> None:
        transactions = ScrollTransactions(
            scroll_inquirer=node_inquirer,
            database=node_inquirer.database,
        )
        super().__init__(
            node_inquirer=node_inquirer,
            transactions=transactions,
            tokens=ScrollTokens(
                database=node_inquirer.database,
                evm_inquirer=node_inquirer,
                token_exceptions={
                    string_to_evm_address('0x8c24Fc82c8fDd763F08E654212fc27e577EbD934'),  # Constant Inflow Token  # noqa: E501
                    string_to_evm_address('0x0de05fe0fF8F5eA9475CA8425e2D05Dd38ccED84'),  # Constant Outflow Token  # noqa: E501
                },
            ),
            transactions_decoder=ScrollTransactionDecoder(
                database=node_inquirer.database,
                scroll_inquirer=node_inquirer,
                transactions=transactions,
                premium=premium,
            ),
            accounting_aggregator=ScrollAccountingAggregator(
                node_inquirer=node_inquirer,
                msg_aggregator=transactions.msg_aggregator,
            ),
        )
        self.node_inquirer: ScrollInquirer  # just to make the type specific
