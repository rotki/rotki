import logging
from abc import ABCMeta, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from enum import auto
from typing import TYPE_CHECKING, Any, Optional, TypedDict, TypeVar

from rotkehlchen.accounting.mixins.event import AccountingEventMixin, AccountingEventType
from rotkehlchen.accounting.structures.types import (
    ActionType,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.chain.ethereum.constants import SHAPPELA_TIMESTAMP
from rotkehlchen.constants.assets import A_ETH2
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_optional,
    deserialize_timestamp,
)
from rotkehlchen.types import Location, Timestamp, TimestampMS
from rotkehlchen.utils.misc import timestamp_to_date, ts_ms_to_sec, ts_sec_to_ms
from rotkehlchen.utils.mixins.enums import DBIntEnumMixIn

from .balance import Balance

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


HISTORY_EVENT_DB_TUPLE_READ = tuple[
    int,            # identifier
    str,            # event_identifier
    int,            # sequence_index
    int,            # timestamp
    str,            # location
    Optional[str],  # location label
    str,            # asset
    str,            # amount
    str,            # usd value
    Optional[str],  # notes
    str,            # type
    str,            # subtype
]

HISTORY_EVENT_DB_TUPLE_WRITE = tuple[
    int,            # entry type
    str,            # event_identifier
    int,            # sequence_index
    int,            # timestamp
    str,            # location
    Optional[str],  # location label
    str,            # asset
    str,            # amount
    str,            # usd value
    Optional[str],  # notes
    str,            # type
    str,            # subtype
]


class HistoryBaseEntryType(DBIntEnumMixIn):
    """Type of a history entry. Value(int) is written/read into/from the DB

    Order matters here as the value is written in the DB, and the value is an int.
    """
    HISTORY_EVENT = auto()
    EVM_EVENT = auto()
    ETH_WITHDRAWAL_EVENT = auto()
    ETH_BLOCK_EVENT = auto()
    ETH_DEPOSIT_EVENT = auto()


class HistoryBaseEntryData(TypedDict):
    event_identifier: str
    sequence_index: int
    timestamp: TimestampMS
    location: Location
    event_type: HistoryEventType
    event_subtype: HistoryEventSubType
    asset: Asset
    balance: Balance
    location_label: Optional[str]
    notes: Optional[str]
    identifier: Optional[int]


T = TypeVar('T', bound='HistoryBaseEntry')


class HistoryBaseEntry(AccountingEventMixin, metaclass=ABCMeta):
    """
    Intended to be the base class for all types of event. All trades, deposits,
    swaps etc. are going to be made up of multiple such entries.
    """

    def __init__(
            self,
            event_identifier: str,
            sequence_index: int,
            timestamp: TimestampMS,
            location: Location,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            asset: Asset,
            balance: Balance,
            location_label: Optional[str] = None,
            notes: Optional[str] = None,
            identifier: Optional[int] = None,
    ) -> None:
        """
        - `event_identifier`: the identifier shared between related events
        - `sequence_index`: When this event is executed relative to other related events
        - `location_label`: a string field that allows to provide more information about
           the location. When we use this structure in blockchains, it is used to specify
           user address. For exchange events it's the exchange name assigned by the user
        """
        self.event_identifier = event_identifier
        self.sequence_index = sequence_index
        self.timestamp = timestamp
        self.location = location
        self.event_type = event_type
        self.event_subtype = event_subtype
        self.asset = asset
        self.balance = balance
        self.location_label = location_label
        self.notes = notes
        self.identifier = identifier

    def __eq__(self, other: Any) -> bool:
        if type(self) != type(other):  # pylint: disable=unidiomatic-typecheck
            return False

        return (
            self.event_identifier == other.event_identifier and
            self.sequence_index == other.sequence_index and
            self.timestamp == other.timestamp and
            self.location == other.location and
            self.event_type == other.event_type and
            self.event_subtype == other.event_subtype and
            self.asset == other.asset and
            self.balance == other.balance and
            self.location_label == other.location_label and
            self.notes == other.notes and
            self.identifier == other.identifier
        )

    def _history_base_entry_repr_fields(self) -> list[str]:
        """Returns a list of printable fields"""
        return [
            f'{self.event_identifier=}',
            f'{self.sequence_index=}',
            f'{self.timestamp=}',
            f'{self.location=}',
            f'{self.event_type=}',
            f'{self.event_subtype=}',
            f'{self.asset=}',
            f'{self.balance=}',
            f'{self.location_label=}',
            f'{self.notes=}',
            f'{self.identifier=}',
        ]

    def _serialize_base_tuple_for_db(self, entry_type: HistoryBaseEntryType) -> HISTORY_EVENT_DB_TUPLE_WRITE:  # noqa: E501
        return (
            entry_type.value,
            self.event_identifier,
            self.sequence_index,
            int(self.timestamp),
            self.location.serialize_for_db(),
            self.location_label,
            self.asset.identifier,
            str(self.balance.amount),
            str(self.balance.usd_value),
            self.notes,
            self.event_type.serialize(),
            self.event_subtype.serialize(),
        )

    @abstractmethod
    def serialize_for_db(self) -> tuple:
        """Serialize the event for writing to DB.
        May contain multiple tuples, one for each DB table"""

    @classmethod
    @abstractmethod
    def deserialize_from_db(cls: type[T], entry: tuple) -> T:
        """
        Deserialize a DB tuple to a proper class object.

        May raise:
        - DeserializationError
        - UnknownAsset
        """

    @property
    @abstractmethod
    def entry_type(self) -> HistoryBaseEntryType:
        """The event category for this event"""

    def get_type_identifier(self, **kwargs: Any) -> str:  # pylint: disable=unused-argument
        """Get the type identifier for this event. Subclasses may accept additional arguments"""
        return str(self.event_type) + '__' + str(self.event_subtype)

    def serialize(self) -> dict[str, Any]:
        """Serialize the event alone for api"""
        return {
            'identifier': self.identifier,
            'entry_type': self.entry_type.serialize(),
            'event_identifier': self.event_identifier,
            'sequence_index': self.sequence_index,
            'timestamp': ts_ms_to_sec(self.timestamp),  # serialize to api in seconds MS
            'location': str(self.location),
            'asset': self.asset.identifier,
            'balance': self.balance.serialize(),
            'event_type': self.event_type.serialize(),
            'event_subtype': self.event_subtype.serialize_or_none(),
            'location_label': self.location_label,
            'notes': self.notes,
        }

    def serialize_for_api(
            self,
            customized_event_ids: list[int],
            ignored_ids_mapping: dict[ActionType, set[str]],
            hidden_event_ids: list[int],
            grouped_events_num: Optional[int] = None,
    ) -> dict[str, Any]:
        """Serialize event and extra flags for api"""
        result: dict[str, Any] = {'entry': self.serialize()}
        if self.should_ignore(ignored_ids_mapping=ignored_ids_mapping):
            result['ignored_in_accounting'] = True
        if self.identifier in customized_event_ids:
            result['customized'] = True
        if self.identifier in hidden_event_ids:
            result['hidden'] = True
        if grouped_events_num is not None:
            result['grouped_events_num'] = grouped_events_num

        return result

    @classmethod
    def _deserialize_base_history_data(cls: type[T], data: dict[str, Any]) -> HistoryBaseEntryData:
        """Deserializes the base history event data to a typed dict

        May raise:
            - DeserializationError
            - UnknownAsset
        """
        try:
            return HistoryBaseEntryData(
                event_identifier=data['event_identifier'],
                sequence_index=data['sequence_index'],
                timestamp=ts_sec_to_ms(deserialize_timestamp(data['timestamp'])),
                location=Location.deserialize(data['location']),
                event_type=HistoryEventType.deserialize(data['event_type']),
                event_subtype=HistoryEventSubType.deserialize(data['event_subtype']) if data['event_subtype'] is not None else HistoryEventSubType.NONE,  # noqa: 501
                location_label=deserialize_optional(data['location_label'], str),
                notes=deserialize_optional(data['notes'], str),
                identifier=deserialize_optional(data['identifier'], int),
                asset=Asset(data['asset']).check_existence(),
                balance=Balance(
                    amount=deserialize_fval(
                        value=data['balance']['amount'],
                        name='balance amount',
                        location='history base entry',
                    ),
                    usd_value=deserialize_fval(
                        value=data['balance']['usd_value'],
                        name='balance usd value',
                        location='history base entry',
                    ),
                ),
            )
        except KeyError as e:
            raise DeserializationError(f'Did not find key {e!s} in event data') from e

    @classmethod
    @abstractmethod
    def deserialize(cls: type[T], data: dict[str, Any]) -> T:
        """Deserializes a dict history base entry to the specific event object.

        May raise:
            - DeserializationError
            - KeyError
            - UnknownAsset
        """

    def __str__(self) -> str:
        return (
            f'{self.event_subtype} event at {self.location} and time '
            f'{timestamp_to_date(ts_ms_to_sec(self.timestamp))} using {self.asset}'
        )

    def get_timestamp_in_sec(self) -> Timestamp:
        return ts_ms_to_sec(self.timestamp)

    # -- Methods of AccountingEventMixin

    def get_timestamp(self) -> Timestamp:
        return self.get_timestamp_in_sec()

    def get_identifier(self) -> str:
        assert self.identifier is not None, 'Should never be called without identifier'
        return str(self.identifier)

    def get_assets(self) -> list[Asset]:
        return [self.asset]

    def __hash__(self) -> int:
        if self.identifier is not None:
            return hash(self.identifier)

        return hash(str(self.event_identifier) + str(self.sequence_index))


class HistoryEvent(HistoryBaseEntry):
    """General history events such as exchange events"""

    def __init__(
            self,
            event_identifier: str,
            sequence_index: int,
            timestamp: TimestampMS,
            location: Location,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            asset: Asset,
            balance: Balance,
            location_label: Optional[str] = None,
            notes: Optional[str] = None,
            identifier: Optional[int] = None,
    ) -> None:
        super().__init__(
            event_identifier=event_identifier,
            sequence_index=sequence_index,
            timestamp=timestamp,
            location=location,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=asset,
            balance=balance,
            location_label=location_label,
            notes=notes,
            identifier=identifier,
        )

    @property
    def entry_type(self) -> HistoryBaseEntryType:
        return HistoryBaseEntryType.HISTORY_EVENT

    def __repr__(self) -> str:
        return f'HistoryEvent({", ".join(self._history_base_entry_repr_fields())})'

    def serialize_for_db(self) -> tuple[HISTORY_EVENT_DB_TUPLE_WRITE]:
        return (self._serialize_base_tuple_for_db(HistoryBaseEntryType.HISTORY_EVENT),)

    @classmethod
    def deserialize_from_db(
            cls: type['HistoryEvent'],
            entry: tuple,
    ) -> 'HistoryEvent':
        """
        May raise:
        - DeserializationError
        - UnknownAsset
        """
        amount = deserialize_fval(entry[7], 'amount', 'history event')
        usd_value = deserialize_fval(entry[8], 'usd_value', 'history event')
        return cls(
            identifier=entry[0],
            event_identifier=entry[1],
            sequence_index=entry[2],
            timestamp=TimestampMS(entry[3]),
            location=Location.deserialize_from_db(entry[4]),
            location_label=entry[5],
            asset=Asset(entry[6]).check_existence(),
            balance=Balance(amount, usd_value),
            notes=entry[9],
            event_type=HistoryEventType.deserialize(entry[10]),
            event_subtype=HistoryEventSubType.deserialize(entry[11]),
        )

    @classmethod
    def deserialize(cls: type['HistoryEvent'], data: dict[str, Any]) -> 'HistoryEvent':
        return cls(**cls._deserialize_base_history_data(data))

    # -- Methods of AccountingEventMixin

    @staticmethod
    def get_accounting_event_type() -> AccountingEventType:
        return AccountingEventType.HISTORY_EVENT

    def should_ignore(self, ignored_ids_mapping: dict[ActionType, set[str]]) -> bool:
        return False  # TODO: How do we ignore general history events? Not possible yet, I think

    def process(
            self,
            accounting: 'AccountingPot',
            events_iterator: Iterator['AccountingEventMixin'],  # pylint: disable=unused-argument
    ) -> int:
        if self.location == Location.KRAKEN:
            if (
                self.event_type != HistoryEventType.STAKING or
                self.event_subtype != HistoryEventSubType.REWARD
            ):
                return 1

            timestamp = self.get_timestamp_in_sec()
            # This omits every acquisition event of `ETH2` if `eth_staking_taxable_after_withdrawal_enabled`  # noqa: 501
            # setting is set to `True` until ETH2 withdrawals were enabled
            if self.asset == A_ETH2 and accounting.settings.eth_staking_taxable_after_withdrawal_enabled is True and timestamp < SHAPPELA_TIMESTAMP:  # noqa: 501
                return 1

            # otherwise it's kraken staking
            accounting.add_acquisition(
                event_type=AccountingEventType.STAKING,
                notes=f'Kraken {self.asset.resolve_to_asset_with_symbol().symbol} staking',
                location=self.location,
                timestamp=timestamp,
                asset=self.asset,
                amount=self.balance.amount,
                taxable=True,
            )
            return 1

        return accounting.events_accountant.process(event=self, events_iterator=events_iterator)


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class StakingEvent:
    event_type: HistoryEventSubType
    asset: AssetWithOracles
    balance: Balance
    timestamp: Timestamp
    location: Location

    @classmethod
    def from_history_base_entry(cls, event: HistoryBaseEntry) -> 'StakingEvent':
        """
        Read staking event from a history base entry.
        May raise:
        - DeserializationError
        """
        return StakingEvent(
            event_type=event.event_subtype,
            asset=event.asset.resolve_to_asset_with_oracles(),
            balance=event.balance,
            timestamp=ts_ms_to_sec(event.timestamp),
            location=event.location,
        )

    def serialize(self) -> dict[str, Any]:
        data = {
            'asset': self.asset.identifier,
            'timestamp': self.timestamp,
            'location': str(self.location),
        }
        # binance has only one type of event, so serializing it is not needed.
        if not (
            self.location == Location.BINANCE and
            self.event_type == HistoryEventSubType.INTEREST_PAYMENT
        ):
            data['event_type'] = self.event_type.serialize()

        balance = abs(self.balance).serialize()
        return {**data, **balance}
