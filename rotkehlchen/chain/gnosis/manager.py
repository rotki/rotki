from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.manager import CurveManagerMixin, EvmManager
from rotkehlchen.chain.evm.types import string_to_evm_address

from .accountant import GnosisAccountingAggregator
from .decoding.decoder import GnosisTransactionDecoder
from .tokens import GnosisTokens
from .transactions import GnosisTransactions

if TYPE_CHECKING:
    from rotkehlchen.premium.premium import Premium

    from .node_inquirer import GnosisInquirer


class GnosisManager(EvmManager, CurveManagerMixin):

    def __init__(self, node_inquirer: 'GnosisInquirer', premium: 'Premium | None' = None) -> None:
        transactions = GnosisTransactions(
            gnosis_inquirer=node_inquirer,
            database=node_inquirer.database,
        )
        super().__init__(
            node_inquirer=node_inquirer,
            transactions=transactions,
            tokens=GnosisTokens(
                database=node_inquirer.database,
                evm_inquirer=node_inquirer,
                token_exceptions={
                    string_to_evm_address('0x1497440B4E92DC4ca0F76223b28C20Cb9cB8a0f1'),  # Constant Inflow Token  # noqa: E501
                    string_to_evm_address('0xfC00dEE8a980110c5608A823a5B3af3872635456'),  # Constant Outflow Token  # noqa: E501
                },
            ),
            transactions_decoder=GnosisTransactionDecoder(
                database=node_inquirer.database,
                gnosis_inquirer=node_inquirer,
                transactions=transactions,
                premium=premium,
            ),
            accounting_aggregator=GnosisAccountingAggregator(
                node_inquirer=node_inquirer,
                msg_aggregator=transactions.msg_aggregator,
            ),
        )
        self.node_inquirer: GnosisInquirer  # just to make the type specific
