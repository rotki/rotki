import logging
from abc import ABC
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.decoder import EventDecoderFunction, EVMTransactionDecoder
from rotkehlchen.chain.evm.l2_with_l1_fees.decoding.interfaces import L2WithL1FeesDecoderInterface
from rotkehlchen.chain.evm.l2_with_l1_fees.types import L2WithL1FeesTransaction
from rotkehlchen.db.l2withl1feestx import DBL2WithL1FeesTx, DBResolvedL1FeeFilter
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import from_wei, ts_now

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
    from rotkehlchen.chain.evm.l2_with_l1_fees.transactions import L2WithL1FeesTransactions
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceipt
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.filtering import EvmTransactionsNotDecodedFilterQuery
    from rotkehlchen.externalapis.monerium import Monerium
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.premium.premium import Premium
    from rotkehlchen.types import EvmTransaction, EVMTxHash

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

    def _decode_transaction(
            self,
            transaction: EvmTransaction,
            tx_receipt: EvmTxReceipt,
            write_buffer: list[tuple[list[EvmEvent], str, int]] | None = None,
    ) -> tuple[list[EvmEvent], bool, set[str] | None]:
        """Leave the transaction undecoded while its L1 fee is unresolved.

        The fee should always be available, so a missing one comes from a transient
        failure of the RPC nodes and indexers. Decoding anyway would save a gas event
        without the L1 part and mark the transaction as decoded, so it would never be
        repaired. Nothing is written instead, and the chain's unresolved fees are left out
        of the periodic decoding for a while before being retried, so an outage is not
        queried again on every run.
        """
        if isinstance(transaction, L2WithL1FeesTransaction) and transaction.l1_fee is None:
            self.database.pending_txs_tracker.mark_l1_fee_unresolved(
                blockchain=self.evm_inquirer.blockchain,
                now=ts_now(),
            )
            log.warning(
                'Not decoding %s transaction %s since its L1 fee could not be resolved. '
                'It will be decoded once the fee is available.',
                self.evm_inquirer.chain_name,
                transaction.tx_hash,
            )
            return [], False, None

        return super()._decode_transaction(
            transaction=transaction,
            tx_receipt=tx_receipt,
            write_buffer=write_buffer,
        )

    def _should_defer_unresolved_l1_fees(self) -> bool:
        return self.database.pending_txs_tracker.should_defer_unresolved_l1_fees(
            blockchain=self.evm_inquirer.blockchain,
            now=ts_now(),
        )

    def _get_tx_not_decoded_filter_query(
            self,
            limit: int | None,
    ) -> EvmTransactionsNotDecodedFilterQuery:
        """Leave out the transactions with an unresolved L1 fee while a recent lookup
        failure defers them. See _decode_transaction."""
        filter_query = super()._get_tx_not_decoded_filter_query(limit=limit)
        if self._should_defer_unresolved_l1_fees():
            filter_query.filters.append(DBResolvedL1FeeFilter(and_op=True))
        return filter_query

    def _decode_undecoded_transaction_hashes(
            self,
            tx_hashes: list[EVMTxHash],
            send_ws_notifications: bool,
    ) -> None:
        """Decode the transactions with an unresolved L1 fee after the rest, and probe with
        the first of them before the others. The lookups of an outage all fail, so a failed
        probe defers the remaining ones instead of repeating the lookup for each of them."""
        unresolved = DBL2WithL1FeesTx(self.database).get_hashes_with_unresolved_l1_fee(
            chain_id=self.evm_inquirer.chain_id,
            tx_hashes=tx_hashes,
        )
        if len(resolved := [x for x in tx_hashes if x not in unresolved]) != 0:
            super()._decode_undecoded_transaction_hashes(
                tx_hashes=resolved,
                send_ws_notifications=send_ws_notifications,
            )

        unresolved_hashes = [x for x in tx_hashes if x in unresolved]
        for batch in (unresolved_hashes[:1], unresolved_hashes[1:]):  # the probe, then the rest
            if len(batch) == 0 or self._should_defer_unresolved_l1_fees():
                break

            super()._decode_undecoded_transaction_hashes(
                tx_hashes=batch,
                send_ws_notifications=send_ws_notifications,
            )

    def _calculate_fees(self, tx: L2WithL1FeesTransaction) -> FVal:  # type: ignore[override]
        return from_wei(FVal(tx.gas_used * tx.gas_price + (tx.l1_fee or 0)))

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
