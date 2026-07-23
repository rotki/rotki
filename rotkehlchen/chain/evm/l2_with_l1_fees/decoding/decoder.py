import logging
from abc import ABC
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.decoder import EventDecoderFunction, EVMTransactionDecoder
from rotkehlchen.chain.evm.l2_with_l1_fees.decoding.interfaces import L2WithL1FeesDecoderInterface
from rotkehlchen.db.l2withl1feestx import DBL2WithL1FeesTx
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import from_wei

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
    from rotkehlchen.chain.evm.l2_with_l1_fees.transactions import L2WithL1FeesTransactions
    from rotkehlchen.chain.evm.l2_with_l1_fees.types import L2WithL1FeesTransaction
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.externalapis.monerium import Monerium
    from rotkehlchen.premium.premium import Premium

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class L2WithL1FeesTransactionDecoder(EVMTransactionDecoder, ABC):
    """
    An intermediary decoder class to be inherited by L2 chains that have an extra L1 Fee structure.
    """

    def __init__(
            self,
            database: DBHandler,
            node_inquirer: EvmNodeInquirer,
            transactions: L2WithL1FeesTransactions,
            value_asset: AssetWithOracles,
            event_rules: list[EventDecoderFunction],
            misc_counterparties: list[CounterpartyDetails],
            base_tools: BaseEvmDecoderTools,
            premium: Premium | None = None,
            dbevmtx_class: type[DBL2WithL1FeesTx] = DBL2WithL1FeesTx,
            monerium: Monerium | None = None,
    ):
        self.transaction_type_mappings: dict[int, list[tuple[int, Callable]]] = defaultdict(list)
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
            monerium=monerium,
        )

    def _calculate_fees(self, tx: L2WithL1FeesTransaction) -> FVal:  # type: ignore[override]
        return from_wei(FVal(tx.gas_used * tx.gas_price + tx.l1_fee))

    def _chain_specific_post_decoding_rules(
            self,
            transaction: L2WithL1FeesTransaction,  # type: ignore[override]
    ) -> list[tuple[int, Callable]]:
        # return a copy since the caller extends and sorts the returned list
        return list(self.transaction_type_mappings.get(transaction.tx_type, []))

    def _chain_specific_decoder_initialization(
            self,
            decoder: EvmDecoderInterface,
    ) -> None:
        """Initialize the transaction type mappings"""
        if not isinstance(decoder, L2WithL1FeesDecoderInterface):
            return  # not all decoders have tx type specific rules. Some common decoders exist for all chains  # noqa: E501

        txtype_mapping = decoder.decoding_by_tx_type()
        for txtype, rules in txtype_mapping.items():
            self.transaction_type_mappings[txtype].extend(rules)
