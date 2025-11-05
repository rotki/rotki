import logging
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Generic, Self, TypeVar, cast

from rotkehlchen.accounting.mixins.event import AccountingEventMixin, AccountingEventType
from rotkehlchen.accounting.types import EventAccountingRuleStatus
from rotkehlchen.assets.asset import Asset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.base import (
    HISTORY_EVENT_DB_TUPLE_WRITE,
    HistoryBaseEntry,
    get_event_type_identifier,
)
from rotkehlchen.history.events.structures.types import (
    CHAIN_EVENT_FIELDS_TYPE,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval, deserialize_optional
from rotkehlchen.types import FVal, Location, TimestampMS
from rotkehlchen.utils.misc import timestamp_to_date, ts_ms_to_sec

if TYPE_CHECKING:
    from more_itertools import peekable

    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.history.events.structures.types import CHAIN_EVENT_DB_TUPLE_READ


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Generic type variables for transaction reference and address types
T_TxRef = TypeVar('T_TxRef')
T_Address = TypeVar('T_Address')


class OnchainEvent(HistoryBaseEntry, Generic[T_TxRef, T_Address]):
    """Abstract base class for blockchain events with common functionality.

    This class provides shared behavior for events that occur on different blockchains,
    parameterized by transaction reference type and address type.

    Type Parameters:
        T_TxRef: The blockchain-specific transaction reference type
        T_Address: The blockchain-specific address type

    Additional fields beyond HistoryBaseEntry:
        - counterparty: optional protocol identifier (e.g., 'uniswap', 'curve')
        - tx_ref: blockchain-specific transaction reference
        - address: optional blockchain-specific address (e.g., contract address)
    """

    # need explicitly define due to also changing eq: https://stackoverflow.com/a/53519136/110395
    __hash__ = HistoryBaseEntry.__hash__

    def __init__(
            self,
            tx_ref: T_TxRef,
            sequence_index: int,
            timestamp: TimestampMS,
            location: Location,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            asset: Asset,
            amount: FVal,
            location_label: str | None = None,
            notes: str | None = None,
            identifier: int | None = None,
            counterparty: str | None = None,
            address: T_Address | None = None,
            extra_data: dict[str, Any] | None = None,
            group_identifier: str | None = None,
    ) -> None:
        if group_identifier is None:
            group_identifier = self._calculate_group_identifier(tx_ref, location)

        HistoryBaseEntry.__init__(  # explicitly calling constructor
            self=self,
            group_identifier=group_identifier,
            sequence_index=sequence_index,
            timestamp=timestamp,
            location=location,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=asset,
            amount=amount,
            location_label=location_label,
            notes=notes,
            identifier=identifier,
            extra_data=extra_data,
        )
        self.counterparty = counterparty
        self.address = address
        self.tx_ref = tx_ref

    def get_type_identifier(self, include_counterparty: bool = True, **kwargs: Any) -> int:
        """
        Computes the identifier from event type, event subtype and counterparty if
        `include_counterparty` is True.
        """
        return get_event_type_identifier(
            event_type=self.event_type,
            event_subtype=self.event_subtype,
            counterparty=self.counterparty if include_counterparty is True else None,
        )

    @staticmethod
    @abstractmethod
    def _calculate_group_identifier(tx_ref: T_TxRef, location: Location) -> str:
        """Calculate the group identifier from transaction reference and location.

        This method must be implemented by subclasses to handle chain-specific
        group identifier generation logic.
        """

    @staticmethod
    @abstractmethod
    def _serialize_tx_ref_for_db(tx_ref: T_TxRef) -> bytes:
        """Serialize transaction reference for database storage.

        This method must be implemented by subclasses to handle chain-specific
        transaction reference serialization.
        """

    @staticmethod
    @abstractmethod
    def _deserialize_tx_ref(tx_ref_data: bytes) -> T_TxRef:
        """Deserialize transaction reference from database.

        This method must be implemented by subclasses to handle chain-specific
        transaction reference deserialization.
        """

    @staticmethod
    @abstractmethod
    def deserialize_address(address_data: Any) -> T_Address:
        """Deserialize address from input data.

        This method must be implemented by subclasses to handle chain-specific
        address deserialization from various data sources.
        """

    def has_details(self) -> bool:
        """Check if this event has extra details available.

        Default implementation returns False. Subclasses can override
        to provide chain-specific detail detection logic.
        """
        return False

    def get_details(self) -> dict[str, Any] | None:
        """Get extra details for this event.

        Default implementation returns None. Subclasses can override
        to provide chain-specific detail extraction logic.
        """
        return None

    def _serialize_onchain_event_tuple_for_db(self) -> tuple[
            tuple[str, str, HISTORY_EVENT_DB_TUPLE_WRITE],
            tuple[str, str, CHAIN_EVENT_FIELDS_TYPE],
    ]:
        """Serialize onchain event data for database storage."""
        return (
            self._serialize_base_tuple_for_db(),
            (
                'chain_events_info(identifier, tx_ref, counterparty, address) VALUES (?, ?, ?, ?)',
                'UPDATE chain_events_info SET tx_ref=?, counterparty=?, address=?', (
                    self._serialize_tx_ref_for_db(self.tx_ref),
                    self.counterparty,
                    self.address,  # type: ignore  # T_Address is a string
                ),
            ),
        )

    def serialize_for_db(self) -> tuple[
            tuple[str, str, HISTORY_EVENT_DB_TUPLE_WRITE],
            tuple[str, str, CHAIN_EVENT_FIELDS_TYPE],
    ]:
        return self._serialize_onchain_event_tuple_for_db()

    def serialize(self) -> dict[str, Any]:
        return HistoryBaseEntry.serialize(self) | {  # not using super() since it has unexpected results due to diamond shaped inheritance.  # noqa: E501
            'tx_ref': str(self.tx_ref),
            'counterparty': self.counterparty,
            'address': str(self.address) if self.address is not None else None,
        }

    def serialize_for_api(
            self,
            customized_event_ids: list[int],
            ignored_ids: set[str],
            hidden_event_ids: list[int],
            event_accounting_rule_status: EventAccountingRuleStatus,
            grouped_events_num: int | None = None,
    ) -> dict[str, Any]:
        result = super().serialize_for_api(
            customized_event_ids=customized_event_ids,
            ignored_ids=ignored_ids,
            hidden_event_ids=hidden_event_ids,
            event_accounting_rule_status=event_accounting_rule_status,
            grouped_events_num=grouped_events_num,
        )
        if self.has_details():
            result['has_details'] = True

        return result

    @classmethod
    def deserialize_from_db(cls, entry: tuple) -> Self:
        entry = cast('CHAIN_EVENT_DB_TUPLE_READ', entry)
        amount = deserialize_fval(entry[7], 'amount', 'onchain event')
        return cls(
            identifier=entry[0],
            group_identifier=entry[1],
            sequence_index=entry[2],
            timestamp=TimestampMS(entry[3]),
            location=Location.deserialize_from_db(entry[4]),
            location_label=entry[5],
            asset=Asset(entry[6]).check_existence(),
            amount=amount,
            notes=entry[8],
            event_type=HistoryEventType.deserialize(entry[9]),
            event_subtype=HistoryEventSubType.deserialize(entry[10]),
            extra_data=cls.deserialize_extra_data(entry=entry, extra_data=entry[11]),
            tx_ref=cls._deserialize_tx_ref(entry[13]),
            counterparty=entry[14],
            address=deserialize_optional(input_val=entry[15], fn=cls.deserialize_address),
        )

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> Self:
        base_data = cls._deserialize_base_history_data(data)
        try:
            return cls(
                **base_data,
                tx_ref=cls._deserialize_tx_ref(data['tx_ref']),
                address=deserialize_optional(data['address'], cls.deserialize_address),
                counterparty=deserialize_optional(data['counterparty'], str),
            )
        except KeyError as e:
            raise DeserializationError(f'Did not find key {e!s} in {cls.__name__} data') from e

    def __eq__(self, other: object) -> bool:
        return (  # ignores are due to object and type checks in super not recognized
            HistoryBaseEntry.__eq__(self, other) is True and
            self.counterparty == other.counterparty and  # type: ignore
            self.tx_ref == other.tx_ref and  # type: ignore
            self.address == other.address  # type: ignore
        )

    def __repr__(self) -> str:
        fields = self._history_base_entry_repr_fields() + [
            f'self.tx_ref={self.tx_ref!s}',
            f'{self.counterparty=}',
            f'{self.address=}',
        ]
        return f'{self.__class__.__name__}({", ".join(fields)})'

    def __str__(self) -> str:
        return (
            f'{self.event_type} / {self.event_subtype} {self.__class__.__name__} '
            f'in {self.location} with tx_ref={self.tx_ref!s} and time '
            f'{timestamp_to_date(ts_ms_to_sec(self.timestamp))} using {self.asset}'
        )

    # -- Methods of AccountingEventMixin
    @staticmethod
    def get_accounting_event_type() -> AccountingEventType:
        return AccountingEventType.TRANSACTION_EVENT

    def process(
            self,
            accounting: 'AccountingPot',
            events_iterator: "peekable['AccountingEventMixin']",  # pylint: disable=unused-argument
    ) -> int:
        return accounting.events_accountant.process(self, events_iterator)
