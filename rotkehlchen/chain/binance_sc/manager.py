from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.manager import CurveManagerMixin, EvmManager
from rotkehlchen.chain.evm.types import string_to_evm_address

from .accountant import BinanceSCAccountingAggregator
from .decoding.decoder import BinanceSCTransactionDecoder
from .tokens import BinanceSCTokens
from .transactions import BinanceSCTransactions

if TYPE_CHECKING:
    from rotkehlchen.premium.premium import Premium

    from .node_inquirer import BinanceSCInquirer


class BinanceSCManager(EvmManager, CurveManagerMixin):

    def __init__(self, node_inquirer: 'BinanceSCInquirer', premium: 'Premium | None' = None) -> None:  # noqa: E501
        super().__init__(
            node_inquirer=node_inquirer,
            transactions=(transactions := BinanceSCTransactions(
                evm_inquirer=node_inquirer,
                database=node_inquirer.database,
            )),
            tokens=BinanceSCTokens(
                database=node_inquirer.database,
                evm_inquirer=node_inquirer,
                token_exceptions={
                    string_to_evm_address('0xbF7BCcE8D60A9C3F6bFaEc9346Aa85B9f781a4e9'),  # Constant Inflow Token  # noqa: E501
                    string_to_evm_address('0xcb05535bd212eCFC4B7b9db81d6C2C768b726776'),  # Constant Outflow Token  # noqa: E501
                },
            ),
            transactions_decoder=BinanceSCTransactionDecoder(
                database=node_inquirer.database,
                binance_sc_inquirer=node_inquirer,
                transactions=transactions,
                premium=premium,
            ),
            accounting_aggregator=BinanceSCAccountingAggregator(
                node_inquirer=node_inquirer,
                msg_aggregator=transactions.msg_aggregator,
            ),
        )
        self.node_inquirer: BinanceSCInquirer  # just to make the type specific
