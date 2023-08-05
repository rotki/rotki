import importlib
import logging
import pkgutil
from abc import ABCMeta, abstractmethod
from contextlib import suppress
from dataclasses import dataclass
from types import ModuleType
from typing import TYPE_CHECKING, Any, Callable, Optional, Protocol, Union

from gevent.lock import Semaphore

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmProduct
from rotkehlchen.accounting.structures.types import (
    ActionType,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import AssetWithOracles, EvmToken
from rotkehlchen.assets.utils import TokenSeenAt, get_or_create_evm_token
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import ReloadableDecoderMixin
from rotkehlchen.chain.evm.decoding.safe.decoder import SafemultisigDecoder
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails, EventCategory
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.constants import ZERO
from rotkehlchen.db.constants import HISTORY_MAPPING_STATE_DECODED
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmEventFilterQuery, EvmTransactionsFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import InputError, ModuleLoadingError, NotERC20Conformant, RemoteError
from rotkehlchen.errors.serialization import ConversionError, DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    ChecksumEvmAddress,
    DecoderEventMappingType,
    EvmTokenKind,
    EvmTransaction,
    EVMTxHash,
)
from rotkehlchen.utils.misc import (
    combine_dicts,
    from_wei,
    hex_or_bytes_to_address,
    hex_or_bytes_to_int,
)
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin

from ...arbitrum_one.modules.arbitrum_one_bridge.decoder import DEPOSIT_TX_TYPE
from .base import BaseDecoderTools, BaseDecoderToolsWithDSProxy
from .constants import CPT_GAS, ERC20_APPROVE, ERC20_OR_ERC721_TRANSFER, OUTGOING_EVENT_TYPES
from .structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
    EnricherContext,
    TransferEnrichmentOutput,
)
from .utils import maybe_reshuffle_events

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.evm_event import EvmEvent
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer, EvmNodeInquirerWithDSProxy
    from rotkehlchen.chain.evm.transactions import EvmTransactions
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

    from .interfaces import DecoderInterface

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EventDecoderFunction(Protocol):

    def __call__(
            self,
            token: Optional[EvmToken],
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            action_items: list[ActionItem],
            all_logs: list[EvmTxReceiptLog],
    ) -> DecodingOutput:
        ...


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class DecodingRules:
    address_mappings: dict[ChecksumEvmAddress, tuple[Any, ...]]
    event_rules: list[EventDecoderFunction]
    input_data_rules: dict[bytes, dict[bytes, Callable]]
    token_enricher_rules: list[Callable]  # enrichers to run for token transfers
    # rules to run after the main decoding loop. post_decoding_rules is a mapping of
    # counterparties to tuples of the rules that need to be executed.
    post_decoding_rules: dict[str, list[tuple[int, Callable]]]
    all_counterparties: set['CounterpartyDetails']
    addresses_to_counterparties: dict[ChecksumEvmAddress, str]

    def __add__(self, other: 'DecodingRules') -> 'DecodingRules':
        if not isinstance(other, DecodingRules):
            raise TypeError(
                f'Can only add DecodingRules to DecodingRules. Got {type(other)}',
            )

        intersection = set(other.input_data_rules).intersection(set(self.input_data_rules))
        if len(intersection) != 0:
            raise ValueError(f'Input data duplicates found in decoding rules for {intersection}')

        return DecodingRules(
            address_mappings=self.address_mappings | other.address_mappings,
            event_rules=self.event_rules + other.event_rules,
            input_data_rules=self.input_data_rules | other.input_data_rules,
            token_enricher_rules=self.token_enricher_rules + other.token_enricher_rules,
            post_decoding_rules=self.post_decoding_rules | other.post_decoding_rules,
            all_counterparties=self.all_counterparties | other.all_counterparties,
            addresses_to_counterparties=self.addresses_to_counterparties | other.addresses_to_counterparties,  # noqa: E501
        )


class EVMTransactionDecoder(metaclass=ABCMeta):

    def __init__(
            self,
            database: 'DBHandler',
            evm_inquirer: 'EvmNodeInquirer',
            transactions: 'EvmTransactions',
            value_asset: AssetWithOracles,
            event_rules: list[EventDecoderFunction],
            misc_counterparties: list[CounterpartyDetails],
            base_tools: BaseDecoderTools,
            dbevmtx_class: type[DBEvmTx] = DBEvmTx,
    ):
        """
        Initialize an evm chain transaction decoder module for a particular chain.

        `value_asset` is the asset that is normally transferred at value transfers
        and the one that is spent for gas in this chain

        `event_rules` is a list of callables to act as decoding rules for all tx
        receipt logs decoding for the particular chain

        `misc_counterparties` is a list of counterparties not associated with any specific
        decoder that should be included for this decoder modules.
        """
        self.database = database
        self.misc_counterparties = [CounterpartyDetails(identifier=CPT_GAS, label='gas', image='gas.svg')] + misc_counterparties  # noqa: E501
        self.evm_inquirer = evm_inquirer
        self.transactions = transactions
        self.msg_aggregator = database.msg_aggregator
        self.chain_modules_root = f'rotkehlchen.chain.{self.evm_inquirer.chain_name}.modules'
        self.chain_modules_prefix_length = len(self.chain_modules_root)
        self.dbevmtx = dbevmtx_class(self.database)
        self.dbevents = DBHistoryEvents(self.database)
        self.base = base_tools
        self.rules = DecodingRules(
            address_mappings={},
            event_rules=[
                self._maybe_decode_erc20_approve,
                self._maybe_decode_erc20_721_transfer,
            ],
            input_data_rules={},
            token_enricher_rules=[],
            post_decoding_rules={},
            all_counterparties=set(self.misc_counterparties),
            addresses_to_counterparties={},
        )
        self.rules.event_rules.extend(event_rules)
        self.value_asset = value_asset
        self.decoders: dict[str, DecoderInterface] = {}
        # store the mapping of possible counterparties to the allowed types and subtypes in events
        self.events_types_tuples: DecoderEventMappingType = {}

        # Add the built-in decoders
        self._add_builtin_decoders(self.rules)
        # Recursively check all submodules to get all decoder address mappings and rules
        self.rules += self._recursively_initialize_decoders(self.chain_modules_root)
        self.undecoded_tx_query_lock = Semaphore()

    def _add_builtin_decoders(self, rules: DecodingRules) -> None:
        """Adds decoders that should be built-in for every EVM decoding run

        Think: Perhaps we can move them under a specific directory and use the
        normal loading?
        """
        return self._add_single_decoder(class_name='Safemultisig', decoder_class=SafemultisigDecoder, rules=rules)  # noqa: E501

    def _add_single_decoder(
            self,
            class_name: str,
            decoder_class: type['DecoderInterface'],
            rules: DecodingRules,
    ) -> None:
        """Initialize a single decoder, add it to the set of decoders to use
        and append its rules to the pased rules
        """
        if class_name in self.decoders:
            raise ModuleLoadingError(f'{self.evm_inquirer.chain_name} decoder with name {class_name} already loaded')  # noqa: E501

        try:  # not giving kwargs since, kwargs name can differ
            self.decoders[class_name] = decoder_class(
                self.evm_inquirer,  # evm_inquirer
                self.base,  # base_tools
                self.msg_aggregator,  # msg_aggregator
            )
        except (UnknownAsset, WrongAssetType) as e:
            self.msg_aggregator.add_error(
                f'Failed at initialization of {self.evm_inquirer.chain_name} '
                f'{class_name} decoder due to asset mismatch: {e!s}',
            )
            return

        new_input_data_rules = self.decoders[class_name].decoding_by_input_data()
        intersection = set(new_input_data_rules).intersection(set(rules.input_data_rules))
        if len(intersection) != 0:
            raise ValueError(f'Input data duplicates found in decoding rules for {intersection}')

        rules.address_mappings.update(self.decoders[class_name].addresses_to_decoders())  # noqa: E501
        rules.event_rules.extend(self.decoders[class_name].decoding_rules())
        rules.input_data_rules.update(new_input_data_rules)
        rules.token_enricher_rules.extend(self.decoders[class_name].enricher_rules())
        rules.post_decoding_rules.update(self.decoders[class_name].post_decoding_rules())  # noqa: E501
        rules.all_counterparties.update(self.decoders[class_name].counterparties())
        rules.addresses_to_counterparties.update(self.decoders[class_name].addresses_to_counterparties())  # noqa: E501
        self._chain_specific_decoder_initialization(self.decoders[class_name])

    def _recursively_initialize_decoders(
            self,
            package: Union[str, ModuleType],
    ) -> DecodingRules:
        if isinstance(package, str):
            package = importlib.import_module(package)

        rules = DecodingRules(
            address_mappings={},
            event_rules=[],
            input_data_rules={},
            token_enricher_rules=[],
            post_decoding_rules={},
            all_counterparties=set(),
            addresses_to_counterparties={},
        )

        for _, name, is_pkg in pkgutil.walk_packages(package.__path__):
            full_name = package.__name__ + '.' + name
            if full_name == __name__ or is_pkg is False:
                continue  # skip

            submodule = None
            with suppress(ModuleNotFoundError):
                submodule = importlib.import_module(full_name + '.decoder')

            if submodule is not None:
                # take module name, transform it and find decoder if exists
                class_name = full_name[self.chain_modules_prefix_length:].translate({ord('.'): None})  # noqa: E501
                parts = class_name.split('_')
                class_name = ''.join([x.capitalize() for x in parts])
                submodule_decoder = getattr(submodule, f'{class_name}Decoder', None)

                if submodule_decoder:
                    self._add_single_decoder(class_name=class_name, decoder_class=submodule_decoder, rules=rules)  # noqa: E501

            if is_pkg:
                recursive_results = self._recursively_initialize_decoders(full_name)
                rules += recursive_results

        return rules

    def get_decoders_products(self) -> dict[str, list[EvmProduct]]:
        """Get the list of possible products"""
        possible_products: dict[str, list[EvmProduct]] = {}
        for decoder in self.decoders.values():
            possible_products |= decoder.possible_products()

        return possible_products

    def get_decoders_event_types(self) -> DecoderEventMappingType:
        """Get the mappings of counterparties to their possible event type
        and subtype combinations
        """
        possible_types = {}
        for decoder in self.decoders.values():
            for counterparty, new_events in decoder.possible_events().items():
                if counterparty not in possible_types:
                    possible_types.update({counterparty: new_events})
                else:
                    possible_types[counterparty] = combine_dicts(
                        a=possible_types[counterparty],
                        b=new_events,
                        op=lambda a, b: a | b,
                    )

        # add gas burning
        possible_types[CPT_GAS] = {
            HistoryEventType.SPEND: {HistoryEventSubType.FEE: EventCategory.GAS},
        }
        return possible_types

    def reload_data(self, cursor: 'DBCursor') -> None:
        """Reload all related settings from DB and data that any decoder may require from the chain
        so that decoding happens with latest data"""
        self.base.refresh_tracked_accounts(cursor)
        for decoder in self.decoders.values():
            if isinstance(decoder, CustomizableDateMixin):
                decoder.reload_settings(cursor)
            if isinstance(decoder, ReloadableDecoderMixin):
                new_mappings = decoder.reload_data()
                if new_mappings is not None:
                    self.rules.address_mappings.update(new_mappings)

    def try_all_rules(
            self,
            token: Optional[EvmToken],
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            action_items: list[ActionItem],
            all_logs: list[EvmTxReceiptLog],
    ) -> Optional[DecodingOutput]:
        """
        Execute event rules for the current tx log. Returns None when no
        new event or actions need to be propagated.
        """
        for rule in self.rules.event_rules:
            if len(tx_log.topics) == 0:
                continue  # ignore anonymous events

            try:
                decoding_output = rule(token=token, tx_log=tx_log, transaction=transaction, decoded_events=decoded_events, action_items=action_items, all_logs=all_logs)  # noqa: E501
            except (DeserializationError, IndexError) as e:
                self.msg_aggregator.add_error(f'Decoding tx log with index {tx_log.log_index} of {transaction.tx_hash.hex()} through {rule} failed due to {e!s}. Skipping rule.')  # noqa: E501
                continue

            if decoding_output.event is not None or len(decoding_output.action_items) > 0:
                return decoding_output

        return None

    def decode_by_address_rules(self, context: DecoderContext) -> DecodingOutput:
        """
        Sees if the log is on an address for which we have specific decoders and calls it

        Should catch all underlying errors these decoders will raise. So far known are:
        - DeserializationError
        - ConversionError
        - UnknownAsset
        """
        mapping_result = self.rules.address_mappings.get(context.tx_log.address)
        if mapping_result is None:
            return DEFAULT_DECODING_OUTPUT
        method = mapping_result[0]

        try:
            if len(mapping_result) == 1:
                result = method(context)
            else:
                result = method(context, *mapping_result[1:])
        except (DeserializationError, ConversionError, UnknownAsset) as e:
            self.msg_aggregator.add_error(
                f'Decoding tx log with index {context.tx_log.log_index} of transaction '
                f'{context.transaction.tx_hash.hex()} through {method.__name__} failed due to {e!s}')  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        return result

    def run_all_post_decoding_rules(
            self,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            all_logs: list[EvmTxReceiptLog],
            counterparties: set[str],
    ) -> list['EvmEvent']:
        """
        The post-decoding rules list consists of tuples (priority, rule) and must be
        sorted by priority in ascending order. The higher the priority number the later
        the rule is run.
        Matches post decoding rules to all matched counterparties propagated for decoding
        from the decoding/enriching rules and also the counterparties associated with the
        transaction to_address field.
        """
        if transaction.to_address is not None:
            address_counterparty = self.rules.addresses_to_counterparties.get(transaction.to_address)  # noqa: E501
            if address_counterparty is not None:
                counterparties.add(address_counterparty)
            elif hasattr(transaction, 'tx_type') and transaction.tx_type == DEPOSIT_TX_TYPE:
                # If this is a transaction for receiving eth in arbitrum one from arbitrum one
                # bridge, then there is no address specific counterparty. Check if there are
                # any rules for all counterparties. This way we can apply post decoding rules
                # to a transaction irrespective of the to_address on specific cases.
                counterparties = {cpt_details.identifier for cpt_details in self.rules.all_counterparties}  # noqa: E501

        rules = self._chain_specific_post_decoding_rules(transaction)
        # get the rules that need to be applied by counterparty
        for counterparty in counterparties:
            new_rules = self.rules.post_decoding_rules.get(counterparty)
            if new_rules is not None:
                rules.extend(new_rules)

        # Sort post decoding rules by priority (which is the first element of the tuple)
        rules.sort(key=lambda x: x[0])
        for _, rule in rules:
            try:
                decoded_events = rule(transaction=transaction, decoded_events=decoded_events, all_logs=all_logs)  # noqa: E501
            except (DeserializationError, IndexError) as e:
                log.error(f'Applying post-decoding rule {rule} for {transaction.tx_hash.hex()} failed due to {e!s}. Skipping rule.')  # noqa: E501

        assert self._check_correct_types(decoded_events)
        return decoded_events

    def _decode_transaction(
            self,
            transaction: EvmTransaction,
            tx_receipt: EvmTxReceipt,
    ) -> tuple[list['EvmEvent'], bool]:
        """
        Decodes an evm transaction and its receipt and saves result in the DB.
        Returns the list of decoded events and a flag which is True if balances refresh is needed.
        """
        self.base.reset_sequence_counter()
        # check if any eth transfer happened in the transaction, including in internal transactions
        events = self._maybe_decode_simple_transactions(transaction, tx_receipt)
        action_items: list[ActionItem] = []
        counterparties = set()
        refresh_balances = False

        # Check if any rules should run due to the 4bytes signature of the input data
        fourbytes = transaction.input_data[:4]
        input_data_rules = self.rules.input_data_rules.get(fourbytes)

        # decode transaction logs from the receipt
        for tx_log in tx_receipt.logs:
            context = DecoderContext(
                tx_log=tx_log,
                transaction=transaction,
                decoded_events=events,
                all_logs=tx_receipt.logs,
                action_items=action_items,
            )
            if input_data_rules and len(tx_log.topics) != 0 and (input_rule := input_data_rules.get(tx_log.topics[0])) is not None:  # noqa: E501
                try:  # run specific decoder if the 4bytes signature + topic match
                    result = input_rule(context)
                except (DeserializationError, ConversionError, UnknownAsset) as e:
                    log.error(f'Decoding log {tx_log} of {transaction} via input data rules failed due to {e!s}')  # noqa: E501
                    result = DEFAULT_DECODING_OUTPUT

                if result.event:
                    events.append(result.event)
                    continue  # since the input data rule found an event for this log

            decoding_output = self.decode_by_address_rules(context)
            if decoding_output.refresh_balances is True:
                refresh_balances = True
            action_items.extend(decoding_output.action_items)
            if decoding_output.matched_counterparty is not None:
                counterparties.add(decoding_output.matched_counterparty)
            if decoding_output.event:
                events.append(decoding_output.event)
                continue

            token = GlobalDBHandler.get_evm_token(
                address=tx_log.address,
                chain_id=self.evm_inquirer.chain_id,
            )
            rules_decoding_output = self.try_all_rules(
                token=token,
                tx_log=tx_log,
                transaction=transaction,
                decoded_events=events,
                action_items=action_items,
                all_logs=tx_receipt.logs,
            )
            if rules_decoding_output is not None:
                if rules_decoding_output.refresh_balances is True:
                    refresh_balances = True
                action_items.extend(rules_decoding_output.action_items)
                if rules_decoding_output.matched_counterparty is not None:
                    counterparties.add(rules_decoding_output.matched_counterparty)
                if rules_decoding_output.event is not None:
                    events.append(rules_decoding_output.event)

        events = self.run_all_post_decoding_rules(
            transaction=transaction,
            decoded_events=events,
            all_logs=tx_receipt.logs,
            counterparties=counterparties,
        )

        if len(events) == 0 and (eth_event := self._get_eth_transfer_event(transaction)) is not None:  # noqa: E501
            events = [eth_event]

        with self.database.user_write() as write_cursor:
            if len(events) > 0:
                self.dbevents.add_history_events(
                    write_cursor=write_cursor,
                    history=events,
                )
            else:
                # This is probably a phishing zero value token transfer tx.
                # Details here: https://github.com/rotki/rotki/issues/5749
                with suppress(InputError):  # We don't care if it's already in the DB
                    self.database.add_to_ignored_action_ids(
                        write_cursor=write_cursor,
                        action_type=ActionType.EVM_TRANSACTION,
                        identifiers=[transaction.identifier],
                    )
            tx_id = transaction.get_or_query_db_id(write_cursor)
            write_cursor.execute(
                'INSERT OR IGNORE INTO evm_tx_mappings(tx_id, value) VALUES(?, ?)',
                (tx_id, HISTORY_MAPPING_STATE_DECODED),
            )

        events = sorted(events, key=lambda x: x.sequence_index, reverse=False)
        return events, refresh_balances  # Propagate for post processing in the caller

    def get_and_decode_undecoded_transactions(
            self,
            limit: Optional[int] = None,
            addresses: Optional[list[ChecksumEvmAddress]] = None,
    ) -> None:
        """Checks the DB for up to `limit` undecoded transactions and decodes them.
        If a list of addresses is provided then only the transactions involving those
        addresses are decoded.

        This is protected by concurrent access from a lock"""
        with self.undecoded_tx_query_lock:
            hashes = self.dbevmtx.get_transaction_hashes_not_decoded(
                chain_id=self.evm_inquirer.chain_id,
                limit=limit,
                addresses=addresses,
            )
            self.decode_transaction_hashes(ignore_cache=False, tx_hashes=hashes)

    def decode_transaction_hashes(
            self,
            ignore_cache: bool,
            tx_hashes: Optional[list[EVMTxHash]],
    ) -> list['EvmEvent']:
        """Make sure that receipts are pulled + events decoded for the given transaction hashes.

        The transaction hashes must exist in the DB at the time of the call

        May raise:
        - DeserializationError if there is a problem with conacting a remote to get receipts
        - RemoteError if there is a problem with contacting a remote to get receipts
        - InputError if the transaction hash is not found in the DB
        """
        events: list[EvmEvent] = []
        refresh_balances = False
        with self.database.conn.read_ctx() as cursor:
            self.reload_data(cursor)
            # If no transaction hashes are passed, decode all transactions.
            if tx_hashes is None:
                cursor.execute(
                    'SELECT tx_hash FROM evm_transactions WHERE chain_id=?',
                    (self.evm_inquirer.chain_id.serialize_for_db(),),
                )
                tx_hashes = [EVMTxHash(x[0]) for x in cursor]

        for tx_hash in tx_hashes:
            try:
                receipt = self.transactions.get_or_query_transaction_receipt(tx_hash)
            except RemoteError as e:
                raise InputError(f'{self.evm_inquirer.chain_name} hash {tx_hash.hex()} does not correspond to a transaction') from e  # noqa: E501

            # TODO: Change this if transaction filter query can accept multiple hashes
            with self.database.conn.read_ctx() as cursor:
                txs = self.dbevmtx.get_evm_transactions(
                    cursor=cursor,
                    filter_=EvmTransactionsFilterQuery.make(tx_hash=tx_hash, chain_id=self.evm_inquirer.chain_id),  # noqa: E501
                    has_premium=True,  # ignore limiting here
                )
            new_events, new_refresh_balances = self._get_or_decode_transaction_events(
                transaction=txs[0],
                tx_receipt=receipt,
                ignore_cache=ignore_cache,
            )
            events.extend(new_events)
            if new_refresh_balances is True:
                refresh_balances = True

        self._post_process(refresh_balances=refresh_balances)
        return events

    def _get_or_decode_transaction_events(
            self,
            transaction: EvmTransaction,
            tx_receipt: EvmTxReceipt,
            ignore_cache: bool,
    ) -> tuple[list['EvmEvent'], bool]:
        """
        Get a transaction's events if existing in the DB or decode them.
        Returns the list of decoded events and a flag which is True if balances refresh is needed.
        """
        with self.database.conn.read_ctx() as cursor:
            tx_id = transaction.get_or_query_db_id(cursor)
        if ignore_cache is True:  # delete all decoded events
            with self.database.user_write() as write_cursor:
                self.dbevents.delete_events_by_tx_hash(
                    write_cursor=write_cursor,
                    tx_hashes=[transaction.tx_hash],
                    chain_id=self.evm_inquirer.chain_id,
                )
                write_cursor.execute(
                    'DELETE from evm_tx_mappings WHERE tx_id=? AND value=?',
                    (tx_id, HISTORY_MAPPING_STATE_DECODED),
                )
        else:  # see if events are already decoded and return them
            with self.database.conn.read_ctx() as cursor:
                cursor.execute(
                    'SELECT COUNT(*) from evm_tx_mappings WHERE tx_id=? AND value=?',
                    (tx_id, HISTORY_MAPPING_STATE_DECODED),
                )
                if cursor.fetchone()[0] != 0:  # already decoded and in the DB
                    events = self.dbevents.get_history_events(
                        cursor=cursor,
                        filter_query=EvmEventFilterQuery.make(
                            tx_hashes=[transaction.tx_hash],
                        ),
                        has_premium=True,  # for this function we don't limit anything
                    )
                    return events, False

        # else we should decode now
        return self._decode_transaction(transaction=transaction, tx_receipt=tx_receipt)

    def _maybe_decode_internal_transactions(
            self,
            tx: EvmTransaction,
            tx_receipt: EvmTxReceipt,
            events: list['EvmEvent'],
    ) -> None:
        """
        check for internal transactions if the transaction is not canceled. This function mutates
        the events argument.
        """
        if tx_receipt.status is False:
            return

        internal_txs = self.dbevmtx.get_evm_internal_transactions(
            parent_tx_hash=tx.tx_hash,
            blockchain=self.evm_inquirer.blockchain,
        )
        for internal_tx in internal_txs:
            if internal_tx.to_address is None:
                continue  # can that happen? Internal transaction deploying a contract?
            direction_result = self.base.decode_direction(
                from_address=internal_tx.from_address,
                to_address=internal_tx.to_address,
            )
            if direction_result is None:
                continue

            amount = ZERO if internal_tx.value == 0 else from_wei(FVal(internal_tx.value))
            if amount == ZERO:
                continue

            event_type, location_label, address, counterparty, verb = direction_result
            counterparty_or_address = counterparty or address
            preposition = 'to' if event_type in OUTGOING_EVENT_TYPES else 'from'
            events.append(self.base.make_event_next_index(
                tx_hash=tx.tx_hash,
                timestamp=tx.timestamp,
                event_type=event_type,
                event_subtype=HistoryEventSubType.NONE,
                asset=self.value_asset,
                balance=Balance(amount=amount),
                location_label=location_label,
                notes=f'{verb} {amount} {self.value_asset.symbol} {preposition} {counterparty_or_address}',  # noqa: E501
                address=address,
                counterparty=counterparty,
            ))

    def _get_eth_transfer_event(self, tx: EvmTransaction) -> Optional['EvmEvent']:
        direction_result = self.base.decode_direction(
            from_address=tx.from_address,
            to_address=tx.to_address,
        )
        if direction_result is None:
            return None
        event_type, location_label, address, counterparty, verb = direction_result
        counterparty_or_address = counterparty or address
        amount = ZERO if tx.value == 0 else from_wei(FVal(tx.value))
        preposition = 'to' if event_type in OUTGOING_EVENT_TYPES else 'from'
        return self.base.make_event_next_index(
            tx_hash=tx.tx_hash,
            timestamp=tx.timestamp,
            event_type=event_type,
            event_subtype=HistoryEventSubType.NONE,
            asset=self.value_asset,
            balance=Balance(amount=amount),
            location_label=location_label,
            notes=f'{verb} {amount} {self.value_asset.symbol} {preposition} {counterparty_or_address}',  # noqa: E501
            address=address,
            counterparty=counterparty,
        )

    def _maybe_decode_erc20_approve(
            self,
            token: Optional[EvmToken],
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],  # pylint: disable=unused-argument
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> DecodingOutput:
        if tx_log.topics[0] != ERC20_APPROVE or token is None:
            return DEFAULT_DECODING_OUTPUT

        if len(tx_log.topics) == 3:
            owner_address = hex_or_bytes_to_address(tx_log.topics[1])
            spender_address = hex_or_bytes_to_address(tx_log.topics[2])
            amount_raw = hex_or_bytes_to_int(tx_log.data)
        elif len(tx_log.topics) == 1 and len(tx_log.data) == 96:  # malformed erc20 approve (finance.vote)  # noqa: E501
            owner_address = hex_or_bytes_to_address(tx_log.data[:32])
            spender_address = hex_or_bytes_to_address(tx_log.data[32:64])
            amount_raw = hex_or_bytes_to_int(tx_log.data[64:])
        else:
            log.debug(
                f'Got an ERC20 approve event with unknown structure '
                f'in transaction {transaction.tx_hash.hex()}',
            )
            return DEFAULT_DECODING_OUTPUT

        if not any(self.base.is_tracked(x) for x in (owner_address, spender_address)):
            return DEFAULT_DECODING_OUTPUT

        amount = token_normalized_value(token_amount=amount_raw, token=token)
        if amount == ZERO:
            notes = f'Revoke {token.symbol} spending approval of {owner_address} by {spender_address}'  # noqa: E501
        else:
            notes = f'Set {token.symbol} spending approval of {owner_address} by {spender_address} to {amount}'  # noqa: E501
        event = self.base.make_event_from_transaction(
            transaction=transaction,
            tx_log=tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=token,
            balance=Balance(amount=amount),
            location_label=owner_address,
            notes=notes,
            address=spender_address,
        )
        return DecodingOutput(event=event)

    def _maybe_decode_simple_transactions(
            self,
            tx: EvmTransaction,
            tx_receipt: EvmTxReceipt,
    ) -> list['EvmEvent']:
        """Decodes normal ETH transfers, internal transactions and gas cost payments"""
        events: list[EvmEvent] = []
        # check for gas spent
        direction_result = self.base.decode_direction(tx.from_address, tx.to_address)
        if direction_result is not None:
            event_type, location_label, _, _, _ = direction_result
            if event_type in OUTGOING_EVENT_TYPES:
                eth_burned_as_gas = self._calculate_gas_burned(tx)
                events.append(self.base.make_event_next_index(
                    tx_hash=tx.tx_hash,
                    timestamp=tx.timestamp,
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.FEE,
                    asset=self.value_asset,
                    balance=Balance(amount=eth_burned_as_gas),
                    location_label=location_label,
                    notes=f'Burned {eth_burned_as_gas} {self.value_asset.symbol} for gas',
                    counterparty=CPT_GAS,
                ))

        # Decode internal transactions after gas so gas is always 0 indexed
        self._maybe_decode_internal_transactions(
            tx=tx,
            tx_receipt=tx_receipt,
            events=events,
        )

        if tx_receipt.status is False or direction_result is None:
            # Not any other action to do for failed transactions or transaction where
            # any tracked address is not involved
            return events

        # now decode the actual transaction eth transfer itself
        amount = ZERO if tx.value == 0 else from_wei(FVal(tx.value))
        if tx.to_address is None:
            if not self.base.is_tracked(tx.from_address):
                return events

            events.append(self.base.make_event_next_index(  # contract deployment
                tx_hash=tx.tx_hash,
                timestamp=tx.timestamp,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.DEPLOY,
                asset=self.value_asset,
                balance=Balance(amount=amount),
                location_label=tx.from_address,
                notes='Contract deployment',
                address=None,  # TODO: Find out contract address
            ))
            return events

        if amount == ZERO:
            return events

        if (eth_event := self._get_eth_transfer_event(tx)) is not None:
            events.append(eth_event)
        return events

    def _maybe_decode_erc20_721_transfer(
            self,
            token: Optional[EvmToken],
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],  # pylint: disable=unused-argument
            action_items: list[ActionItem],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> DecodingOutput:
        if tx_log.topics[0] != ERC20_OR_ERC721_TRANSFER:
            return DEFAULT_DECODING_OUTPUT

        if self._is_non_conformant_erc721(tx_log.address) or len(tx_log.topics) == 4:  # typical ERC721 has 3 indexed args  # noqa: E501
            token_kind = EvmTokenKind.ERC721
        elif len(tx_log.topics) == 3:  # typical ERC20 has 2 indexed args
            token_kind = EvmTokenKind.ERC20
        else:
            log.debug(f'Failed to decode token with address {tx_log.address} due to inability to match token type')  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        if token is None:
            try:
                found_token = get_or_create_evm_token(
                    userdb=self.database,
                    evm_address=tx_log.address,
                    chain_id=self.evm_inquirer.chain_id,
                    token_kind=token_kind,
                    evm_inquirer=self.evm_inquirer,
                    seen=TokenSeenAt(tx_hash=transaction.tx_hash),
                )
            except NotERC20Conformant:
                return DEFAULT_DECODING_OUTPUT  # ignore non-ERC20 transfers for now
        else:
            found_token = token

        transfer = self.base.decode_erc20_721_transfer(
            token=found_token,
            tx_log=tx_log,
            transaction=transaction,
        )
        if transfer is None:
            return DEFAULT_DECODING_OUTPUT

        for idx, action_item in enumerate(action_items):
            if action_item.asset == found_token and action_item.amount == transfer.balance.amount and action_item.from_event_type == transfer.event_type and action_item.from_event_subtype == transfer.event_subtype:  # noqa: E501
                if action_item.action == 'skip':
                    action_items.pop(idx)
                    return DEFAULT_DECODING_OUTPUT
                if action_item.action == 'skip & keep':
                    # the action item is skipped but kept in the list of action items. Is used
                    # to propagate information between event decoders and enrichers
                    continue

                # else atm only transform
                if action_item.to_event_type is not None:
                    transfer.event_type = action_item.to_event_type
                if action_item.to_event_subtype is not None:
                    transfer.event_subtype = action_item.to_event_subtype
                if action_item.to_notes is not None:
                    transfer.notes = action_item.to_notes
                if action_item.to_counterparty is not None:
                    transfer.counterparty = action_item.to_counterparty
                if action_item.extra_data is not None:
                    transfer.extra_data = action_item.extra_data

                if action_item.paired_event_data is not None:
                    # If there is a paired event to this, take care of the order
                    out_event = transfer
                    in_event = action_item.paired_event_data[0]
                    if action_item.paired_event_data[1] is True:
                        out_event = action_item.paired_event_data[0]
                        in_event = transfer
                    maybe_reshuffle_events(
                        ordered_events=[out_event, in_event],
                        events_list=decoded_events + [transfer],
                    )

                action_items.pop(idx)
                break  # found an action item and acted on it

        # Add additional information to transfers for different protocols
        enrichment_output = self._enrich_protocol_tranfers(
            context=EnricherContext(
                tx_log=tx_log,
                transaction=transaction,
                action_items=action_items,
                all_logs=all_logs,
                token=found_token,
                event=transfer,
            ),
        )
        return DecodingOutput(
            event=transfer,
            matched_counterparty=enrichment_output.matched_counterparty,
            refresh_balances=enrichment_output.refresh_balances,
        )

    def _post_process(self, refresh_balances: bool) -> None:
        """
        Method that handles actions that have to be taken after a batch of transactions gets
        decoded. Currently may only send a websocket message to the frontend to refresh balances.
        The caller of decode_transactions should call this method after a batch of transactions
        has been decoded.
        """
        if refresh_balances is True:
            self.msg_aggregator.add_message(
                message_type=WSMessageType.REFRESH_BALANCES,
                data={
                    'type': 'blockchain_balances',
                    'blockchain': self.evm_inquirer.chain_id.to_blockchain().serialize(),
                },
            )

    def _chain_specific_decoder_initialization(
            self,
            decoder: 'DecoderInterface',  # pylint: disable=unused-argument
    ) -> None:
        """Custom initialization for each decoder, based on the type of EVM chain.

        This is a no-op by default
        """
        return None

    def _chain_specific_post_decoding_rules(
            self,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
    ) -> list[tuple[int, Callable]]:
        """Custom post-decoding rules for specific chains. This is a no-op by default."""
        return []

    def _calculate_gas_burned(self, tx: EvmTransaction) -> FVal:
        """Calculates gas burn based on relevant chain's formula."""
        return from_wei(FVal(tx.gas_used * tx.gas_price))

    # -- methods to be implemented by child classes --

    @abstractmethod
    def _enrich_protocol_tranfers(self, context: EnricherContext) -> TransferEnrichmentOutput:
        """
        Decode special transfers made by contract execution for example at the moment
        of depositing assets or withdrawing.
        It assumes that the event being decoded has been already filtered and is a
        transfer.
        """

    @staticmethod
    @abstractmethod
    def _is_non_conformant_erc721(address: ChecksumEvmAddress) -> bool:
        """Determine whether the address is a non-conformant erc721 for the chain"""

    @staticmethod
    @abstractmethod
    def _address_is_exchange(address: ChecksumEvmAddress) -> Optional[str]:
        """Takes an address and returns if it's an exchange in the given chain
        and the counterparty to use if it is."""

    if __debug__:
        def _check_correct_types(self, decoded_events: list['EvmEvent']) -> bool:
            """
            Check that the decoded events have the expected combination of event type
            and subtype from its decoder mappings
            """
            unexpected_types = set()
            for event in decoded_events:
                if event.counterparty is None:
                    continue

                expected_mappings = self.events_types_tuples.get(event.counterparty)
                if expected_mappings is None:
                    continue

                if (
                    event.event_type not in expected_mappings and
                    event.event_subtype not in expected_mappings[event.event_type]
                ):
                    unexpected_types.add((event.event_type, event.event_subtype, event.counterparty))  # noqa: E501

            assert len(unexpected_types) == 0, f'Found the following unexpected types {unexpected_types}'  # noqa: E501
            return True


class EVMTransactionDecoderWithDSProxy(EVMTransactionDecoder, metaclass=ABCMeta):
    def __init__(
            self,
            database: 'DBHandler',
            evm_inquirer: 'EvmNodeInquirerWithDSProxy',
            transactions: 'EvmTransactions',
            value_asset: AssetWithOracles,
            event_rules: list[EventDecoderFunction],
            misc_counterparties: list[CounterpartyDetails],
            base_tools: BaseDecoderToolsWithDSProxy,
    ):
        super().__init__(
            database=database,
            evm_inquirer=evm_inquirer,
            transactions=transactions,
            value_asset=value_asset,
            event_rules=event_rules,
            misc_counterparties=misc_counterparties,
            base_tools=base_tools,
        )
        self.evm_inquirer: EvmNodeInquirerWithDSProxy  # Set explicit type
        self.base: BaseDecoderToolsWithDSProxy  # Set explicit type
