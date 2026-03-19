import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.decoding.decoder import TransactionDecoder
from rotkehlchen.chain.decoding.types import DecodingRulesBase
from rotkehlchen.chain.starknet.types import StarknetTransaction
from rotkehlchen.chain.starknet.utils import wei_to_strk
from rotkehlchen.constants.assets import A_STRK
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.filtering import (
    StarknetEventFilterQuery,
    StarknetTransactionsNotDecodedFilterQuery,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.starknettx import DBStarknetTx
from rotkehlchen.errors.misc import ModuleLoadingError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.starknet_event import StarknetEvent
from rotkehlchen.history.events.structures.starknet_swap import StarknetSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location, StarknetAddress, SupportedBlockchain

from .interfaces import StarknetDecoderInterface
from .tools import StarknetDecoderTools

if TYPE_CHECKING:
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.starknet.node_inquirer import StarknetInquirer
    from rotkehlchen.chain.starknet.transactions import StarknetTransactions
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.premium.premium import Premium

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class StarknetDecodingRules(DecodingRulesBase):
    contract_address_mappings: dict[StarknetAddress, tuple]
    all_counterparties: set['CounterpartyDetails']

    def __add__(self, other: 'StarknetDecodingRules') -> 'StarknetDecodingRules':
        if not isinstance(other, StarknetDecodingRules):
            raise TypeError(
                f'Can only add StarknetDecodingRules to StarknetDecodingRules. Got {type(other)}',
            )

        return StarknetDecodingRules(
            contract_address_mappings=self.contract_address_mappings | other.contract_address_mappings,  # noqa: E501
            all_counterparties=self.all_counterparties | other.all_counterparties,
        )


class StarknetTransactionDecoder(TransactionDecoder[StarknetTransaction, StarknetDecodingRules, StarknetDecoderInterface, str, StarknetEvent, StarknetTransaction, StarknetDecoderTools, DBStarknetTx, StarknetEventFilterQuery, StarknetTransactionsNotDecodedFilterQuery]):  # noqa: E501

    def __init__(
            self,
            database: 'DBHandler',
            node_inquirer: 'StarknetInquirer',
            transactions: 'StarknetTransactions',
            base_tools: 'StarknetDecoderTools',
            premium: 'Premium | None' = None,
    ):
        self.node_inquirer = node_inquirer
        self.transactions = transactions
        self.dbevents = DBHistoryEvents(database)
        super().__init__(
            database=database,
            dbtx=DBStarknetTx(database),
            tx_mappings_table='starknet_tx_mappings',
            chain_name=SupportedBlockchain.STARKNET.name.lower(),
            value_asset=A_STRK.resolve_to_asset_with_oracles(),
            rules=StarknetDecodingRules(
                contract_address_mappings={},
                all_counterparties=set(),
            ),
            premium=premium,
            base_tools=base_tools,
            misc_counterparties=[],
            possible_decoding_exceptions=(),
        )

    def _add_builtin_decoders(self, rules: StarknetDecodingRules) -> None:
        """No-op for starknet. All decoders are loaded dynamically."""

    def _add_single_decoder(
            self,
            class_name: str,
            decoder_class: type[StarknetDecoderInterface],
            rules: StarknetDecodingRules,
    ) -> None:
        """Initialize a single decoder, add it to the set of decoders to use
        and append its rules to the passed rules
        """
        if class_name in self.decoders:
            raise ModuleLoadingError(f'{self.chain_name} decoder with name {class_name} already loaded')  # noqa: E501

        self.decoders[class_name] = (decoder := decoder_class(
            node_inquirer=self.node_inquirer,
            base_tools=self.base,
            msg_aggregator=self.msg_aggregator,
        ))
        new_address_mappings = decoder.addresses_to_decoders()

        if __debug__:
            self.assert_keys_are_unique(
                new_struct=new_address_mappings,
                main_struct=rules.contract_address_mappings,
                class_name=class_name,
                type_name='contract_address_mappings',
            )

        rules.contract_address_mappings.update(new_address_mappings)
        rules.all_counterparties.update(decoder.counterparties())

    @staticmethod
    def _load_default_decoding_rules() -> StarknetDecodingRules:
        return StarknetDecodingRules(
            contract_address_mappings={},
            all_counterparties=set(),
        )

    def _get_tx_not_decoded_filter_query(
            self,
            limit: int | None,
    ) -> StarknetTransactionsNotDecodedFilterQuery:
        return StarknetTransactionsNotDecodedFilterQuery.make(limit=limit)

    def _load_transaction_context(
            self,
            cursor: 'DBCursor',
            tx_hash: str,
    ) -> StarknetTransaction:
        return self.transactions.get_or_create_transaction(tx_hash=tx_hash)

    def _decode_transaction_from_context(
            self,
            context: StarknetTransaction,
            ignore_cache: bool,
            delete_customized: bool,
    ) -> tuple[list[StarknetEvent], bool, set[str] | None]:
        if (events := self._maybe_load_or_purge_events_from_db(
            transaction=context,
            tx_ref=context.transaction_hash,
            location=Location.STARKNET,
            ignore_cache=ignore_cache,
            delete_customized=delete_customized,
        )) is not None:
            return events, False, None

        return self._decode_transaction(transaction=context)

    def _make_event_filter_query(self, tx_ref: str) -> StarknetEventFilterQuery:
        return StarknetEventFilterQuery.make(tx_hashes=[tx_ref])

    def _calculate_fees(self, tx: StarknetTransaction) -> FVal:
        return wei_to_strk(tx.actual_fee)

    def _create_swap_event(
            self,
            trade_event: StarknetEvent,
            spend_event: StarknetEvent,
            sequence_index: int,
            event_type: HistoryEventType,
    ) -> StarknetEvent:
        """Creates a StarknetSwapEvent from trade event data."""
        return StarknetSwapEvent(
            tx_ref=trade_event.tx_ref,
            sequence_index=sequence_index,
            timestamp=trade_event.timestamp,
            event_type=event_type,  # type: ignore[arg-type]  # will be TRADE or MULTI_TRADE
            event_subtype=trade_event.event_subtype,  # type: ignore[arg-type]  # will be SPEND, RECEIVE, or FEE
            asset=trade_event.asset,
            amount=trade_event.amount,
            notes=trade_event.notes,
            extra_data=trade_event.extra_data,
            location_label=trade_event.location_label if trade_event.location_label is not None else spend_event.location_label,  # noqa: E501
            counterparty=spend_event.counterparty,
            address=spend_event.address,
        )

    def _maybe_decode_fee_event(self, transaction: StarknetTransaction) -> StarknetEvent | None:
        """Decode the fee event for the given transaction."""
        if transaction.actual_fee == ZERO or not self.base.is_tracked(transaction.from_address):
            return None

        amount = wei_to_strk(transaction.actual_fee)
        return self.base.make_event_next_index(
            tx_ref=transaction.transaction_hash,
            timestamp=transaction.block_timestamp,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_STRK,
            amount=amount,
            location_label=transaction.from_address,
            notes=f'Spend {amount} STRK as transaction fee',
            counterparty=CPT_GAS,
        )

    def _decode_transaction(
            self,
            transaction: StarknetTransaction,
    ) -> tuple[list[StarknetEvent], bool, set[str] | None]:
        """Decodes a starknet transaction and saves the result in the DB."""
        log.debug(f'Starting decoding of starknet transaction {transaction.transaction_hash}')

        with self.database.conn.write_ctx() as write_cursor:
            tx_id = transaction.get_or_query_db_id(write_cursor)
            # Ensure the Starknet location and STRK asset exist in the user DB
            write_cursor.execute(
                "INSERT OR IGNORE INTO location(location, seq) VALUES ('y', 57)",
            )
            self.database.add_asset_identifiers(write_cursor, [A_STRK.identifier])

        self.base.reset_sequence_counter(tx_data=transaction)
        events: list[StarknetEvent] = []

        # Decode fee event
        if (fee_event := self._maybe_decode_fee_event(transaction=transaction)) is not None:
            events.append(fee_event)

        # Sort events by sequence index
        events = sorted(events, key=lambda x: x.sequence_index, reverse=False)

        self._write_new_tx_events_to_the_db(
            events=events,
            action_id=transaction.transaction_hash,
            db_id=tx_id,
        )
        return events, False, None
