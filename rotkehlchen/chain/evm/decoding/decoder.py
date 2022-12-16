import importlib
import logging
import pkgutil
from types import ModuleType
from typing import TYPE_CHECKING, Any, Callable, Optional, Protocol, Union

from gevent.lock import Semaphore

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import AssetWithOracles, EvmToken
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.constants import ZERO
from rotkehlchen.db.constants import HISTORY_MAPPING_STATE_DECODED
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery, HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import InputError, ModuleLoadingError, RemoteError
from rotkehlchen.errors.serialization import ConversionError, DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction, EVMTxHash, Location, TimestampMS
from rotkehlchen.utils.misc import from_wei, ts_sec_to_ms
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin

from .base import BaseDecoderTools
from .constants import CPT_GAS
from .structures import ActionItem

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
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
            decoded_events: list[HistoryBaseEntry],
            action_items: list[ActionItem],
    ) -> Optional[HistoryBaseEntry]:
        ...


class EVMTransactionDecoder():

    def __init__(
            self,
            database: 'DBHandler',
            evm_inquirer: 'EvmNodeInquirer',
            transactions: 'EvmTransactions',
            value_asset: AssetWithOracles,
            event_rules: list[EventDecoderFunction],
            misc_counterparties: list[str],
            address_is_exchange_fn: Callable[[ChecksumEvmAddress], Optional[str]],
    ):
        """
        Initialize an evm chain transaction decoder module for a particular chain.

        `value_asset` is the asset that is normally transferred at value transfers
        and the one that is spent for gas in this chain

        `event_rules` is a list of callables to act as decoding rules for all tx
        receipt logs decoding for the particular chain

        `misc_counterparties` is a list of counterparties not associated with any specific
        decoder that should be included for this decoder modules.

        `address_is_exchange_fn` a function that takes an address and returns if it's
        an exchange in the given chain and the counterparty to use if it is.
        """
        self.database = database
        self.misc_counterparties = [CPT_GAS] + misc_counterparties
        self.all_counterparties: set[str] = set()
        self.evm_inquirer = evm_inquirer
        self.transactions = transactions
        self.msg_aggregator = database.msg_aggregator
        self.chain_modules_root = f'rotkehlchen.chain.{self.evm_inquirer.chain_name}.modules'
        self.chain_modules_prefix_length = len(self.chain_modules_root)
        self.dbevmtx = DBEvmTx(self.database)
        self.dbevents = DBHistoryEvents(self.database)
        self.base = BaseDecoderTools(
            database=database,
            address_is_exchange_fn=address_is_exchange_fn,
        )
        self.event_rules = event_rules
        self.token_enricher_rules: list[Callable] = []  # enrichers to run for token transfers
        self.value_asset = value_asset
        self.initialize_all_decoders()
        self.undecoded_tx_query_lock = Semaphore()

    def _recursively_initialize_decoders(
            self,
            package: Union[str, ModuleType],
    ) -> tuple[
            dict[ChecksumEvmAddress, tuple[Any, ...]],
            list[Callable],
            list[Callable],
    ]:
        if isinstance(package, str):
            package = importlib.import_module(package)
        address_results = {}
        rules_results = []
        enricher_results = []
        for _, name, is_pkg in pkgutil.walk_packages(package.__path__):
            full_name = package.__name__ + '.' + name
            if full_name == __name__:
                continue  # skip -- this is this source file

            if is_pkg:
                submodule = importlib.import_module(full_name)
                # take module name, transform it and find decoder if exists
                class_name = full_name[self.chain_modules_prefix_length:].translate({ord('.'): None})  # noqa: E501
                parts = class_name.split('_')
                class_name = ''.join([x.capitalize() for x in parts])
                submodule_decoder = getattr(submodule, f'{class_name}Decoder', None)

                if submodule_decoder:
                    if class_name in self.decoders:
                        raise ModuleLoadingError(f'{self.evm_inquirer.chain_name} decoder with name {class_name} already loaded')  # noqa: E501

                    try:  # not giving kwargs since, kwargs name can differ
                        self.decoders[class_name] = submodule_decoder(
                            self.evm_inquirer,  # evm_inquirer
                            self.base,  # base_tools
                            self.msg_aggregator,  # msg_aggregator
                        )
                    except (UnknownAsset, WrongAssetType) as e:
                        self.msg_aggregator.add_error(
                            f'Failed at initialization of {self.evm_inquirer.chain_name} '
                            f'{class_name} decoder due to asset mismatch: {str(e)}',
                        )
                        continue

                    address_results.update(self.decoders[class_name].addresses_to_decoders())
                    rules_results.extend(self.decoders[class_name].decoding_rules())
                    enricher_results.extend(self.decoders[class_name].enricher_rules())
                    self.all_counterparties.update(self.decoders[class_name].counterparties())

                recursive_addrs, recursive_rules, recurisve_enricher_results = self._recursively_initialize_decoders(full_name)  # noqa: E501
                address_results.update(recursive_addrs)
                rules_results.extend(recursive_rules)
                enricher_results.extend(recurisve_enricher_results)

        return address_results, rules_results, enricher_results

    def initialize_all_decoders(self) -> None:
        """Recursively check all submodules to get all decoder address mappings and rules
        """
        self.decoders: dict[str, 'DecoderInterface'] = {}
        address_result, rules_result, enrichers_result = self._recursively_initialize_decoders(self.chain_modules_root)  # noqa: E501
        self.address_mappings = address_result
        self.event_rules.extend(rules_result)
        self.token_enricher_rules.extend(enrichers_result)
        # update with counterparties not in any module
        self.all_counterparties.update(self.misc_counterparties)

    def reload_from_db(self, cursor: 'DBCursor') -> None:
        """Reload all related settings from DB so that decoding happens with latest"""
        self.base.refresh_tracked_accounts(cursor)
        for _, decoder in self.decoders.items():
            if isinstance(decoder, CustomizableDateMixin):
                decoder.reload_settings(cursor)

    def try_all_rules(
            self,
            token: Optional[EvmToken],
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list[HistoryBaseEntry],
            action_items: list[ActionItem],
    ) -> Optional[HistoryBaseEntry]:
        for rule in self.event_rules:
            event = rule(token=token, tx_log=tx_log, transaction=transaction, decoded_events=decoded_events, action_items=action_items)  # noqa: E501
            if event:
                return event

        return None

    def decode_by_address_rules(
            self,
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list[HistoryBaseEntry],
            all_logs: list[EvmTxReceiptLog],
            action_items: list[ActionItem],
    ) -> tuple[Optional[HistoryBaseEntry], list[ActionItem]]:
        """
        Sees if the log is on an address for which we have specific decoders and calls it

        Should catch all underlying errors these decoders will raise. So far known are:
        - DeserializationError
        - ConversionError
        - UnknownAsset
        """
        mapping_result = self.address_mappings.get(tx_log.address)
        if mapping_result is None:
            return None, []
        method = mapping_result[0]

        try:
            if len(mapping_result) == 1:
                result = method(tx_log, transaction, decoded_events, all_logs, action_items)
            else:
                result = method(tx_log, transaction, decoded_events, all_logs, action_items, *mapping_result[1:])  # noqa: E501
        except (DeserializationError, ConversionError, UnknownAsset) as e:
            log.debug(
                f'Decoding tx log with index {tx_log.log_index} of transaction '
                f'{transaction.tx_hash.hex()} through {method.__name__} failed due to {str(e)}')
            return None, []

        return result

    def decode_transaction(
            self,
            write_cursor: 'DBCursor',
            transaction: EvmTransaction,
            tx_receipt: EvmTxReceipt,
    ) -> list[HistoryBaseEntry]:
        """Decodes an evm transaction and its receipt and saves result in the DB"""
        self.base.reset_sequence_counter()
        # check if any eth transfer happened in the transaction, including in internal transactions
        events = self._maybe_decode_simple_transactions(transaction, tx_receipt)
        action_items: list[ActionItem] = []

        # decode transaction logs from the receipt
        for tx_log in tx_receipt.logs:
            event, new_action_items = self.decode_by_address_rules(tx_log, transaction, events, tx_receipt.logs, action_items)  # noqa: E501
            action_items.extend(new_action_items)
            if event:
                events.append(event)
                continue

            token = GlobalDBHandler.get_evm_token(
                address=tx_log.address,
                chain_id=self.evm_inquirer.chain_id,
            )
            event = self.try_all_rules(
                token=token,
                tx_log=tx_log,
                transaction=transaction,
                decoded_events=events,
                action_items=action_items,
            )
            if event:
                events.append(event)

        if len(events) == 0 and (eth_event := self._get_eth_transfer_event(transaction)) is not None:  # noqa: E501
            events = [eth_event]

        self.dbevents.add_history_events(
            write_cursor=write_cursor,
            history=events,
            chain_id=self.evm_inquirer.chain_id,
        )
        write_cursor.execute(
            'INSERT OR IGNORE INTO evm_tx_mappings(tx_hash, chain_id, value) VALUES(?, ?, ?)',
            (transaction.tx_hash, self.evm_inquirer.chain_id.serialize_for_db(), HISTORY_MAPPING_STATE_DECODED),  # noqa: E501
        )

        return sorted(events, key=lambda x: x.sequence_index, reverse=False)

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
    ) -> list[HistoryBaseEntry]:
        """Make sure that receipts are pulled + events decoded for the given transaction hashes.

        The transaction hashes must exist in the DB at the time of the call

        May raise:
        - DeserializationError if there is a problem with conacting a remote to get receipts
        - RemoteError if there is a problem with contacting a remote to get receipts
        - InputError if the transaction hash is not found in the DB
        """
        events = []
        with self.database.conn.read_ctx() as cursor:
            self.reload_from_db(cursor)
            # If no transaction hashes are passed, decode all transactions.
            if tx_hashes is None:
                tx_hashes = []
                for entry in cursor.execute('SELECT tx_hash FROM evm_transactions'):
                    tx_hashes.append(EVMTxHash(entry[0]))

        with self.database.user_write() as cursor:
            for tx_hash in tx_hashes:
                try:
                    receipt = self.transactions.get_or_query_transaction_receipt(cursor, tx_hash)  # noqa: E501
                except RemoteError as e:
                    raise InputError(f'{self.evm_inquirer.chain_name} hash {tx_hash.hex()} does not correspond to a transaction') from e  # noqa: E501

                # TODO: Change this if transaction filter query can accept multiple hashes
                txs = self.dbevmtx.get_evm_transactions(
                    cursor=cursor,
                    filter_=EvmTransactionsFilterQuery.make(tx_hash=tx_hash, chain_id=self.evm_inquirer.chain_id),  # noqa: E501
                    has_premium=True,  # ignore limiting here
                )
                events.extend(self.get_or_decode_transaction_events(
                    write_cursor=cursor,
                    transaction=txs[0],
                    tx_receipt=receipt,
                    ignore_cache=ignore_cache,
                ))

        return events

    def get_or_decode_transaction_events(
            self,
            write_cursor: 'DBCursor',
            transaction: EvmTransaction,
            tx_receipt: EvmTxReceipt,
            ignore_cache: bool,
    ) -> list[HistoryBaseEntry]:
        """Get a transaction's events if existing in the DB or decode them"""
        serialized_chain_id = self.evm_inquirer.chain_id.serialize_for_db()
        if ignore_cache is True:  # delete all decoded events
            self.dbevents.delete_events_by_tx_hash(
                write_cursor=write_cursor,
                tx_hashes=[transaction.tx_hash],
                chain_id=self.evm_inquirer.chain_id,
            )
            write_cursor.execute(
                'DELETE from evm_tx_mappings WHERE tx_hash=? AND chain_id=? AND value=?',
                (transaction.tx_hash, serialized_chain_id, HISTORY_MAPPING_STATE_DECODED),
            )
        else:  # see if events are already decoded and return them
            write_cursor.execute(
                'SELECT COUNT(*) from evm_tx_mappings WHERE tx_hash=? AND chain_id=? AND value=?',  # noqa: E501
                (transaction.tx_hash, serialized_chain_id, HISTORY_MAPPING_STATE_DECODED),
            )
            if write_cursor.fetchone()[0] != 0:  # already decoded and in the DB
                events = self.dbevents.get_history_events(
                    cursor=write_cursor,
                    filter_query=HistoryEventFilterQuery.make(
                        event_identifiers=[transaction.tx_hash],
                    ),
                    has_premium=True,  # for this function we don't limit anything
                )
                return events

        # else we should decode now
        events = self.decode_transaction(write_cursor, transaction, tx_receipt)
        return events

    def _maybe_decode_internal_transactions(
            self,
            tx: EvmTransaction,
            tx_receipt: EvmTxReceipt,
            events: list[HistoryBaseEntry],
            ts_ms: TimestampMS,
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

            event_type, location_label, counterparty, verb = direction_result
            preposition = 'to' if verb == 'Send' else 'from'
            events.append(HistoryBaseEntry(
                event_identifier=tx.tx_hash,
                sequence_index=self.base.get_next_sequence_counter(),
                timestamp=ts_ms,
                location=Location.BLOCKCHAIN,
                location_label=location_label,
                asset=self.value_asset,
                balance=Balance(amount=amount),
                notes=f'{verb} {amount} {self.value_asset.symbol} {preposition} {counterparty}',
                event_type=event_type,
                event_subtype=HistoryEventSubType.NONE,
                counterparty=counterparty,
            ))

    def _get_eth_transfer_event(self, tx: EvmTransaction) -> Optional[HistoryBaseEntry]:
        direction_result = self.base.decode_direction(
            from_address=tx.from_address,
            to_address=tx.to_address,
        )
        if direction_result is None:
            return None
        event_type, location_label, counterparty, verb = direction_result
        amount = ZERO if tx.value == 0 else from_wei(FVal(tx.value))
        preposition = 'to' if verb == 'Send' else 'from'
        return HistoryBaseEntry(
            event_identifier=tx.tx_hash,
            sequence_index=self.base.get_next_sequence_counter(),
            timestamp=ts_sec_to_ms(tx.timestamp),
            location=Location.BLOCKCHAIN,
            location_label=location_label,
            asset=self.value_asset,
            balance=Balance(amount=amount),
            notes=f'{verb} {amount} {self.value_asset.symbol} {preposition} {counterparty}',
            event_type=event_type,
            event_subtype=HistoryEventSubType.NONE,
            counterparty=counterparty,
        )

    def _maybe_decode_simple_transactions(
            self,
            tx: EvmTransaction,
            tx_receipt: EvmTxReceipt,
    ) -> list[HistoryBaseEntry]:
        """Decodes normal ETH transfers, internal transactions and gas cost payments"""
        events: list[HistoryBaseEntry] = []
        ts_ms = ts_sec_to_ms(tx.timestamp)

        # check for gas spent
        direction_result = self.base.decode_direction(tx.from_address, tx.to_address)
        if direction_result is not None:
            event_type, location_label, _, _ = direction_result
            if event_type in (HistoryEventType.SPEND, HistoryEventType.TRANSFER):
                eth_burned_as_gas = from_wei(FVal(tx.gas_used * tx.gas_price))
                events.append(HistoryBaseEntry(
                    event_identifier=tx.tx_hash,
                    sequence_index=self.base.get_next_sequence_counter(),
                    timestamp=ts_ms,
                    location=Location.BLOCKCHAIN,
                    location_label=location_label,
                    asset=self.value_asset,
                    balance=Balance(amount=eth_burned_as_gas),
                    notes=f'Burned {eth_burned_as_gas} {self.value_asset.symbol} for gas',
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.FEE,
                    counterparty=CPT_GAS,
                ))

        # Decode internal transactions after gas so gas is always 0 indexed
        self._maybe_decode_internal_transactions(
            tx=tx,
            tx_receipt=tx_receipt,
            events=events,
            ts_ms=ts_ms,
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

            events.append(HistoryBaseEntry(  # contract deployment
                event_identifier=tx.tx_hash,
                sequence_index=self.base.get_next_sequence_counter(),
                timestamp=ts_ms,
                location=Location.BLOCKCHAIN,
                location_label=tx.from_address,
                asset=self.value_asset,
                balance=Balance(amount=amount),
                notes='Contract deployment',
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.DEPLOY,
                counterparty=None,  # TODO: Find out contract address
            ))
            return events

        if amount == ZERO:
            return events

        if (eth_event := self._get_eth_transfer_event(tx)) is not None:
            events.append(eth_event)
        return events
