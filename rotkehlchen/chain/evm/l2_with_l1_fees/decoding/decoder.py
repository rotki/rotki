import logging
from abc import ABC
from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
from rotkehlchen.chain.evm.decoding.decoder import EventDecoderFunction, EVMTransactionDecoder
from rotkehlchen.chain.evm.l2_with_l1_fees.types import L2WithL1FeesTransaction
from rotkehlchen.db.l2withl1feestx import DBL2WithL1FeesTx
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import from_wei

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.l2_with_l1_fees.node_inquirer import L2WithL1FeesInquirer
    from rotkehlchen.chain.evm.l2_with_l1_fees.transactions import L2WithL1FeesTransactions
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.premium.premium import Premium

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class L2WithL1FeesTransactionDecoder(EVMTransactionDecoder, ABC):
    """
    An intermediary decoder class to be inherited by L2 chains that have an extra L1 Fee structure.
    """

    def __init__(
            self,
            database: 'DBHandler',
            node_inquirer: 'L2WithL1FeesInquirer',
            transactions: 'L2WithL1FeesTransactions',
            value_asset: AssetWithOracles,
            event_rules: list[EventDecoderFunction],
            misc_counterparties: list[CounterpartyDetails],
            base_tools: BaseEvmDecoderTools,
            premium: 'Premium | None' = None,
            dbevmtx_class: type[DBL2WithL1FeesTx] = DBL2WithL1FeesTx,
    ):
        super().__init__(
            database=database,
            evm_inquirer=node_inquirer,
            transactions=transactions,
            value_asset=value_asset,
            event_rules=event_rules,
            misc_counterparties=misc_counterparties,
            base_tools=base_tools,
            premium=premium,
            dbevmtx_class=dbevmtx_class,
        )

    def _calculate_fees(self, tx: L2WithL1FeesTransaction) -> FVal:  # type: ignore[override]
        return from_wei(FVal(tx.gas_used * tx.gas_price + tx.l1_fee))
