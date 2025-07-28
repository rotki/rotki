from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.manager import CurveManagerMixin, EvmManager
from rotkehlchen.chain.evm.types import string_to_evm_address

from .accountant import PolygonPOSAccountingAggregator
from .decoding.decoder import PolygonPOSTransactionDecoder
from .tokens import PolygonPOSTokens
from .transactions import PolygonPOSTransactions

if TYPE_CHECKING:
    from rotkehlchen.premium.premium import Premium

    from .node_inquirer import PolygonPOSInquirer


class PolygonPOSManager(EvmManager, CurveManagerMixin):

    def __init__(
            self,
            node_inquirer: 'PolygonPOSInquirer',
            premium: 'Premium | None' = None,
    ) -> None:
        transactions = PolygonPOSTransactions(
            polygon_pos_inquirer=node_inquirer,
            database=node_inquirer.database,
        )
        super().__init__(
            node_inquirer=node_inquirer,
            transactions=transactions,
            tokens=PolygonPOSTokens(
                database=node_inquirer.database,
                evm_inquirer=node_inquirer,
                token_exceptions={
                    string_to_evm_address('0x55909bB8cd8276887Aae35118d60b19755201c68'),  # Constant Inflow Token  # noqa: E501
                    string_to_evm_address('0x554e2bbaCF43FD87417b7201A9F1649a3ED89d68'),  # Constant Outflow Token  # noqa: E501
                },
            ),
            transactions_decoder=PolygonPOSTransactionDecoder(
                database=node_inquirer.database,
                polygon_pos_inquirer=node_inquirer,
                transactions=transactions,
                premium=premium,
            ),
            accounting_aggregator=PolygonPOSAccountingAggregator(
                node_inquirer=node_inquirer,
                msg_aggregator=transactions.msg_aggregator,
            ),
        )
        self.node_inquirer: PolygonPOSInquirer  # just to make the type specific
