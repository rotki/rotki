import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional, Tuple

from rotkehlchen.accounting.mixins.event import AccountingEventMixin, AccountingEventType
from rotkehlchen.accounting.structures.types import (
    ActionType,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.assets.asset import Asset, AssetWithSymbol
from rotkehlchen.constants.assets import A_ETH2
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_optional,
    deserialize_timestamp,
)
from rotkehlchen.types import Location, Timestamp, TimestampMS
from rotkehlchen.utils.hexbytes import hexstring_to_bytes
from rotkehlchen.utils.misc import (
    is_valid_ethereum_tx_hash,
    timestamp_to_date,
    ts_ms_to_sec,
    ts_sec_to_ms,
)

from ...assets.utils import get_asset_by_identifier
from .balance import Balance

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


HISTORY_EVENT_DB_TUPLE_READ = Tuple[
    int,            # identifier
    bytes,          # event_identifier
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
    Optional[str],  # counterparty
    Optional[str],  # extra_data
]

HISTORY_EVENT_DB_TUPLE_WRITE = Tuple[
    bytes,          # event_identifier
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
    Optional[str],  # counterparty
    Optional[str],  # extra_data
]


def get_tx_event_type_identifier(event_type: HistoryEventType, event_subtype: HistoryEventSubType, counterparty: str) -> str:  # noqa: E501
    return str(event_type) + '__' + str(event_subtype) + '__' + counterparty


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class HistoryBaseEntry(AccountingEventMixin):
    """
    Intended to be the base unit of any type of accounting. All trades, deposits,
    swaps etc. are going to be made up of multiple HistoryBaseEntry
    """
    event_identifier: bytes  # identifier shared between related events
    sequence_index: int  # When this transaction was executed relative to other related events
    timestamp: TimestampMS
    location: Location
    event_type: HistoryEventType
    event_subtype: HistoryEventSubType
    asset: AssetWithSymbol
    balance: Balance
    # location_label is a string field that allows to provide more information about the location.
    # When we use this structure in blockchains can be used to specify addresses for example.
    # currently we use to identify the exchange name assigned by the user.
    location_label: Optional[str] = None
    notes: Optional[str] = None
    # identifier for counterparty.
    # For a send it's the target
    # For a receive it's the sender
    # For bridged transfer it's the bridge's network identifier
    # For a protocol interaction it's the protocol.
    counterparty: Optional[str] = None
    identifier: Optional[int] = None
    # contains event specific extra data. Optional, only for events that need to keep
    # extra information such as the CDP ID of a makerdao vault etc.
    extra_data: Optional[Dict[str, Any]] = None

    def serialize_for_db(self) -> HISTORY_EVENT_DB_TUPLE_WRITE:
        return (
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
            self.counterparty,
            json.dumps(self.extra_data) if self.extra_data else None,
        )

    @classmethod
    def deserialize_from_db(cls, entry: HISTORY_EVENT_DB_TUPLE_READ) -> 'HistoryBaseEntry':
        """May raise:
        - DeserializationError
        - UnknownAsset
        """
        extra_data = None
        if entry[13] is not None:
            try:
                extra_data = json.loads(entry[13])
            except json.JSONDecodeError as e:
                log.debug(
                    f'Failed to read extra_data when reading HistoryBaseEntry entry '
                    f'{entry} from the DB due to {str(e)}. Setting it to null',
                )

        try:
            return HistoryBaseEntry(
                identifier=entry[0],
                event_identifier=entry[1],
                sequence_index=entry[2],
                timestamp=TimestampMS(entry[3]),
                location=Location.deserialize_from_db(entry[4]),
                location_label=entry[5],
                # Setting incomplete data to true since we save all history events,
                # regardless of the type of token that it may involve
                asset=get_asset_by_identifier(entry[6], form_with_incomplete_data=True),
                balance=Balance(
                    amount=FVal(entry[7]),
                    usd_value=FVal(entry[8]),
                ),
                notes=entry[9],
                event_type=HistoryEventType.deserialize(entry[10]),
                event_subtype=HistoryEventSubType.deserialize(entry[11]),
                counterparty=entry[12],
                extra_data=extra_data,
            )
        except ValueError as e:
            raise DeserializationError(
                f'Failed to read FVal value from database history event with '
                f'event identifier {str(entry[1])}. {str(e)}',
            ) from e

    @property
    def serialized_event_identifier(self) -> str:
        """Take a HistoryBaseEntry's event_identifier and returns a string representation."""
        if self.location == Location.KRAKEN or self.event_identifier.startswith('rotki_events'.encode()):  # noqa: E501
            return self.event_identifier.decode()

        hex_representation = self.event_identifier.hex()
        if hex_representation.startswith('0x') is True:
            return hex_representation
        return '0x' + hex_representation

    @classmethod
    def deserialize_event_identifier(cls, val: str) -> bytes:
        """Takes any arbitrary string and turns it into a bytes event_identifier.

        May raise:
        - DeserializationError if value is not valid transaction hash.
        """
        if is_valid_ethereum_tx_hash(val):
            return hexstring_to_bytes(val)
        return val.encode()

    def serialize(self) -> Dict[str, Any]:
        return {
            'identifier': self.identifier,
            'event_identifier': self.serialized_event_identifier,
            'sequence_index': self.sequence_index,
            'timestamp': ts_ms_to_sec(self.timestamp),  # serialize to api in seconds MS
            'location': str(self.location),
            'asset': self.asset.identifier,
            'balance': self.balance.serialize(),
            'event_type': self.event_type.serialize(),
            'event_subtype': self.event_subtype.serialize_or_none(),
            'location_label': self.location_label,
            'notes': self.notes,
            'counterparty': self.counterparty,
        }

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'HistoryBaseEntry':
        """Deserializes a dict history base entry to HistoryBaseEntry object.
        May raise:
            - DeserializationError
            - KeyError
            - UnknownAsset
        """
        return cls(
            event_identifier=cls.deserialize_event_identifier(data['event_identifier']),
            sequence_index=data['sequence_index'],
            timestamp=ts_sec_to_ms(deserialize_timestamp(data['timestamp'])),
            location=Location.deserialize(data['location']),
            event_type=HistoryEventType.deserialize(data['event_type']),
            event_subtype=HistoryEventSubType.deserialize(data['event_subtype']) if data['event_subtype'] is not None else HistoryEventSubType.NONE,  # noqa: 501
            location_label=deserialize_optional(data['location_label'], str),
            notes=deserialize_optional(data['notes'], str),
            identifier=deserialize_optional(data['identifier'], int),
            counterparty=deserialize_optional(data['counterparty'], str),
            asset=get_asset_by_identifier(data['asset']),
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

    def __str__(self) -> str:
        return (
            f'{self.event_subtype} event at {self.location} and time '
            f'{timestamp_to_date(ts_ms_to_sec(self.timestamp))} using {self.asset}'
        )

    def get_timestamp_in_sec(self) -> Timestamp:
        return ts_ms_to_sec(self.timestamp)

    def get_type_identifier(self) -> str:
        """A unique type identifier for known event types"""
        identifier = str(self.event_type) + '__' + str(self.event_subtype)
        if self.counterparty and not self.counterparty.startswith('0x'):
            identifier += '__' + self.counterparty

        return identifier

    # -- Methods of AccountingEventMixin

    def get_timestamp(self) -> Timestamp:
        return self.get_timestamp_in_sec()

    @staticmethod
    def get_accounting_event_type() -> AccountingEventType:
        return AccountingEventType.HISTORY_BASE_ENTRY

    def should_ignore(self, ignored_ids_mapping: Dict[ActionType, List[str]]) -> bool:
        if not self.serialized_event_identifier.startswith('0x'):
            return False

        ignored_ids = ignored_ids_mapping.get(ActionType.ETHEREUM_TRANSACTION, [])
        return self.serialized_event_identifier in ignored_ids

    def get_identifier(self) -> str:
        assert self.identifier is not None, 'Should never be called without identifier'
        return str(self.identifier)

    def get_assets(self) -> List[Asset]:
        return [self.asset]

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

            # This omits every acquisition event of `ETH2` if `eth_staking_taxable_after_withdrawal_enabled`  # noqa: 501
            # setting is set to `True` until ETH2 is merged.
            if self.asset == A_ETH2  and accounting.settings.eth_staking_taxable_after_withdrawal_enabled is True:  # noqa: 501
                return 1

            # otherwise it's kraken staking
            accounting.add_acquisition(
                event_type=AccountingEventType.STAKING,
                notes=f'Kraken {self.asset.symbol} staking',
                location=self.location,
                timestamp=self.get_timestamp_in_sec(),
                asset=self.asset,
                amount=self.balance.amount,
                taxable=True,
            )
            return 1
        # else it's a decoded transaction event and should be processed there
        return accounting.transactions.process(self, events_iterator)


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class StakingEvent:
    event_type: HistoryEventSubType
    asset: AssetWithSymbol
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
            asset=event.asset,
            balance=event.balance,
            timestamp=ts_ms_to_sec(event.timestamp),
            location=event.location,
        )

    def serialize(self) -> Dict[str, Any]:
        data = {
            'event_type': self.event_type.serialize(),
            'asset': self.asset.identifier,
            'timestamp': self.timestamp,
            'location': str(self.location),
        }
        balance = abs(self.balance).serialize()
        return {**data, **balance}
