import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.transactions import EthereumTransactions
from rotkehlchen.chain.evm.manager import CurveManagerMixin, EvmManager
from rotkehlchen.logging import RotkehlchenLogsAdapter

from .accountant import EthereumAccountingAggregator
from .decoding.decoder import EthereumTransactionDecoder
from .tokens import EthereumTokens

if TYPE_CHECKING:
    from rotkehlchen.externalapis.beaconchain.service import BeaconChain

    from .node_inquirer import EthereumInquirer


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EthereumManager(EvmManager, CurveManagerMixin):
    def __init__(
            self,
            node_inquirer: 'EthereumInquirer',
            beacon_chain: 'BeaconChain | None' = None,
    ) -> None:
        transactions = EthereumTransactions(
            ethereum_inquirer=node_inquirer,
            database=node_inquirer.database,
        )
        super().__init__(
            node_inquirer=node_inquirer,
            transactions=transactions,
            tokens=EthereumTokens(
                database=node_inquirer.database,
                ethereum_inquirer=node_inquirer,
            ),
            transactions_decoder=EthereumTransactionDecoder(
                database=node_inquirer.database,
                ethereum_inquirer=node_inquirer,
                transactions=transactions,
                beacon_chain=beacon_chain,
            ),
            accounting_aggregator=EthereumAccountingAggregator(
                node_inquirer=node_inquirer,
                msg_aggregator=transactions.msg_aggregator,
            ),
        )
        self.node_inquirer: EthereumInquirer  # just to make the type specific
