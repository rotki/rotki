import logging
from typing import TYPE_CHECKING, Optional, Tuple

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.decoding.constants import NAUGHTY_ERC721
from rotkehlchen.constants import ONE
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import EvmTokenKind, EvmTransaction, Location
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int, ts_sec_to_ms

from .utils import address_is_exchange

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BaseDecoderTools():
    """A class that keeps a common state and offers some common decoding functionality"""

    def __init__(self, database: 'DBHandler') -> None:
        self.database = database
        with self.database.conn.read_ctx() as cursor:
            self.tracked_accounts = self.database.get_blockchain_accounts(cursor)
        self.sequence_counter = 0

    def reset_sequence_counter(self) -> None:
        self.sequence_counter = 0

    def get_next_sequence_counter(self) -> int:
        """Returns current counter and also increases it.
        Meant to be called for all transaction events that do not have a corresponding log index"""
        value = self.sequence_counter
        self.sequence_counter += 1
        return value

    def get_sequence_index(self, tx_log: EthereumTxReceiptLog) -> int:
        """Get the value that should go for this event's sequence index

        This function exists to calculate the index bases on the pre-calculated
        sequence index and the event's log index"""
        return self.sequence_counter + tx_log.log_index

    def refresh_tracked_accounts(self, cursor: 'DBCursor') -> None:
        self.tracked_accounts = self.database.get_blockchain_accounts(cursor)

    def is_tracked(self, adddress: ChecksumEvmAddress) -> bool:
        return adddress in self.tracked_accounts.eth

    def decode_direction(
            self,
            from_address: ChecksumEvmAddress,
            to_address: Optional[ChecksumEvmAddress],
    ) -> Optional[Tuple[HistoryEventType, Optional[str], str, str]]:
        """Depending on addresses, if they are tracked by the user or not, if they
        are an exchange address etc. determine the type of event to classify the transfer as"""
        tracked_from = from_address in self.tracked_accounts.eth
        tracked_to = to_address in self.tracked_accounts.eth
        if not tracked_from and not tracked_to:
            return None

        from_exchange = address_is_exchange(from_address)
        to_exchange = address_is_exchange(to_address) if to_address else None

        counterparty: Optional[str]
        if tracked_from and tracked_to:
            event_type = HistoryEventType.TRANSFER
            location_label = from_address
            counterparty = to_address
            verb = 'Send'
        elif tracked_from:
            if to_exchange is not None:
                event_type = HistoryEventType.DEPOSIT
                verb = 'Deposit'
                counterparty = to_exchange
            else:
                event_type = HistoryEventType.SPEND
                verb = 'Send'
                counterparty = to_address

            location_label = from_address
        else:  # can only be tracked_to
            if from_exchange:
                event_type = HistoryEventType.WITHDRAWAL
                verb = 'Withdraw'
                counterparty = from_exchange
            else:
                event_type = HistoryEventType.RECEIVE
                verb = 'Receive'
                counterparty = from_address

            location_label = to_address  # type: ignore  # to_address can't be None here

        return event_type, location_label, counterparty, verb  # type: ignore

    def decode_erc20_721_transfer(
            self,
            token: EvmToken,
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,
    ) -> Optional[HistoryBaseEntry]:
        """
        Caller should know this is a transfer of either an ERC20 or an ERC721 token.
        Call this method to decode it.

        May raise:
        - DeserializationError
        - ConversionError
        """
        from_address = hex_or_bytes_to_address(tx_log.topics[1])
        to_address = hex_or_bytes_to_address(tx_log.topics[2])
        direction_result = self.decode_direction(
            from_address=from_address,
            to_address=to_address,
        )
        if direction_result is None:
            return None

        extra_data = None
        event_type, location_label, counterparty, verb = direction_result
        amount_raw_or_token_id = hex_or_bytes_to_int(tx_log.data)
        if token.token_kind == EvmTokenKind.ERC20:
            amount = token_normalized_value(token_amount=amount_raw_or_token_id, token=token)
            if event_type == HistoryEventType.SPEND:
                notes = f'{verb} {amount} {token.symbol} from {location_label} to {counterparty}'
            else:
                notes = f'{verb} {amount} {token.symbol} from {counterparty} to {location_label}'
        elif token.token_kind == EvmTokenKind.ERC721:
            try:
                if token.evm_address in NAUGHTY_ERC721:  # id is in the data
                    token_id = hex_or_bytes_to_int(tx_log.data[0:32])
                else:
                    token_id = hex_or_bytes_to_int(tx_log.topics[3])
            except IndexError as e:
                log.debug(
                    f'At decoding of token {token.evm_address} as ERC721 got '
                    f'insufficient number of topics: {tx_log.topics} and error: {str(e)}',
                )
                return None

            amount = ONE
            name = 'ERC721 token' if token.name == '' else token.name
            extra_data = {'token_id': token_id, 'token_name': name}
            if event_type == HistoryEventType.SPEND:
                notes = f'{verb} {name} with id {token_id} from {location_label} to {counterparty}'  # noqa: E501
            else:
                notes = f'{verb} {name} with id {token_id} from {counterparty} to {location_label}'  # noqa: E501
        else:
            return None  # unknown kind

        return HistoryBaseEntry(
            event_identifier=transaction.tx_hash,
            sequence_index=self.get_sequence_index(tx_log),
            timestamp=ts_sec_to_ms(transaction.timestamp),
            location=Location.BLOCKCHAIN,
            location_label=location_label,
            asset=token,
            balance=Balance(amount=amount),
            notes=notes,
            event_type=event_type,
            event_subtype=HistoryEventSubType.NONE,
            counterparty=counterparty,
            extra_data=extra_data,
        )
