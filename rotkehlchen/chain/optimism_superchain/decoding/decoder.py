import logging
from abc import ABCMeta
from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
from rotkehlchen.chain.evm.decoding.decoder import EventDecoderFunction, EVMTransactionDecoder
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.optimism.types import OptimismTransaction
from rotkehlchen.db.optimismtx import DBOptimismTx
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import from_wei

if TYPE_CHECKING:
    from rotkehlchen.chain.optimism_superchain.node_inquirer import OptimismSuperchainInquirer
    from rotkehlchen.chain.optimism_superchain.transactions import OptimismSuperchainTransactions
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class OptimismSuperchainTransactionDecoder(EVMTransactionDecoder, metaclass=ABCMeta):
    """
    An intermediary decoder class to be inherited by chains based on the Optimism Superchain.

    Provides support for handling the layer 1 fee structure common to optimism-based chains.
    """

    def __init__(
            self,
            database: 'DBHandler',
            node_inquirer: 'OptimismSuperchainInquirer',
            transactions: 'OptimismSuperchainTransactions',
            value_asset: AssetWithOracles,
            event_rules: list[EventDecoderFunction],
            misc_counterparties: list[CounterpartyDetails],
            base_tools: BaseDecoderTools,
            dbevmtx_class: type[DBOptimismTx] = DBOptimismTx,
    ):
        super().__init__(
            database=database,
            evm_inquirer=node_inquirer,
            transactions=transactions,
            value_asset=value_asset,
            event_rules=event_rules,
            misc_counterparties=misc_counterparties,
            base_tools=base_tools,
            dbevmtx_class=dbevmtx_class,
        )

    def _calculate_gas_burned(self, tx: OptimismTransaction) -> FVal:  # type: ignore[override]
        return from_wei(FVal(tx.gas_used * tx.gas_price + tx.l1_fee))
