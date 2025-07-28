from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.manager import CurveManagerMixin, EvmManager
from rotkehlchen.chain.evm.types import string_to_evm_address

from .accountant import BaseAccountingAggregator
from .decoding.decoder import BaseTransactionDecoder
from .tokens import BaseTokens
from .transactions import BaseTransactions

if TYPE_CHECKING:
    from rotkehlchen.premium.premium import Premium

    from .node_inquirer import BaseInquirer


class BaseManager(EvmManager, CurveManagerMixin):

    def __init__(
            self,
            node_inquirer: 'BaseInquirer',
            premium: 'Premium | None' = None,
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
                evm_inquirer=node_inquirer,
                token_exceptions={
                    string_to_evm_address('0x2d51962A9EE4D3C2819EF585eab7412c2a2C31Ac'),  # Constant Inflow Token  # noqa: E501
                    string_to_evm_address('0xD3C78bb5a16Ea4ab584844eeb8F90Ac710c16355'),  # Constant Outflow Token  # noqa: E501
                },
            ),
            transactions_decoder=BaseTransactionDecoder(
                database=node_inquirer.database,
                base_inquirer=node_inquirer,
                transactions=transactions,
                premium=premium,
            ),
            accounting_aggregator=BaseAccountingAggregator(
                node_inquirer=node_inquirer,
                msg_aggregator=transactions.msg_aggregator,
            ),
        )
        self.node_inquirer: BaseInquirer
