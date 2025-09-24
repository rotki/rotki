import logging
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SupportedBlockchain, Timestamp

from .utils import decode_transfer_direction

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

T = TypeVar('T')  # For transaction receipts/data
H = TypeVar('H')  # For transaction hashes
E = TypeVar('E')  # For events
A = TypeVar('A')  # For addresses
P = TypeVar('P')  # For product types (EvmProduct, etc.)


class BaseDecoderTools(ABC, Generic[T, A, H, E, P]):
    """Base class for chain-agnostic decoder tools providing common state and functionality"""

    def __init__(
            self,
            database: 'DBHandler',
            blockchain: SupportedBlockchain,
            address_is_exchange_fn: Callable[[A], str | None],
    ) -> None:
        """Initialize base decoder tools with database connection and blockchain type"""
        self.database = database
        self.blockchain = blockchain
        self.address_is_exchange = address_is_exchange_fn
        with self.database.conn.read_ctx() as cursor:
            self.tracked_accounts = self.database.get_blockchain_accounts(cursor)
        self.sequence_counter = 0
        self.sequence_offset = 0

    def reset_sequence_counter(self, tx_data: T) -> None:
        """Reset the sequence index counter before decoding a transaction.
        Chain-specific implementations handle how to calculate sequence_offset from tx_data.
        """
        self.sequence_counter = 0
        if __debug__:
            self.get_sequence_index_called = False

    def get_next_sequence_index_pre_decoding(self) -> int:
        """Get a sequence index for a new event created prior to running the decoding rules.
        Used for gas/fee events, native transfers, etc. Must never be used after sequence
        indexing with logs has started to prevent collisions.
        Returns the current counter and increments it.
        """
        if __debug__:  # develop only test that sequence index was not called
            assert not self.get_sequence_index_called  # Perhaps remove after some time.

        value = self.sequence_counter
        self.sequence_counter += 1
        return value

    def get_next_sequence_index(self) -> int:
        """Get a sequence index for a new event with no associated transaction log/instruction.
        Used during protocol decoding for informational or fee events.
        Returns the current counter added to the sequence offset.
        """
        if __debug__:
            self.get_sequence_index_called = True

        value = self.sequence_counter
        self.sequence_counter += 1
        return value + self.sequence_offset

    def refresh_tracked_accounts(self, cursor: 'DBCursor') -> None:
        """Refresh tracked accounts from the database"""
        self.tracked_accounts = self.database.get_blockchain_accounts(cursor)

    def is_tracked(self, address: A) -> bool:
        """Check if an address is tracked"""
        return address in self.tracked_accounts.get(self.blockchain)

    def any_tracked(self, addresses: Sequence[A]) -> bool:
        """Check if any of the addresses are tracked"""
        return set(addresses).isdisjoint(self.tracked_accounts.get(self.blockchain)) is False

    def decode_direction(
            self,
            from_address: A,
            to_address: A | None,
    ) -> tuple[HistoryEventType, HistoryEventSubType, str | None, A, str, str] | None:
        """Decode the direction of a transfer"""
        return decode_transfer_direction(  # type: ignore[type-var, return-value]
            from_address=from_address,
            to_address=to_address,
            tracked_accounts=self.tracked_accounts.get(self.blockchain),
            maybe_get_exchange_fn=self.address_is_exchange,  # type: ignore[arg-type]
        )

    @abstractmethod
    def make_event(
            self,
            tx_hash: H,
            sequence_index: int,
            timestamp: Timestamp,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            asset: 'Asset',
            amount: FVal,
            location_label: str | None = None,
            notes: str | None = None,
            counterparty: str | None = None,
            product: P | None = None,
            address: A | None = None,
            extra_data: dict[str, Any] | None = None,
    ) -> E:
        """Create an event of the appropriate type for this chain"""

    def make_event_next_index(
            self,
            tx_hash: H,
            timestamp: Timestamp,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            asset: 'Asset',
            amount: FVal,
            location_label: str | None = None,
            notes: str | None = None,
            counterparty: str | None = None,
            product: P | None = None,
            address: A | None = None,
            extra_data: dict[str, Any] | None = None,
    ) -> E:
        """Convenience function to use next sequence index"""
        return self.make_event(
            tx_hash=tx_hash,
            sequence_index=self.get_next_sequence_index(),
            timestamp=timestamp,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=asset,
            amount=amount,
            location_label=location_label,
            notes=notes,
            counterparty=counterparty,
            product=product,
            address=address,
            extra_data=extra_data,
        )
