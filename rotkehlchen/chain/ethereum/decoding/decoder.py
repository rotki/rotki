import importlib
import logging
import pkgutil
from types import ModuleType
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, Union

from rotkehlchen.accounting.structures import (
    Balance,
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.utils import get_or_create_ethereum_token
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem
from rotkehlchen.chain.ethereum.structures import EthereumTxReceipt, EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.utils import decode_event_data_abi_str, token_normalized_value
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_1INCH, A_ETH, A_GTC
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.db.filtering import ETHTransactionsFilterQuery, HistoryEventFilterQuery
from rotkehlchen.errors import (
    ConversionError,
    DecoderLoadingError,
    DeserializationError,
    UnknownAsset,
)
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import ChecksumEthAddress, EthereumTransaction, Location
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import (
    from_wei,
    hex_or_bytes_to_address,
    hex_or_bytes_to_int,
    timestamp_to_date,
)

from .base import BaseDecoderTools
from .constants import (
    ERC20_APPROVE,
    ERC20_OR_ERC721_TRANSFER,
    GOVERNORALPHA_PROPOSE,
    GOVERNORALPHA_PROPOSE_ABI,
    GTC_CLAIM,
    ONEINCH_CLAIM,
    XDAI_BRIDGE_RECEIVE,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


MODULES_PREFIX = 'rotkehlchen.chain.ethereum.decoding.'
MODULES_PREFIX_LENGTH = len(MODULES_PREFIX)


class EVMTransactionDecoder():

    def __init__(
            self,
            database: 'DBHandler',
            ethereum_manager: 'EthereumManager',
            msg_aggregator: MessagesAggregator,
    ):
        self.database = database
        self.ethereum_manager = ethereum_manager
        self.msg_aggregator = msg_aggregator
        self.dbethtx = DBEthTx(self.database)
        self.base = BaseDecoderTools(database=database)
        self.event_rules = [  # rules to try for all tx receipt logs decoding
            self._maybe_decode_erc20_approve,
            self._maybe_decode_erc20_721_transfer,
            self._maybe_enrich_transfers,
            self._maybe_decode_governance,
        ]
        self.initialize_all_decoders()

    def _recursively_initialize_decoders(
            self, package: Union[str, ModuleType],
    ) -> Tuple[
            Dict[ChecksumEthAddress, Tuple[Any, ...]],
            List[Callable],
    ]:
        if isinstance(package, str):
            package = importlib.import_module(package)
        address_results = {}
        rules_results = []
        for _, name, is_pkg in pkgutil.walk_packages(package.__path__):
            full_name = package.__name__ + '.' + name
            if full_name == __name__:
                continue  # skip -- this is this source file

            if is_pkg:
                submodule = importlib.import_module(full_name)
                class_name = full_name[MODULES_PREFIX_LENGTH:].translate({ord('.'): None})
                submodule_decoder = getattr(submodule, f'{class_name.capitalize()}Decoder', None)

                if submodule_decoder:
                    if class_name in self.decoders:
                        raise DecoderLoadingError(f'Decoder with name {class_name} already loaded')
                    self.decoders[class_name] = submodule_decoder(
                        ethereum_manager=self.ethereum_manager,
                        base_tools=self.base,
                        msg_aggregator=self.msg_aggregator,
                    )
                    address_results.update(self.decoders[class_name].addresses_to_decoders())
                    rules_results.extend(self.decoders[class_name].decoding_rules())

                recursive_addrs, recursive_rules = self._recursively_initialize_decoders(full_name)
                address_results.update(recursive_addrs)
                rules_results.extend(recursive_rules)

        return address_results, rules_results

    def initialize_all_decoders(self) -> None:
        """Recursively check all submodules of this module to get all decoder address
        mappings and rules
        """
        self.decoders: Dict[str, 'DecoderInterface'] = {}
        address_result, rules_result = self._recursively_initialize_decoders(__package__)
        self.address_mappings = address_result
        self.event_rules.extend(rules_result)

    def try_all_rules(
            self,
            token: Optional[EthereumToken],
            tx_log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,
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
            transaction: EthereumTransaction,
            decoded_events: List[HistoryBaseEntry],
            all_logs: List[EthereumTxReceiptLog],
            action_items: List[ActionItem],
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        """
        Sees if the log is on an address for which we have specific decoders and calls it

        Should catch all underlying errors these decoders will raise. So far known are:
        - DeserializationError
        - ConversionError
        - UnknownAsset
        """
        mapping_result = self.address_mappings.get(tx_log.address)
        if mapping_result is None:
            return None, None
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
            return None, None

        return result

    def decode_transaction(
            self,
            transaction: EthereumTransaction,
            tx_receipt: EthereumTxReceipt,
    ) -> List[HistoryBaseEntry]:
        """Decodes an ethereum transaction and its receipt and saves result in the DB"""
        cursor = self.database.conn.cursor()
        tx_hex = '0x' + transaction.tx_hash.hex()
        cursor.execute('DELETE FROM history_events WHERE event_identifier=?', (tx_hex,))
        cursor.execute(
            'DELETE FROM evm_tx_mappings WHERE tx_hash=? AND blockchain=? AND value=?',
            (transaction.tx_hash, 'ETH', 'decoded'),
        )
        # check if any eth transfer happened in the transaction, including in internal transactions
        events = self._maybe_decode_simple_transactions(transaction)
        action_items: List[ActionItem] = []

        # decode transaction logs from the receipt
        for tx_log in tx_receipt.logs:
            event, action_item = self.decode_by_address_rules(tx_log, transaction, events, tx_receipt.logs, action_items)  # noqa: E501
            if action_item:
                action_items.append(action_item)
            if event:
                events.append(event)
                continue

            token = GlobalDBHandler.get_ethereum_token(tx_log.address)
            event = self.try_all_rules(token=token, tx_log=tx_log, transaction=transaction, decoded_events=events, action_items=action_items)  # noqa: E501
            if event:
                events.append(event)

        self.database.add_history_events(events)
        cursor.execute(
            'INSERT INTO evm_tx_mappings(tx_hash, blockchain, value) VALUES(?, ?, ?)',
            (transaction.tx_hash, 'ETH', 'decoded'),
        )
        self.database.update_last_write()
        return sorted(events, key=lambda x: x.sequence_index, reverse=False)

    def decode_transaction_hashes(self, hashes: List[bytes]) -> None:
        """Runs the decoding logic for a number of transaction hashes

        Caller must make sure that:
        - The transaction hashes must exist in the DB for transactions
        - The transaction hashes must also have the corresponding receipts in the DB
        """
        # TODO: Change this if transaction filter query can accept multiple hashes
        for tx_hash in hashes:
            txs = self.dbethtx.get_ethereum_transactions(
                filter_=ETHTransactionsFilterQuery.make(tx_hash=tx_hash),
                has_premium=True,  # ignore limiting here
            )
            tx_receipt = self.dbethtx.get_receipt(tx_hash)
            assert tx_receipt, 'The transaction receipt for {tx_hash.hex()} should be in the DB'
            self.decode_transaction(transaction=txs[0], tx_receipt=tx_receipt)

    def get_or_decode_transaction_events(
            self,
            transaction: EthereumTransaction,
            tx_receipt: EthereumTxReceipt,
    ) -> List[HistoryBaseEntry]:
        """Get a transaction's events if existing in the DB or decode them"""
        tx_hex = '0x' + transaction.tx_hash.hex()
        cursor = self.database.conn.cursor()
        results = cursor.execute(
            'SELECT COUNT(*) from evm_tx_mappings WHERE tx_hash=? AND blockchain=? AND value=?',
            (transaction.tx_hash, 'ETH', 'decoded'),
        )
        if results.fetchone()[0] != 0:  # already decoded and in the DB
            events = self.database.get_history_events(
                filter_query=HistoryEventFilterQuery.make(
                    event_identifier=tx_hex,
                ),
                has_premium=True,  # for this function we don't limit anything
            )
            return events

        # else we should decode now
        events = self.decode_transaction(transaction, tx_receipt)
        return events

    def _maybe_decode_simple_transactions(
            self,
            tx: EthereumTransaction,
    ) -> List[HistoryBaseEntry]:
        events: List[HistoryBaseEntry] = []
        internal_txs = self.dbethtx.get_ethereum_internal_transactions(parent_tx_hash=tx.tx_hash)
        for internal_tx in internal_txs:
            if internal_tx.to_address is None:
                continue  # can that actually happen? An internal transaction deploying a contract?
            direction_result = self.base.decode_direction(internal_tx.from_address, internal_tx.to_address)  # noqa: E501
            if direction_result is None:
                continue

            amount = ZERO if internal_tx.value == 0 else from_wei(FVal(internal_tx.value))
            if amount == ZERO:
                continue

            event_type, location_label, counterparty, verb = direction_result
            events.append(HistoryBaseEntry(
                event_identifier='0x' + tx.tx_hash.hex(),
                sequence_index=internal_tx.trace_id,
                timestamp=internal_tx.timestamp,
                location=Location.BLOCKCHAIN,
                location_label=location_label,
                asset=A_ETH,
                balance=Balance(amount=amount),
                notes=f'{verb} {amount} ETH {internal_tx.from_address} -> {internal_tx.to_address}',  # noqa: E501
                event_type=event_type,
                event_subtype=HistoryEventSubType.NONE,
                counterparty=counterparty,
            ))

        # now decode the actual transaction eth transfer itself
        amount = ZERO if tx.value == 0 else from_wei(FVal(tx.value))
        if tx.to_address is None:
            if not self.base.is_tracked(tx.from_address):
                return events

            events.append(HistoryBaseEntry(  # contract deployment
                event_identifier='0x' + tx.tx_hash.hex(),
                sequence_index=0,
                timestamp=tx.timestamp,
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

        direction_result = self.base.decode_direction(tx.from_address, tx.to_address)
        if direction_result is None:
            return events

        event_type, location_label, counterparty, verb = direction_result
        events.append(HistoryBaseEntry(
            event_identifier='0x' + tx.tx_hash.hex(),
            sequence_index=0,
            timestamp=tx.timestamp,
            location=Location.BLOCKCHAIN,
            location_label=location_label,
            asset=A_ETH,
            balance=Balance(amount=amount),
            notes=f'{verb} {amount} ETH {tx.from_address} -> {tx.to_address}',
            event_type=event_type,
            event_subtype=HistoryEventSubType.NONE,
            counterparty=counterparty,
        ))
        return events

    def _maybe_decode_erc20_approve(
            self,
            token: Optional[EthereumToken],
            tx_log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> Optional[HistoryBaseEntry]:
        if tx_log.topics[0] != ERC20_APPROVE or token is None:
            return None

        owner_address = hex_or_bytes_to_address(tx_log.topics[1])
        spender_address = hex_or_bytes_to_address(tx_log.topics[2])

        if not any(self.base.is_tracked(x) for x in (owner_address, spender_address)):
            return None

        amount_raw = hex_or_bytes_to_int(tx_log.data)
        amount = token_normalized_value(token_amount=amount_raw, token=token)
        notes = f'Approve {amount} {token.symbol} of {owner_address} for spending by {spender_address}'  # noqa: E501
        return HistoryBaseEntry(
            event_identifier='0x' + transaction.tx_hash.hex(),
            sequence_index=tx_log.log_index,
            timestamp=transaction.timestamp,
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
            token: Optional[EthereumToken],
            tx_log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            action_items: List[ActionItem],
    ) -> Optional[HistoryBaseEntry]:
        if tx_log.topics[0] != ERC20_OR_ERC721_TRANSFER:
            return None

        if token is None:
            found_token = get_or_create_ethereum_token(
                userdb=self.database,
                ethereum_address=tx_log.address,
                ethereum_manager=self.ethereum_manager,
            )
        else:
            found_token = token

        set_verbs = None
        set_counterparty = None
        if transaction.to_address == '0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE':
            set_verbs = 'Donate', 'Receive donation'
            set_counterparty = 'gitcoin'
        transfer = self.base.decode_erc20_721_transfer(
            token=found_token,
            tx_log=tx_log,
            transaction=transaction,
            set_verbs=set_verbs,
            set_counterparty=set_counterparty,
        )
        if transfer is None:
            return None

        for action_item in action_items:
            if action_item.asset == found_token and action_item.amount == transfer.balance.amount and action_item.from_event_type == transfer.event_type and action_item.from_event_subtype == transfer.event_subtype:  # noqa: E501
                if action_item.action == 'skip':
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

                break  # found an action item and acted on it

        return transfer

    def _maybe_enrich_transfers(  # pylint: disable=no-self-use
            self,
            token: Optional[EthereumToken],  # pylint: disable=unused-argument
            tx_log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,  # pylint: disable=unused-argument
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

        if tx_log.topics[0] == XDAI_BRIDGE_RECEIVE and tx_log.address == '0x88ad09518695c6c3712AC10a214bE5109a655671':  # noqa: E501
            for event in decoded_events:
                if event.event_type == HistoryEventType.RECEIVE:
                    # user bridged from xdai
                    event.event_type = HistoryEventType.TRANSFER
                    event.event_subtype = HistoryEventSubType.BRIDGE
                    event.counterparty = 'XDAI'
                    event.notes = (
                        f'Bridge {event.balance.amount} {event.asset.symbol} from XDAI'
                    )

        return None

    def _maybe_decode_governance(  # pylint: disable=no-self-use
            self,
            token: Optional[EthereumToken],  # pylint: disable=unused-argument
            tx_log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,
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
                event_identifier='0x' + transaction.tx_hash.hex(),
                sequence_index=tx_log.log_index,
                timestamp=transaction.timestamp,
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
