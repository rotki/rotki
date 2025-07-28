from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.manager import CurveManagerMixin, EvmManager
from rotkehlchen.chain.evm.types import string_to_evm_address

from .accountant import OptimismAccountingAggregator
from .decoding.decoder import OptimismTransactionDecoder
from .tokens import OptimismTokens
from .transactions import OptimismTransactions

if TYPE_CHECKING:
    from rotkehlchen.premium.premium import Premium

    from .node_inquirer import OptimismInquirer


class OptimismManager(EvmManager, CurveManagerMixin):

    def __init__(
            self,
            node_inquirer: 'OptimismInquirer',
            premium: 'Premium | None' = None,
    ) -> None:
        transactions = OptimismTransactions(
            optimism_inquirer=node_inquirer,
            database=node_inquirer.database,
        )
        super().__init__(
            node_inquirer=node_inquirer,
            transactions=transactions,
            tokens=OptimismTokens(
                database=node_inquirer.database,
                evm_inquirer=node_inquirer,
                token_exceptions={
                    string_to_evm_address('0x0C6D90a98426bfD572a5c5Be572a7f6Bd1C5ED76'),  # Constant Inflow Token  # noqa: E501
                    string_to_evm_address('0xFb2b126660BE2fdEBa254b1F6e4348644E8482e7'),  # Constant Outflow Token  # noqa: E501
                },
            ),
            transactions_decoder=OptimismTransactionDecoder(
                database=node_inquirer.database,
                optimism_inquirer=node_inquirer,
                transactions=transactions,
                premium=premium,
            ),
            accounting_aggregator=OptimismAccountingAggregator(
                node_inquirer=node_inquirer,
                msg_aggregator=transactions.msg_aggregator,
            ),
        )
        self.node_inquirer: OptimismInquirer  # just to make the type specific
