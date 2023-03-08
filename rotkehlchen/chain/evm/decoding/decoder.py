import importlib
import logging
import pkgutil
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from types import ModuleType
from typing import TYPE_CHECKING, Any, Callable, Optional, Protocol, Union

from gevent.lock import Semaphore

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import AssetWithOracles, EvmToken
from rotkehlchen.assets.utils import TokenSeenAt, get_or_create_evm_token
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import ReloadableDecoderMixin
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.constants import ZERO
from rotkehlchen.db.constants import HISTORY_MAPPING_STATE_DECODED
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery, HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import InputError, ModuleLoadingError, NotERC20Conformant, RemoteError
from rotkehlchen.errors.serialization import ConversionError, DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTokenKind, EvmTransaction, EVMTxHash
from rotkehlchen.utils.misc import from_wei, hex_or_bytes_to_address, hex_or_bytes_to_int
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin

from .base import BaseDecoderTools
from .constants import CPT_GAS, ERC20_APPROVE, ERC20_OR_ERC721_TRANSFER, OUTGOING_EVENT_TYPES
from .structures import ActionItem
from .utils import maybe_reshuffle_events

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
            all_logs: list[EvmTxReceiptLog],
    ) -> tuple[Optional[HistoryBaseEntry], list[ActionItem]]:
        ...


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class DecodingRules():
    address_mappings: dict[ChecksumEvmAddress, tuple[Any, ...]]
    event_rules: list[EventDecoderFunction]
    token_enricher_rules: list[Callable]  # enrichers to run for token transfers
    post_decoding_rules: list[tuple[int, Callable]]  # rules to run after the main decoding loop
    all_counterparties: set[str]

    def __add__(self, other: 'DecodingRules') -> 'DecodingRules':
        if not isinstance(other, DecodingRules):
            raise TypeError(
                f'Can only add DecodingRules to DecodingRules. Got {type(other)}',
            )
        return DecodingRules(
            address_mappings={**self.address_mappings, **other.address_mappings},
            event_rules=self.event_rules + other.event_rules,
            token_enricher_rules=self.token_enricher_rules + other.token_enricher_rules,
            post_decoding_rules=self.post_decoding_rules + other.post_decoding_rules,
            all_counterparties=self.all_counterparties | other.all_counterparties,
        )


class EVMTransactionDecoder(metaclass=ABCMeta):

    def __init__(
            self,
            database: 'DBHandler',
            evm_inquirer: 'EvmNodeInquirer',
            transactions: 'EvmTransactions',
            value_asset: AssetWithOracles,
            event_rules: list[EventDecoderFunction],
            misc_counterparties: list[str],
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
        self.misc_counterparties = [CPT_GAS] + misc_counterparties
        self.evm_inquirer = evm_inquirer
        self.transactions = transactions
        self.msg_aggregator = database.msg_aggregator
        self.chain_modules_root = f'rotkehlchen.chain.{self.evm_inquirer.chain_name}.modules'
        self.chain_modules_prefix_length = len(self.chain_modules_root)
        self.dbevmtx = DBEvmTx(self.database)
        self.dbevents = DBHistoryEvents(self.database)
        self.base = BaseDecoderTools(
            database=database,
            chain_id=self.evm_inquirer.chain_id,
            is_non_conformant_erc721_fn=self._is_non_conformant_erc721,
            address_is_exchange_fn=self._address_is_exchange,
        )
        self.rules = DecodingRules(
            address_mappings={},
            event_rules=[
                self._maybe_decode_erc20_approve,
                self._maybe_decode_erc20_721_transfer,
            ],
            token_enricher_rules=[],
            post_decoding_rules=[],
            all_counterparties=set(self.misc_counterparties),
        )
        self.rules.event_rules.extend(event_rules)
        self.value_asset = value_asset
        self.decoders: dict[str, 'DecoderInterface'] = {}
        # Recursively check all submodules to get all decoder address mappings and rules
        rules = self._recursively_initialize_decoders(self.chain_modules_root)
        self.rules += rules
        # Sort post decoding rules by priority (which is the first element of the tuple)
        self.rules.post_decoding_rules.sort(key=lambda x: x[0])
        self.undecoded_tx_query_lock = Semaphore()

    def _recursively_initialize_decoders(
            self,
            package: Union[str, ModuleType],
    ) -> DecodingRules:
        if isinstance(package, str):
            package = importlib.import_module(package)

        results = DecodingRules(
            address_mappings={},
            event_rules=[],
            token_enricher_rules=[],
            post_decoding_rules=[],
            all_counterparties=set(),
        )

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

                    results.address_mappings.update(self.decoders[class_name].addresses_to_decoders())  # noqa: E501
                    results.event_rules.extend(self.decoders[class_name].decoding_rules())
                    results.token_enricher_rules.extend(self.decoders[class_name].enricher_rules())
                    results.post_decoding_rules.extend(self.decoders[class_name].post_decoding_rules())  # noqa: E501
                    results.all_counterparties.update(self.decoders[class_name].counterparties())

                recursive_results = self._recursively_initialize_decoders(full_name)
                results += recursive_results

        return results

    def reload_data(self, cursor: 'DBCursor') -> None:
        """Reload all related settings from DB and data that any decoder may require from the chain
        so that decoding happens with latest data"""
        self.base.refresh_tracked_accounts(cursor)
        for _, decoder in self.decoders.items():
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
            decoded_events: list[HistoryBaseEntry],
            action_items: list[ActionItem],
            all_logs: list[EvmTxReceiptLog],
    ) -> tuple[Optional[HistoryBaseEntry], list[ActionItem]]:
        for rule in self.rules.event_rules:
            event, new_action_items = rule(token=token, tx_log=tx_log, transaction=transaction, decoded_events=decoded_events, action_items=action_items, all_logs=all_logs)  # noqa: E501
            if event is not None or len(new_action_items) > 0:
                return event, new_action_items

        return None, []

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
        mapping_result = self.rules.address_mappings.get(tx_log.address)
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

    def run_all_post_decoding_rules(
            self,
            transaction: EvmTransaction,
            decoded_events: list[HistoryBaseEntry],
            all_logs: list[EvmTxReceiptLog],
    ) -> list[HistoryBaseEntry]:
        """
        Runs all post-decoding rules from self.rules.post_decoding_rules.
        The post-decoding rules list consists of tuples (priority, rule) and must be sorted by
        priority in ascending order. The higher the priority number the later the rule is run.
        """
        for (_, rule) in self.rules.post_decoding_rules:
            decoded_events = rule(transaction=transaction, decoded_events=decoded_events, all_logs=all_logs)  # noqa: E501

        return decoded_events

    def decode_transaction(
            self,
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
            event, new_action_items = self.try_all_rules(
                token=token,
                tx_log=tx_log,
                transaction=transaction,
                decoded_events=events,
                action_items=action_items,
                all_logs=tx_receipt.logs,
            )
            action_items.extend(new_action_items)
            if event is not None:
                events.append(event)

        events = self.run_all_post_decoding_rules(
            transaction=transaction,
            decoded_events=events,
            all_logs=tx_receipt.logs,
        )

        if len(events) == 0 and (eth_event := self._get_eth_transfer_event(transaction)) is not None:  # noqa: E501
            events = [eth_event]

        with self.database.user_write() as write_cursor:
            self.dbevents.add_history_events(
                write_cursor=write_cursor,
                history=events,
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
            self.reload_data(cursor)
            # If no transaction hashes are passed, decode all transactions.
            if tx_hashes is None:
                tx_hashes = []
                cursor.execute(
                    'SELECT tx_hash FROM evm_transactions WHERE chain_id=?',
                    (self.evm_inquirer.chain_id.serialize_for_db(),),
                )
                for entry in cursor:
                    tx_hashes.append(EVMTxHash(entry[0]))

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
            events.extend(self.get_or_decode_transaction_events(
                transaction=txs[0],
                tx_receipt=receipt,
                ignore_cache=ignore_cache,
            ))

        return events

    def get_or_decode_transaction_events(
            self,
            transaction: EvmTransaction,
            tx_receipt: EvmTxReceipt,
            ignore_cache: bool,
    ) -> list[HistoryBaseEntry]:
        """Get a transaction's events if existing in the DB or decode them"""
        serialized_chain_id = self.evm_inquirer.chain_id.serialize_for_db()
        if ignore_cache is True:  # delete all decoded events
            with self.database.user_write() as write_cursor:
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
            with self.database.conn.read_ctx() as cursor:
                cursor.execute(
                    'SELECT COUNT(*) from evm_tx_mappings WHERE tx_hash=? AND chain_id=? AND value=?',  # noqa: E501
                    (transaction.tx_hash, serialized_chain_id, HISTORY_MAPPING_STATE_DECODED),
                )
                if cursor.fetchone()[0] != 0:  # already decoded and in the DB
                    events = self.dbevents.get_history_events(
                        cursor=cursor,
                        filter_query=HistoryEventFilterQuery.make(
                            event_identifiers=[transaction.tx_hash],
                        ),
                        has_premium=True,  # for this function we don't limit anything
                    )
                    return events

        # else we should decode now
        events = self.decode_transaction(transaction, tx_receipt)
        return events

    def _maybe_decode_internal_transactions(
            self,
            tx: EvmTransaction,
            tx_receipt: EvmTxReceipt,
            events: list[HistoryBaseEntry],
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
            preposition = 'to' if event_type in OUTGOING_EVENT_TYPES else 'from'
            events.append(self.base.make_event_next_index(
                tx_hash=tx.tx_hash,
                timestamp=tx.timestamp,
                event_type=event_type,
                event_subtype=HistoryEventSubType.NONE,
                asset=self.value_asset,
                balance=Balance(amount=amount),
                location_label=location_label,
                notes=f'{verb} {amount} {self.value_asset.symbol} {preposition} {counterparty}',
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
        preposition = 'to' if event_type in OUTGOING_EVENT_TYPES else 'from'
        return self.base.make_event_next_index(
            tx_hash=tx.tx_hash,
            timestamp=tx.timestamp,
            event_type=event_type,
            event_subtype=HistoryEventSubType.NONE,
            asset=self.value_asset,
            balance=Balance(amount=amount),
            location_label=location_label,
            notes=f'{verb} {amount} {self.value_asset.symbol} {preposition} {counterparty}',
            counterparty=counterparty,
        )

    def _maybe_decode_erc20_approve(
            self,
            token: Optional[EvmToken],
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list[HistoryBaseEntry],  # pylint: disable=unused-argument
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> tuple[Optional[HistoryBaseEntry], list[ActionItem]]:
        if tx_log.topics[0] != ERC20_APPROVE or token is None:
            return None, []

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
            return None, []

        if not any(self.base.is_tracked(x) for x in (owner_address, spender_address)):
            return None, []

        amount = token_normalized_value(token_amount=amount_raw, token=token)
        prefix = f'Revoke {token.symbol} approval' if amount == ZERO else f'Approve {amount} {token.symbol}'  # noqa: E501
        notes = f'{prefix} of {owner_address} for spending by {spender_address}'
        event = self.base.make_event_from_transaction(
            transaction=transaction,
            tx_log=tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=token,
            balance=Balance(amount=amount),
            location_label=owner_address,
            notes=notes,
            counterparty=spender_address,
        )
        return event, []

    def _maybe_decode_simple_transactions(
            self,
            tx: EvmTransaction,
            tx_receipt: EvmTxReceipt,
    ) -> list[HistoryBaseEntry]:
        """Decodes normal ETH transfers, internal transactions and gas cost payments"""
        events: list[HistoryBaseEntry] = []
        # check for gas spent
        direction_result = self.base.decode_direction(tx.from_address, tx.to_address)
        if direction_result is not None:
            event_type, location_label, _, _ = direction_result
            if event_type in OUTGOING_EVENT_TYPES:
                eth_burned_as_gas = from_wei(FVal(tx.gas_used * tx.gas_price))
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
                counterparty=None,  # TODO: Find out contract address
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
            decoded_events: list[HistoryBaseEntry],  # pylint: disable=unused-argument
            action_items: list[ActionItem],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> tuple[Optional[HistoryBaseEntry], list[ActionItem]]:
        if tx_log.topics[0] != ERC20_OR_ERC721_TRANSFER:
            return None, []

        if self._is_non_conformant_erc721(tx_log.address) or len(tx_log.topics) == 4:  # typical ERC721 has 3 indexed args  # noqa: E501
            token_kind = EvmTokenKind.ERC721
        elif len(tx_log.topics) == 3:  # typical ERC20 has 2 indexed args
            token_kind = EvmTokenKind.ERC20
        else:
            log.debug(f'Failed to decode token with address {tx_log.address} due to inability to match token type')  # noqa: E501
            return None, []

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
                return None, []  # ignore non-ERC20 transfers for now
        else:
            found_token = token

        transfer = self.base.decode_erc20_721_transfer(
            token=found_token,
            tx_log=tx_log,
            transaction=transaction,
        )
        if transfer is None:
            return None, []

        for idx, action_item in enumerate(action_items):
            if action_item.asset == found_token and action_item.amount == transfer.balance.amount and action_item.from_event_type == transfer.event_type and action_item.from_event_subtype == transfer.event_subtype:  # noqa: E501
                if action_item.action == 'skip':
                    action_items.pop(idx)
                    return None, []
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
                        out_event=out_event,
                        in_event=in_event,
                        events_list=decoded_events + [transfer],
                    )

                action_items.pop(idx)
                break  # found an action item and acted on it

        # Add additional information to transfers for different protocols
        self._enrich_protocol_tranfers(
            token=found_token,
            tx_log=tx_log,
            transaction=transaction,
            event=transfer,
            action_items=action_items,
            all_logs=all_logs,
        )
        return transfer, []

    # -- methods to be implemented by child classes --

    @abstractmethod
    def _enrich_protocol_tranfers(  # pylint: disable=no-self-use
            self,
            token: EvmToken,
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            event: HistoryBaseEntry,
            action_items: list[ActionItem],
            all_logs: list[EvmTxReceiptLog],
    ) -> None:
        """
        Decode special transfers made by contract execution for example at the moment
        of depositing assets or withdrawing.
        It assumes that the event being decoded has been already filtered and is a
        transfer.
        """
        ...

    @staticmethod
    @abstractmethod
    def _is_non_conformant_erc721(address: ChecksumEvmAddress) -> bool:
        """Determine whether the address is a non-conformant erc721 for the chain"""
        ...

    @staticmethod
    @abstractmethod
    def _address_is_exchange(address: ChecksumEvmAddress) -> Optional[str]:
        """Takes an address and returns if it's an exchange in the given chain
        and the counterparty to use if it is."""
        ...
