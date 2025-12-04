import importlib
import logging
import pkgutil
from abc import ABC, abstractmethod
from contextlib import suppress
from typing import TYPE_CHECKING, Generic, Literal, TypeVar

from gevent.lock import Semaphore
from more_itertools import peekable

from rotkehlchen.api.websockets.typedefs import ProgressUpdateSubType, WSMessageType
from rotkehlchen.db.constants import TX_DECODED, TX_SPAM
from rotkehlchen.db.dbtx import DBCommonTx, T_Transaction, T_TxHash, T_TxNotDecodedFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.errors.serialization import ConversionError, DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import BLOCKCHAIN_LOCATIONS_TYPE
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin

from .constants import CPT_GAS
from .structures import T_Event
from .tools import BaseDecoderTools
from .types import CounterpartyDetails, SupportsAddition

if TYPE_CHECKING:
    from types import ModuleType

    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.premium.premium import Premium

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


T_DecodingRules = TypeVar('T_DecodingRules', bound=SupportsAddition)
T_DecoderInterface = TypeVar('T_DecoderInterface')
T_DecoderTools = TypeVar('T_DecoderTools', bound=BaseDecoderTools)
T_TransactionDecodingContext = TypeVar('T_TransactionDecodingContext')
T_DBTx = TypeVar('T_DBTx', bound=DBCommonTx)
T_EventFilterQuery = TypeVar('T_EventFilterQuery')


class TransactionDecoder(ABC, Generic[T_Transaction, T_DecodingRules, T_DecoderInterface, T_TxHash, T_Event, T_TransactionDecodingContext, T_DecoderTools, T_DBTx, T_EventFilterQuery, T_TxNotDecodedFilterQuery]):  # noqa: E501
    def __init__(
            self,
            database: 'DBHandler',
            dbtx: T_DBTx,
            tx_mappings_table: Literal['evm_tx_mappings', 'solana_tx_mappings'],
            chain_name: str,
            value_asset: 'AssetWithOracles',
            rules: T_DecodingRules,
            misc_counterparties: list[CounterpartyDetails],
            base_tools: T_DecoderTools,
            premium: 'Premium | None' = None,
            possible_decoding_exceptions: tuple[type[Exception], ...] | None = None,
    ) -> None:
        """Initialize a transaction decoder module for a particular blockchain.

        `value_asset` is the asset that is normally transferred at value transfers
        and the one that is spent for gas in this chain

        `misc_counterparties` is a list of counterparties not associated with any specific
        decoder that should be included for this decoder modules.

        `premium` is the Premium object for checking user limits
        """
        self.database = database
        self.dbtx = dbtx
        self.tx_mappings_table = tx_mappings_table
        self.premium = premium
        self.misc_counterparties = [CounterpartyDetails(identifier=CPT_GAS, label='gas', icon='lu-flame')] + misc_counterparties  # noqa: E501
        self.msg_aggregator = database.msg_aggregator
        self.chain_name = chain_name
        self.chain_modules_root = f'rotkehlchen.chain.{self.chain_name}.modules'
        self.chain_modules_prefix_length = len(self.chain_modules_root)
        self.dbevents = DBHistoryEvents(self.database)
        self.base = base_tools
        self.value_asset = value_asset
        self.rules = rules
        self.decoders: dict[str, T_DecoderInterface] = {}
        self.possible_decoding_exceptions: tuple[type[Exception], ...] = (
            UnknownAsset,
            WrongAssetType,
            DeserializationError,
            IndexError,
            ValueError,
            ConversionError,
            RemoteError,
        )
        if possible_decoding_exceptions is not None:
            self.possible_decoding_exceptions += possible_decoding_exceptions

        # Add the built-in decoders
        self._add_builtin_decoders(self.rules)
        # Recursively check all submodules to get all decoder address mappings and rules
        self.rules += self._recursively_initialize_decoders(self.chain_modules_root)
        self.undecoded_tx_query_lock = Semaphore()

    @abstractmethod
    def _add_builtin_decoders(self, rules: T_DecodingRules) -> None:
        """Adds decoders that should be built-in for every decoding run

        Think: Perhaps we can move them under a specific directory and use the
        normal loading?
        """

    @abstractmethod
    def _add_single_decoder(
            self,
            class_name: str,
            decoder_class: type[T_DecoderInterface],
            rules: T_DecodingRules,
    ) -> None:
        """Initialize a single decoder, add it to the set of decoders to use
        and append its rules to the passed rules
        """

    @staticmethod
    @abstractmethod
    def _load_default_decoding_rules() -> T_DecodingRules:
        """Return a fresh rules object with all chain-specific defaults."""

    def _recursively_initialize_decoders(
            self,
            package: 'str | ModuleType',
    ) -> T_DecodingRules:
        """Discover decoder modules under `package` and merge their rules.
        May raise:
         - ModuleLoadingError if a decoder is registered more than once
         - ImportError for unexpected import failures while loading submodules
        """
        if isinstance(package, str):
            package = importlib.import_module(package)

        rules = self._load_default_decoding_rules()
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

    def _reload_single_decoder(self, cursor: 'DBCursor', decoder: T_DecoderInterface) -> None:
        """Reload data for a single decoder"""
        if isinstance(decoder, CustomizableDateMixin):
            decoder.reload_settings(cursor)

    def reload_data(self, cursor: 'DBCursor') -> None:
        """Reload all related settings from DB and data that any decoder may require from the chain
        so that decoding happens with latest data
        """
        self.base.refresh_tracked_accounts(cursor)
        for decoder in self.decoders.values():
            self._reload_single_decoder(cursor, decoder)

    def reload_specific_decoders(self, cursor: 'DBCursor', decoders: set[str]) -> None:
        """Reload DB data for the given decoders. Decoders are identified by the class name
        (without the Decoder suffix)
        """
        self.base.refresh_tracked_accounts(cursor)
        for decoder_name in decoders:
            if (decoder := self.decoders.get(decoder_name)) is None:
                log.error(f'Requested reloading of data for unknown {self.chain_name} decoder {decoder_name}')  # noqa: E501
                continue

            self._reload_single_decoder(cursor, decoder)

    @abstractmethod
    def _get_tx_not_decoded_filter_query(self, limit: int | None) -> T_TxNotDecodedFilterQuery:
        """Return a filter query for loading txs that still need decoding for this chain using
        the specified limit.
        """

    def get_and_decode_undecoded_transactions(
            self,
            limit: int | None = None,
            send_ws_notifications: bool = False,
    ) -> list[T_TxHash]:
        """Checks the DB for up to `limit` undecoded transactions and decodes them.
        If a list of addresses is provided then only the transactions involving those
        addresses are decoded.

        This is protected by concurrent access from a lock"""
        with self.undecoded_tx_query_lock:
            log.debug(f'Starting task to process undecoded transactions for {self.chain_name} with {limit=}')  # noqa: E501
            hashes = self.dbtx.get_transaction_hashes_not_decoded(
                filter_query=self._get_tx_not_decoded_filter_query(limit=limit),
            )
            if len(hashes) != 0:
                log.debug(f'Will decode {len(hashes)} transactions for {self.chain_name}')
                self.decode_transaction_hashes(
                    ignore_cache=False,
                    tx_hashes=hashes,
                    send_ws_notifications=send_ws_notifications,
                )

            log.debug(f'Finished task to process undecoded transactions for {self.chain_name} with {limit=}')  # noqa: E501
            return hashes

    def decode_and_get_transaction_hashes(
            self,
            ignore_cache: bool,
            tx_hashes: list[T_TxHash],
            send_ws_notifications: bool = False,
            delete_customized: bool = False,
    ) -> list[T_Event]:
        """
        Thin wrapper around _decode_transaction_hashes that returns the decoded events.

        May raise:
        - DeserializationError if there is a problem with contacting a remote to get receipts
        - RemoteError if there is a problem with contacting a remote to get receipts
        - InputError if the transaction hash is not found in the DB
        """
        events: list[T_Event] = []
        self._decode_transaction_hashes(
            ignore_cache=ignore_cache,
            tx_hashes=tx_hashes,
            events=events,
            send_ws_notifications=send_ws_notifications,
            delete_customized=delete_customized,
        )
        return events

    def decode_transaction_hashes(
            self,
            ignore_cache: bool,
            tx_hashes: list[T_TxHash],
            send_ws_notifications: bool = False,
            delete_customized: bool = False,
    ) -> None:
        """
        Thin wrapper around _decode_transaction_hashes that ignores decoded events

        May raise:
        - DeserializationError if there is a problem with contacting a remote to get receipts
        - RemoteError if there is a problem with contacting a remote to get receipts
        - InputError if the transaction hash is not found in the DB
        """
        self._decode_transaction_hashes(
            ignore_cache=ignore_cache,
            tx_hashes=tx_hashes,
            events=None,
            send_ws_notifications=send_ws_notifications,
            delete_customized=delete_customized,
        )

    @abstractmethod
    def _load_transaction_context(
            self,
            cursor: 'DBCursor',
            tx_hash: T_TxHash,
    ) -> T_TransactionDecodingContext:
        """Return the chain-specific decoding context for `tx_hash`.

        The context can be any type (tuple, dataclass, etc.) that the subclass
        understands and will later pass to `_decode_transaction_from_context`.
        Implementations should raise `InputError` if the transaction cannot be
        located or fetched.
        """

    @abstractmethod
    def _decode_transaction_from_context(
            self,
            context: T_TransactionDecodingContext,
            ignore_cache: bool,
            delete_customized: bool,
    ) -> tuple[list[T_Event], bool, set[str] | None]:
        """Decode a transaction using the previously loaded `context`.

        Returns `(events, refresh_balances, reload_decoders)` where:
        - `events` is the list of decoded events for this transaction,
        - `refresh_balances` signals whether balances must be refreshed,
        - `reload_decoders` lists decoder names that should be reloaded (or `None`).
        """

    @abstractmethod
    def _make_event_filter_query(self, tx_ref: T_TxHash) -> T_EventFilterQuery:
        """Make a query to filter events by the given tx_ref."""

    def _maybe_load_or_purge_events_from_db(
            self,
            transaction: T_Transaction,
            tx_ref: T_TxHash,
            location: BLOCKCHAIN_LOCATIONS_TYPE,
            ignore_cache: bool,
            delete_customized: bool,
    ) -> list[T_Event] | None:
        """Load events from the DB for the given tx if they are already decoded and return them,
        or purge them from the DB if ignore_cache is True.
        Returns the list of events or None if the tx was not decoded or the events were purged.
        """
        with self.database.conn.read_ctx() as cursor:
            tx_id = transaction.get_or_query_db_id(cursor)

        if ignore_cache is True:  # delete all decoded events for the given tx ref
            with self.database.user_write() as write_cursor:
                self.dbevents.delete_events_by_tx_ref(
                    write_cursor=write_cursor,
                    tx_refs=[tx_ref],
                    location=location,
                    delete_customized=delete_customized,
                )
                write_cursor.execute(
                    f'DELETE from {self.tx_mappings_table} WHERE tx_id=? AND value IN (?, ?)',
                    (tx_id, TX_DECODED, TX_SPAM),
                )
        else:  # see if events are already decoded and return them
            with self.database.conn.read_ctx() as cursor:
                cursor.execute(
                    f'SELECT COUNT(*) from {self.tx_mappings_table} WHERE tx_id=? AND value=?',
                    (tx_id, TX_DECODED),
                )
                if cursor.fetchone()[0] != 0:  # already decoded and in the DB
                    return self.dbevents.get_history_events_internal(  # type: ignore[call-overload]
                        cursor=cursor,
                        filter_query=self._make_event_filter_query(tx_ref),
                    )

        return None

    def _decode_transaction_hashes(
            self,
            ignore_cache: bool,
            tx_hashes: list[T_TxHash],
            events: list[T_Event] | None = None,
            send_ws_notifications: bool = False,
            delete_customized: bool = False,
    ) -> tuple[bool, list[T_Event]]:
        """Make sure that receipts are pulled + events decoded for the given transaction hashes.
        If delete_customized is True then also customized events are deleted before redecoding.

        The transaction hashes must exist in the DB at the time of the call.
        This logic modifies the `events` argument if it isn't none.

        May raise:
        - DeserializationError if there is a problem with contacting a remote to get receipts
        - RemoteError if there is a problem with contacting a remote to get receipts
        - InputError if the transaction hash is not found in the DB
        """
        with self.database.conn.read_ctx() as cursor:
            self.reload_data(cursor)

        refresh_balances, new_events = False, []
        total_transactions = len(tx_hashes)
        log.debug(f'Started logic to decode {total_transactions} transactions from {self.chain_name}')  # noqa: E501
        for tx_index, tx_hash in enumerate(tx_hashes):
            log.debug(f'Decoding logic started for {tx_hash!s} ({self.chain_name})')
            if send_ws_notifications and tx_index % 10 == 0:
                log.debug(f'Processed {tx_index} out of {total_transactions} transactions from {self.chain_name}')  # noqa: E501
                self.msg_aggregator.add_message(
                    message_type=WSMessageType.PROGRESS_UPDATES,
                    data={
                        'chain': self.chain_name,
                        'subtype': str(ProgressUpdateSubType.UNDECODED_TRANSACTIONS),
                        'total': total_transactions,
                        'processed': tx_index,
                    },
                )

            # TODO: Change this if transaction filter query can accept multiple hashes
            with self.database.conn.read_ctx() as cursor:
                context = self._load_transaction_context(
                    cursor=cursor,
                    tx_hash=tx_hash,
                )

            fresh_events, new_refresh_balances, reload_decoders = self._decode_transaction_from_context(  # noqa: E501
                context=context,
                ignore_cache=ignore_cache,
                delete_customized=delete_customized,
            )

            if events is not None:
                events.extend(fresh_events)

            new_events.extend(fresh_events)
            if new_refresh_balances is True:
                refresh_balances = True

            if reload_decoders is not None:
                with self.database.conn.read_ctx() as cursor:
                    self.reload_specific_decoders(cursor, decoders=reload_decoders)

        if send_ws_notifications:
            self.msg_aggregator.add_message(
                message_type=WSMessageType.PROGRESS_UPDATES,
                data={
                    'chain': self.chain_name,
                    'subtype': str(ProgressUpdateSubType.UNDECODED_TRANSACTIONS),
                    'total': total_transactions,
                    'processed': total_transactions,
                },
            )

        return refresh_balances, new_events

    def _write_new_tx_events_to_the_db(
            self,
            events: list[T_Event],
            action_id: str,
            db_id: int,
    ) -> None:
        """Writes new events from a single tx to the DB and sets the decoded flag.

        `action_id` uniquely identifies the tx (for example, chain id + tx hash for EVM txs)
        which is added to the ignored_action_ids if there are no events.
        `db_id` is the id of the transaction in the DB, used in the tx mappings table.
        """
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
                        identifiers=[action_id],
                    )

            write_cursor.execute(
                f'INSERT OR IGNORE INTO {self.tx_mappings_table}(tx_id, value) VALUES(?, ?)',
                (db_id, TX_DECODED),
            )

    def _process_swaps(
            self,
            transaction: T_Transaction,
            decoded_events: list[T_Event],
    ) -> list[T_Event]:
        """Convert trade events into chain-specific swap events.

        Assumes that the decoding logic has already ordered the sequence indexes of trade events
        in the correct spend/receive/fee order with no other events between them (although the
        indexes do not need to be consecutive). If an incomplete or unordered group of Trade events
        is encountered an error will be logged and the original events saved to the db.

        If a swap has multiple spend receive or fee events, then the event_type will be set to
        MULTI_TRADE for all the events in the swap.

        Returns the list of decoded events ordered by sequence index with any complete groups
        of trade events replaced with chain-specific swap events.
        """
        processed_events = []
        trade_subtypes = (HistoryEventSubType.SPEND, HistoryEventSubType.RECEIVE, HistoryEventSubType.FEE)  # noqa: E501
        events_iterator = peekable(iter(decoded_events))
        while (next_event := events_iterator.peek(None)) is not None:
            if (
                    next_event.event_type != HistoryEventType.TRADE or
                    next_event.event_subtype not in trade_subtypes
            ):  # event is not part of a swap - save it and continue
                processed_events.append(next(events_iterator))
                continue

            trade_events: list[T_Event] = []
            event_type = HistoryEventType.TRADE
            for subtype in trade_subtypes:
                subtype_events = []
                while (
                        (next_event := events_iterator.peek(None)) is not None and
                        next_event.event_type == HistoryEventType.TRADE and
                        next_event.event_subtype == subtype
                ):  # match events in the order defined in trade_subtypes
                    subtype_events.append(next(events_iterator))

                if len(subtype_events) > 1:
                    event_type = HistoryEventType.MULTI_TRADE
                elif len(subtype_events) == 0 and subtype != HistoryEventSubType.FEE:  # if no spend or receive was found then the group is incomplete or out of order.  # noqa: E501
                    # If no events yet (failed on SPEND), save next(events_iterator), so that
                    # we move on to the event after in the next while loop iteration.
                    # If some events (failed on RECEIVE), save only the already matched
                    # trade_events so the next event (could be the SPEND of another group) will be
                    # reprocessed in the next iteration of the main while loop.
                    processed_events.extend(trade_events if len(trade_events) > 0 else [next(events_iterator)])  # noqa: E501
                    log.error(
                        'Encountered incomplete or unordered swap event group '
                        f'{trade_events + [next_event]} in transaction {transaction!s}',
                    )
                    trade_events = []
                    break

                trade_events.extend(subtype_events)

            if len(trade_events) == 0:
                continue  # swap group was incomplete or unordered.

            spend_event = trade_events[0]
            for idx, trade_event in enumerate(trade_events):
                processed_events.append(self._create_swap_event(
                    trade_event=trade_event,
                    spend_event=spend_event,
                    sequence_index=spend_event.sequence_index + idx,
                    event_type=event_type,
                ))

        return processed_events

    @abstractmethod
    def _calculate_fees(self, tx: T_Transaction) -> FVal:
        """Calculates the transaction fee using the chain's formula."""

    @abstractmethod
    def _create_swap_event(
            self,
            trade_event: T_Event,
            spend_event: T_Event,
            sequence_index: int,
            event_type: HistoryEventType,
    ) -> T_Event:
        """Creates a chain-specific swap event from trade event data.

        `trade_event` is the main trade/swap event being processed.
        `spend_event` is the "spend" side of the swap (outgoing asset) used as
        the source for consistent metadata across all events in the swap group.

        * Make indexes consecutive (required for retrieving the receive and fee
          events when editing a swap event group via the api)
        * Location label can be different on the spend versus the receive,
          but if its missing, fall back to setting it from the spend event
        * Counterparty, product, and address should be the
          same for the whole group, so set from the spend event
        """

    if __debug__:  # for now only debug as decoders are constant

        def assert_keys_are_unique(self, new_struct: dict, main_struct: dict, class_name: str, type_name: str) -> None:  # noqa: E501
            """Asserts that some decoders keys of new rules are unique"""
            intersection = set(new_struct).intersection(set(main_struct))
            if len(intersection) != 0:
                raise AssertionError(f'{type_name} duplicates found in decoding rules of {self.chain_name} {class_name}: {intersection}')  # noqa: E501
