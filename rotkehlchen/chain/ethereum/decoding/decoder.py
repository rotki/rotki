import importlib
import logging
import pkgutil
from types import ModuleType
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set, Tuple, Union

from gevent.lock import Semaphore

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.abi import decode_event_data_abi_str
from rotkehlchen.chain.ethereum.constants import MODULES_PACKAGE, MODULES_PREFIX_LENGTH
from rotkehlchen.chain.ethereum.decoding.constants import NAUGHTY_ERC721
from rotkehlchen.chain.ethereum.structures import EthereumTxReceipt, EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_1INCH, A_ETH, A_GTC
from rotkehlchen.db.constants import HISTORY_MAPPING_DECODED
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.db.filtering import ETHTransactionsFilterQuery, HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import InputError, ModuleLoadingError, NotERC20Conformant, RemoteError
from rotkehlchen.errors.serialization import ConversionError, DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EvmTokenKind,
    EvmTransaction,
    EVMTxHash,
    Location,
    TimestampMS,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import (
    from_wei,
    hex_or_bytes_to_address,
    hex_or_bytes_to_int,
    ts_sec_to_ms,
)
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin

from .base import BaseDecoderTools
from .constants import (
    CPT_GAS,
    CPT_GNOSIS_CHAIN,
    ERC20_APPROVE,
    ERC20_OR_ERC721_TRANSFER,
    GNOSIS_CHAIN_BRIDGE_RECEIVE,
    GOVERNORALPHA_PROPOSE,
    GOVERNORALPHA_PROPOSE_ABI,
    GTC_CLAIM,
    ONEINCH_CLAIM,
)
from .structures import ActionItem
from .utils import maybe_reshuffle_events

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.chain.ethereum.transactions import EthTransactions
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EVMTransactionDecoder():

    def __init__(
            self,
            database: 'DBHandler',
            ethereum_manager: 'EthereumManager',
            transactions: 'EthTransactions',
            msg_aggregator: MessagesAggregator,
    ):
        self.database = database
        self.all_counterparties: Set[str] = set()
        self.ethereum_manager = ethereum_manager
        self.transactions = transactions
        self.msg_aggregator = msg_aggregator
        self.dbethtx = DBEthTx(self.database)
        self.dbevents = DBHistoryEvents(self.database)
        self.base = BaseDecoderTools(database=database)
        self.event_rules = [  # rules to try for all tx receipt logs decoding
            self._maybe_decode_erc20_approve,
            self._maybe_decode_erc20_721_transfer,
            self._maybe_enrich_transfers,
            self._maybe_decode_governance,
        ]
        self.token_enricher_rules: List[Callable] = []  # enrichers to run for token transfers
        self.initialize_all_decoders()
        self.undecoded_tx_query_lock = Semaphore()

    def _recursively_initialize_decoders(
            self, package: Union[str, ModuleType],
    ) -> Tuple[
            Dict[ChecksumEvmAddress, Tuple[Any, ...]],
            List[Callable],
            List[Callable],
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
                class_name = full_name[MODULES_PREFIX_LENGTH:].translate({ord('.'): None})
                parts = class_name.split('_')
                class_name = ''.join([x.capitalize() for x in parts])
                submodule_decoder = getattr(submodule, f'{class_name}Decoder', None)

                if submodule_decoder:
                    if class_name in self.decoders:
                        raise ModuleLoadingError(f'Decoder with name {class_name} already loaded')
                    try:
                        self.decoders[class_name] = submodule_decoder(
                            ethereum_manager=self.ethereum_manager,
                            base_tools=self.base,
                            msg_aggregator=self.msg_aggregator,
                        )
                    except (UnknownAsset, WrongAssetType) as e:
                        self.msg_aggregator.add_error(f'Failed at initialization of {class_name} decoder due to asset mismatch: {str(e)}')  # noqa: E501
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
        self.decoders: Dict[str, 'DecoderInterface'] = {}
        address_result, rules_result, enrichers_result = self._recursively_initialize_decoders(MODULES_PACKAGE)  # noqa: E501
        self.address_mappings = address_result
        self.event_rules.extend(rules_result)
        self.token_enricher_rules.extend(enrichers_result)
        # update with counterparties not in any module
        self.all_counterparties.update([CPT_GAS, CPT_GNOSIS_CHAIN])

    def reload_from_db(self, cursor: 'DBCursor') -> None:
        """Reload all related settings from DB so that decoding happens with latest"""
        self.base.refresh_tracked_accounts(cursor)
        for _, decoder in self.decoders.items():
            if isinstance(decoder, CustomizableDateMixin):
                decoder.reload_settings(cursor)

    def try_all_rules(
            self,
            token: Optional[EvmToken],
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: List[HistoryBaseEntry],
            action_items: List[ActionItem],
    ) -> Optional[HistoryBaseEntry]:
        for rule in self.event_rules:
            event = rule(token=token, tx_log=tx_log, transaction=transaction, decoded_events=decoded_events, action_items=action_items)  # noqa: E501
            if event:
                return event

        return None

    def decode_by_address_rules(
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: List[HistoryBaseEntry],
            all_logs: List[EthereumTxReceiptLog],
            action_items: List[ActionItem],
    ) -> Tuple[Optional[HistoryBaseEntry], List[ActionItem]]:
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
            tx_receipt: EthereumTxReceipt,
    ) -> List[HistoryBaseEntry]:
        """Decodes an ethereum transaction and its receipt and saves result in the DB"""
        self.base.reset_sequence_counter()
        # check if any eth transfer happened in the transaction, including in internal transactions
        events = self._maybe_decode_simple_transactions(transaction, tx_receipt)
        action_items: List[ActionItem] = []

        # decode transaction logs from the receipt
        for tx_log in tx_receipt.logs:
            event, new_action_items = self.decode_by_address_rules(tx_log, transaction, events, tx_receipt.logs, action_items)  # noqa: E501
            action_items.extend(new_action_items)
            if event:
                events.append(event)
                continue

            token = GlobalDBHandler.get_evm_token(tx_log.address, chain=ChainID.ETHEREUM)
            event = self.try_all_rules(token=token, tx_log=tx_log, transaction=transaction, decoded_events=events, action_items=action_items)  # noqa: E501
            if event:
                events.append(event)

        self.dbevents.add_history_events(write_cursor=write_cursor, history=events)
        write_cursor.execute(
            'INSERT OR IGNORE INTO evm_tx_mappings(tx_hash, blockchain, value) VALUES(?, ?, ?)',  # noqa: E501
            (transaction.tx_hash, 'ETH', HISTORY_MAPPING_DECODED),
        )
        if events == [] and (eth_event := self._get_eth_transfer_event(transaction)) is not None:
            events = [eth_event]
        return sorted(events, key=lambda x: x.sequence_index, reverse=False)

    def get_and_decode_undecoded_transactions(self, limit: Optional[int] = None) -> None:
        """Checks the DB for up to `limit` undecoded transactions and decodes them.

        This is protected by concurrent access from a lock"""
        with self.undecoded_tx_query_lock:
            hashes = self.dbethtx.get_transaction_hashes_not_decoded(limit=limit)
            self.decode_transaction_hashes(ignore_cache=False, tx_hashes=hashes)

    def decode_transaction_hashes(self, ignore_cache: bool, tx_hashes: Optional[List[EVMTxHash]]) -> List[HistoryBaseEntry]:  # noqa: E501
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
                for entry in cursor.execute('SELECT tx_hash FROM ethereum_transactions'):
                    tx_hashes.append(EVMTxHash(entry[0]))

        with self.database.user_write() as cursor:
            for tx_hash in tx_hashes:
                try:
                    receipt = self.transactions.get_or_query_transaction_receipt(cursor, tx_hash)  # noqa: E501
                except RemoteError as e:
                    raise InputError(f'Hash {tx_hash.hex()} does not correspond to a transaction') from e  # noqa: E501

                # TODO: Change this if transaction filter query can accept multiple hashes
                txs = self.dbethtx.get_ethereum_transactions(
                    cursor=cursor,
                    filter_=ETHTransactionsFilterQuery.make(tx_hash=tx_hash),
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
            tx_receipt: EthereumTxReceipt,
            ignore_cache: bool,
    ) -> List[HistoryBaseEntry]:
        """Get a transaction's events if existing in the DB or decode them"""
        if ignore_cache is True:  # delete all decoded events
            self.dbevents.delete_events_by_tx_hash(write_cursor, [transaction.tx_hash])
            write_cursor.execute(
                'DELETE from evm_tx_mappings WHERE tx_hash=? AND blockchain=? AND value=?',
                (transaction.tx_hash, 'ETH', HISTORY_MAPPING_DECODED),
            )
        else:  # see if events are already decoded and return them
            write_cursor.execute(
                'SELECT COUNT(*) from evm_tx_mappings WHERE tx_hash=? AND blockchain=? AND value=?',  # noqa: E501
                (transaction.tx_hash, 'ETH', HISTORY_MAPPING_DECODED),
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
            tx_receipt: EthereumTxReceipt,
            events: List[HistoryBaseEntry],
            ts_ms: TimestampMS,
    ) -> None:
        """
        check for internal transactions if the transaction is not canceled. This function mutates
        the events argument.
        """
        if tx_receipt.status is False:
            return

        internal_txs = self.dbethtx.get_ethereum_internal_transactions(
            parent_tx_hash=tx.tx_hash,
        )
        for internal_tx in internal_txs:
            if internal_tx.to_address is None:
                continue  # can that happen? Internal transaction deploying a contract?
            direction_result = self.base.decode_direction(internal_tx.from_address, internal_tx.to_address)  # noqa: E501
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
                asset=A_ETH,
                balance=Balance(amount=amount),
                notes=f'{verb} {amount} ETH {preposition} {counterparty}',
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
            asset=A_ETH,
            balance=Balance(amount=amount),
            notes=f'{verb} {amount} ETH {preposition} {counterparty}',
            event_type=event_type,
            event_subtype=HistoryEventSubType.NONE,
            counterparty=counterparty,
        )

    def _maybe_decode_simple_transactions(
            self,
            tx: EvmTransaction,
            tx_receipt: EthereumTxReceipt,
    ) -> List[HistoryBaseEntry]:
        """Decodes normal ETH transfers, internal transactions and gas cost payments"""
        events: List[HistoryBaseEntry] = []
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
                    asset=A_ETH,
                    balance=Balance(amount=eth_burned_as_gas),
                    notes=f'Burned {eth_burned_as_gas} ETH for gas',
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
                asset=A_ETH,
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

    def _maybe_decode_erc20_approve(
            self,
            token: Optional[EvmToken],
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> Optional[HistoryBaseEntry]:
        if tx_log.topics[0] != ERC20_APPROVE or token is None:
            return None

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
            return None

        if not any(self.base.is_tracked(x) for x in (owner_address, spender_address)):
            return None

        amount = token_normalized_value(token_amount=amount_raw, token=token)
        prefix = f'Revoke {token.symbol} approval' if amount == ZERO else f'Approve {amount} {token.symbol}'  # noqa: E501
        notes = f'{prefix} of {owner_address} for spending by {spender_address}'
        return HistoryBaseEntry(
            event_identifier=transaction.tx_hash,
            sequence_index=self.base.get_sequence_index(tx_log),
            timestamp=ts_sec_to_ms(transaction.timestamp),
            location=Location.BLOCKCHAIN,
            location_label=owner_address,
            asset=token,
            balance=Balance(amount=amount),
            notes=notes,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            counterparty=spender_address,
        )

    def _maybe_decode_erc20_721_transfer(
            self,
            token: Optional[EvmToken],
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            action_items: List[ActionItem],
    ) -> Optional[HistoryBaseEntry]:
        if tx_log.topics[0] != ERC20_OR_ERC721_TRANSFER:
            return None

        if tx_log.address in NAUGHTY_ERC721 or len(tx_log.topics) == 4:  # typical ERC721 has 3 indexed args  # noqa: E501
            token_kind = EvmTokenKind.ERC721
        elif len(tx_log.topics) == 3:  # typical ERC20 has 2 indexed args
            token_kind = EvmTokenKind.ERC20
        else:
            log.debug(f'Failed to decode token with address {tx_log.address} due to inability to match token type')  # noqa: E501
            return None

        if token is None:
            try:
                found_token = get_or_create_evm_token(
                    userdb=self.database,
                    evm_address=tx_log.address,
                    chain=ChainID.ETHEREUM,
                    token_kind=token_kind,
                    ethereum_manager=self.ethereum_manager,
                )
            except NotERC20Conformant:
                return None  # ignore non-ERC20 transfers for now
        else:
            found_token = token

        transfer = self.base.decode_erc20_721_transfer(
            token=found_token,
            tx_log=tx_log,
            transaction=transaction,
        )
        if transfer is None:
            return None

        for idx, action_item in enumerate(action_items):
            if action_item.asset == found_token and action_item.amount == transfer.balance.amount and action_item.from_event_type == transfer.event_type and action_item.from_event_subtype == transfer.event_subtype:  # noqa: E501
                if action_item.action == 'skip':
                    action_items.pop(idx)
                    return None

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
        )
        return transfer

    def _maybe_enrich_transfers(
            self,
            token: Optional[EvmToken],  # pylint: disable=unused-argument
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> Optional[HistoryBaseEntry]:
        if tx_log.topics[0] == GTC_CLAIM and tx_log.address == '0xDE3e5a990bCE7fC60a6f017e7c4a95fc4939299E':  # noqa: E501
            for event in decoded_events:
                if event.asset == A_GTC and event.event_type == HistoryEventType.RECEIVE:
                    event.event_subtype = HistoryEventSubType.AIRDROP
                    event.notes = f'Claim {event.balance.amount} GTC from the GTC airdrop'
            return None

        if tx_log.topics[0] == ONEINCH_CLAIM and tx_log.address == '0xE295aD71242373C37C5FdA7B57F26f9eA1088AFe':  # noqa: E501
            for event in decoded_events:
                if event.asset == A_1INCH and event.event_type == HistoryEventType.RECEIVE:
                    event.event_subtype = HistoryEventSubType.AIRDROP
                    event.notes = f'Claim {event.balance.amount} 1INCH from the 1INCH airdrop'  # noqa: E501
            return None

        if tx_log.topics[0] == GNOSIS_CHAIN_BRIDGE_RECEIVE and tx_log.address == '0x88ad09518695c6c3712AC10a214bE5109a655671':  # noqa: E501
            for event in decoded_events:
                if event.event_type == HistoryEventType.RECEIVE:
                    try:
                        crypto_asset = event.asset.resolve_to_crypto_asset()
                    except (UnknownAsset, WrongAssetType):
                        next(iter(self.decoders.values())).notify_user(
                            event=event,
                            counterparty=CPT_GNOSIS_CHAIN,
                        )
                        continue

                    # user bridged from gnosis chain
                    event.event_type = HistoryEventType.TRANSFER
                    event.event_subtype = HistoryEventSubType.BRIDGE
                    event.counterparty = CPT_GNOSIS_CHAIN
                    event.notes = (
                        f'Bridge {event.balance.amount} {crypto_asset.symbol} from gnosis chain'
                    )

        return None

    def _enrich_protocol_tranfers(  # pylint: disable=no-self-use
            self,
            token: EvmToken,
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,
            event: HistoryBaseEntry,
            action_items: List[ActionItem],
    ) -> None:
        """
        Decode special transfers made by contract execution for example at the moment
        of depositing assets or withdrawing.
        It assumes that the event being decoded has been already filtered and is a
        transfer.
        """
        for enrich_call in self.token_enricher_rules:
            try:
                transfer_enriched = enrich_call(
                    token=token,
                    tx_log=tx_log,
                    transaction=transaction,
                    event=event,
                    action_items=action_items,
                )
            except (UnknownAsset, WrongAssetType) as e:
                log.error(
                    f'Failed to enrich transfer due to unknown asset {event.asset}. {str(e)}',
                )
                # Don't try other rules since all of them will fail to resolve the asset
                break

            if transfer_enriched:
                break

    def _maybe_decode_governance(  # pylint: disable=no-self-use
            self,
            token: Optional[EvmToken],  # pylint: disable=unused-argument
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> Optional[HistoryBaseEntry]:
        if tx_log.topics[0] == GOVERNORALPHA_PROPOSE:
            if tx_log.address == '0xDbD27635A534A3d3169Ef0498beB56Fb9c937489':
                governance_name = 'Gitcoin'
            else:
                governance_name = tx_log.address

            try:
                _, decoded_data = decode_event_data_abi_str(tx_log, GOVERNORALPHA_PROPOSE_ABI)
            except DeserializationError as e:
                log.debug(f'Failed to decode governor alpha event due to {str(e)}')
                return None

            proposal_id = decoded_data[0]
            proposal_text = decoded_data[8]
            notes = f'Create {governance_name} proposal {proposal_id}. {proposal_text}'
            return HistoryBaseEntry(
                event_identifier=transaction.tx_hash,
                sequence_index=self.base.get_sequence_index(tx_log),
                timestamp=ts_sec_to_ms(transaction.timestamp),
                location=Location.BLOCKCHAIN,
                location_label=transaction.from_address,
                # TODO: This should be null for proposals and other informational events
                asset=A_ETH,
                balance=Balance(),
                notes=notes,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.GOVERNANCE_PROPOSE,
                counterparty=governance_name,
            )

        return None
