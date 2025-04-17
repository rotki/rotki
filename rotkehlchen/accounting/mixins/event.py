from abc import ABC, abstractmethod
from enum import auto
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import Asset
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.mixins.enums import SerializableEnumNameMixin

if TYPE_CHECKING:
    from more_itertools import peekable

    from rotkehlchen.accounting.pot import AccountingPot


class AccountingEventType(SerializableEnumNameMixin):
    TRADE = auto()
    FEE = auto()
    ASSET_MOVEMENT = auto()
    MARGIN_POSITION = auto()
    LOAN = auto()
    PREFORK_ACQUISITION = auto()
    STAKING = auto()
    HISTORY_EVENT = auto()
    TRANSACTION_EVENT = auto()


class AccountingEventMixin(ABC):
    """Interface to be followed by all data structures that go in accounting"""

    @abstractmethod
    def get_timestamp(self) -> Timestamp:
        """Get the event's timestamp"""

    @staticmethod
    @abstractmethod
    def get_accounting_event_type() -> AccountingEventType:
        """
        Returns the event type for accounting
        """

    @abstractmethod
    def get_identifier(self) -> str:
        """Get a unique identifier from an accounting event"""

    @abstractmethod
    def should_ignore(self, ignored_ids: set[str]) -> bool:
        """Returns whether this event should be ignored due to user settings"""

    @abstractmethod
    def get_assets(self) -> list[Asset]:
        """Gets the assets involved in the event.

        May raise:
        - UnknownAsset, UnsupportedAsset due to the trade pair's assets
        - UnprocessableTradePair: If a trade's pair can't be processed
        """

    @abstractmethod
    def process(
            self,
            accounting: 'AccountingPot',
            events_iterator: "peekable['AccountingEventMixin']",
    ) -> int:
        """Processes the event for accounting and adds to the respective pot's processed events.

        Can also accept the iterator of the processed events of the accounting pot if there is
        a need to pull multiple events from the iterator (e.g. for defi swaps)

        Returns the number of events consumed.
        """

    @abstractmethod
    def serialize(self) -> dict[str, Any]:
        """Serializes the event"""

    def serialize_for_debug_import(self) -> dict[str, Any]:
        data = self.serialize()
        data['accounting_event_type'] = self.get_accounting_event_type().serialize()
        return data

    @classmethod
    @abstractmethod
    def deserialize(cls, data: dict[str, Any]) -> 'AccountingEventMixin':
        """Deserializes the event"""
