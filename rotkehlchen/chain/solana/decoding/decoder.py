import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from solders.solders import Signature

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.decoding.decoder import TransactionDecoder
from rotkehlchen.chain.decoding.utils import decode_safely
from rotkehlchen.chain.evm.decoding.constants import OUTGOING_EVENT_TYPES
from rotkehlchen.chain.solana.decoding.constants import NATIVE_TRANSFER_DELIMITER, SYSTEM_PROGRAM
from rotkehlchen.chain.solana.decoding.interfaces import SolanaDecoderInterface
from rotkehlchen.chain.solana.decoding.structures import (
    SolanaDecoderContext,
    SolanaDecodingOutput,
)
from rotkehlchen.chain.solana.decoding.tools import SolanaDecoderTools
from rotkehlchen.chain.solana.types import SolanaInstruction, SolanaTransaction
from rotkehlchen.chain.solana.utils import lamports_to_sol
from rotkehlchen.constants.assets import A_SOL
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.filtering import (
    SolanaEventFilterQuery,
    SolanaTransactionsNotDecodedFilterQuery,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.solanatx import DBSolanaTx
from rotkehlchen.errors.misc import ModuleLoadingError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.solana_event import SolanaEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location, SolanaAddress, SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.chain.solana.node_inquirer import SolanaInquirer
    from rotkehlchen.chain.solana.transactions import SolanaTransactions
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.premium.premium import Premium

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class SolanaDecodingRules:
    address_mappings: dict[SolanaAddress, tuple[Any, ...]]

    def __add__(self, other: 'SolanaDecodingRules') -> 'SolanaDecodingRules':
        if not isinstance(other, SolanaDecodingRules):
            raise TypeError(
                f'Can only add SolanaDecodingRules to SolanaDecodingRules. Got {type(other)}',
            )

        return SolanaDecodingRules(
            address_mappings=self.address_mappings | other.address_mappings,
        )


class SolanaTransactionDecoder(TransactionDecoder[SolanaTransaction, SolanaDecodingRules, SolanaDecoderInterface, Signature, SolanaEvent, SolanaTransaction, SolanaDecoderTools, DBSolanaTx, SolanaEventFilterQuery, SolanaTransactionsNotDecodedFilterQuery]):  # noqa: E501

    def __init__(
            self,
            database: 'DBHandler',
            node_inquirer: 'SolanaInquirer',
            transactions: 'SolanaTransactions',
            base_tools: 'SolanaDecoderTools',
            premium: 'Premium | None' = None,
    ):
        self.node_inquirer = node_inquirer
        self.transactions = transactions
        self.dbevents = DBHistoryEvents(database)
        super().__init__(
            database=database,
            dbtx=DBSolanaTx(database),
            tx_not_decoded_filter_query_class=SolanaTransactionsNotDecodedFilterQuery,
            tx_mappings_table='solana_tx_mappings',
            chain_name=SupportedBlockchain.SOLANA.name.lower(),
            value_asset=A_SOL.resolve_to_asset_with_oracles(),
            rules=SolanaDecodingRules(address_mappings={}),
            premium=premium,
            base_tools=base_tools,
            misc_counterparties=[],
            possible_decoding_exceptions=(),
        )

    def _add_builtin_decoders(self, rules: SolanaDecodingRules) -> None:
        """No-op for solana. All decoders are loaded dynamically."""

    def _add_single_decoder(
            self,
            class_name: str,
            decoder_class: type[SolanaDecoderInterface],
            rules: SolanaDecodingRules,
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
        new_address_to_decoders = decoder.addresses_to_decoders()

        if __debug__:  # sanity checks for now only in debug as decoders are constant
            self.assert_keys_are_unique(
                new_struct=new_address_to_decoders,
                main_struct=rules.address_mappings,
                class_name=class_name,
                type_name='address_mappings',
            )

        rules.address_mappings.update(new_address_to_decoders)

    @staticmethod
    def _load_default_decoding_rules() -> SolanaDecodingRules:
        return SolanaDecodingRules(address_mappings={})

    def _load_transaction_context(
            self,
            cursor: 'DBCursor',
            tx_hash: Signature,
    ) -> SolanaTransaction:
        return self.transactions.get_or_create_transaction(signature=tx_hash)

    def _decode_transaction_from_context(
            self,
            context: SolanaTransaction,
            ignore_cache: bool,
            delete_customized: bool,
    ) -> tuple[list[SolanaEvent], bool, set[str] | None]:
        if (events := self._maybe_load_or_purge_events_from_db(
            transaction=context,
            tx_ref=context.signature,
            location=Location.SOLANA,
            ignore_cache=ignore_cache,
            delete_customized=delete_customized,
        )) is not None:
            return events, False, None

        # else we should decode now
        return self._decode_transaction(transaction=context)

    def _make_event_filter_query(self, tx_ref: Signature) -> SolanaEventFilterQuery:
        return SolanaEventFilterQuery.make(signatures=[tx_ref])

    def _calculate_fees(self, tx: SolanaTransaction) -> FVal:
        return lamports_to_sol(tx.fee)

    def _maybe_decode_fee_event(self, transaction: SolanaTransaction) -> SolanaEvent | None:
        """Decode the fee event for the given transaction.
        Returns the fee event or None if the fee is zero or the fee payer is not tracked.
        """
        if transaction.fee == ZERO or not self.base.is_tracked(fee_payer := transaction.account_keys[0]):  # noqa: E501
            return None

        return self.base.make_event_next_index(
            tx_hash=transaction.signature,
            timestamp=transaction.block_time,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_SOL,
            amount=(amount := lamports_to_sol(transaction.fee)),
            location_label=fee_payer,
            notes=f'Spend {amount} SOL as transaction fee',
            counterparty=CPT_GAS,
        )

    def _maybe_decode_native_transfer(
            self,
            transaction: SolanaTransaction,
            instruction: SolanaInstruction,
    ) -> SolanaEvent | None:
        """Decode native SOL transfers."""
        if instruction.program_id != SYSTEM_PROGRAM or instruction.data[:4] != NATIVE_TRANSFER_DELIMITER:  # noqa: E501
            return None

        if (account_len := len(instruction.accounts)) < 2:
            log.error(
                f'Encountered a native transfer instruction in {transaction} '
                f'with {account_len} accounts. Expected 2. Skipping.',
            )
            return None

        if (
            (direction_result := self.base.decode_direction(
                from_address=instruction.accounts[0],
                to_address=instruction.accounts[1],
            )) is None or
            (raw_amount := int.from_bytes(instruction.data[4:12], byteorder='little')) == 0
        ):
            return None

        amount = lamports_to_sol(raw_amount)
        event_type, event_subtype, location_label, address, counterparty, verb = direction_result
        counterparty_or_address = counterparty or address
        preposition = 'to' if event_type in OUTGOING_EVENT_TYPES else 'from'
        return self.base.make_event_next_index(
            tx_hash=transaction.signature,
            timestamp=transaction.block_time,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=A_SOL,
            amount=amount,
            location_label=location_label,
            notes=f'{verb} {amount} SOL {preposition} {counterparty_or_address}',
            counterparty=counterparty,
            address=address,
        )

    def _decode_basic_events(
            self,
            transaction: SolanaTransaction,
    ) -> tuple[list[SolanaEvent], list[SolanaInstruction]]:
        """Decode the basic events (fee, transfers, etc.) for the given transaction.
        Returns a tuple containing the list of decoded events and the list of instructions that
        have not been decoded yet.
        """
        events: list[SolanaEvent] = []
        if (fee_event := self._maybe_decode_fee_event(transaction=transaction)) is not None:
            events.append(fee_event)

        # Decode basic transfer instructions so that the more complex decoding that runs later
        # can simply modify the already decoded transfer events.
        undecoded_instructions = []
        for instruction in transaction.instructions:
            if (native_transfer_event := self._maybe_decode_native_transfer(
                transaction=transaction,
                instruction=instruction,
            )) is not None:
                events.append(native_transfer_event)
                continue

            # TODO: also decode token transfers here

            undecoded_instructions.append(instruction)

        return events, undecoded_instructions

    def _decode_transaction(
            self,
            transaction: SolanaTransaction,
    ) -> tuple[list[SolanaEvent], bool, set[str] | None]:
        """Decodes a solana transaction and saves the result in the DB.
        Returns
        - the list of decoded events
        - a flag which is True if balances refresh is needed
        - A list of decoders to reload or None if no need
        """
        log.debug(f'Starting decoding of solana transaction {transaction.signature!s}')

        if len(transaction.account_keys) == 0 or len(transaction.instructions) == 0:
            log.warning(
                f'Solana transaction {transaction.signature!s} '
                f'has empty instructions or accounts. Skipping.',
            )
            return [], False, None

        self.base.reset_sequence_counter(tx_data=transaction)
        events, undecoded_instructions = self._decode_basic_events(transaction=transaction)
        refresh_balances, reload_decoders = False, set()
        for instruction in undecoded_instructions:
            if (mapping_result := self.rules.address_mappings.get(instruction.program_id)) is None:
                continue

            context = SolanaDecoderContext(
                transaction=transaction,
                instruction=instruction,
                decoded_events=events,
            )
            method, *args = mapping_result
            decoding_output: SolanaDecodingOutput
            decoding_output, err = decode_safely(  # can't used named arguments with *args
                self.possible_decoding_exceptions,
                self.msg_aggregator,
                SupportedBlockchain.SOLANA,
                method,
                str(context.transaction.signature),
                *(context, *args),
            )
            if err:
                continue

            if decoding_output.refresh_balances:
                refresh_balances = True
            if decoding_output.reload_decoders is not None:
                reload_decoders.update(decoding_output.reload_decoders)
            if decoding_output.events is not None:
                events.extend(decoding_output.events)

        if len(reload_decoders) == 0:
            return events, refresh_balances, None

        return events, refresh_balances, reload_decoders
