import json
import logging
from dataclasses import dataclass
from enum import auto
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional, Tuple

from rotkehlchen.accounting.mixins.event import AccountingEventMixin, AccountingEventType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location, Timestamp, TimestampMS
from rotkehlchen.utils.misc import timestamp_to_date, ts_ms_to_sec
from rotkehlchen.utils.mixins.dbenum import DBEnumMixIn
from rotkehlchen.utils.mixins.serializableenum import SerializableEnumMixin

from .balance import Balance

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ActionType(DBEnumMixIn):
    TRADE = 1
    ASSET_MOVEMENT = 2
    ETHEREUM_TRANSACTION = 3
    LEDGER_ACTION = 4


class HistoryEventType(SerializableEnumMixin):
    TRADE = 0
    STAKING = auto()
    DEPOSIT = auto()
    WITHDRAWAL = auto()
    TRANSFER = auto()
    SPEND = auto()
    RECEIVE = auto()
    # forced adjustments of a system, like a CEX. For example having DAO in Kraken
    # and Kraken delisting them and exchanging them for ETH for you
    ADJUSTMENT = auto()
    UNKNOWN = auto()
    # An informational event. For kraken entries it means an unknown event
    INFORMATIONAL = auto()
    MIGRATE = auto()
    RENEW = auto()


class HistoryEventSubType(SerializableEnumMixin):
    REWARD = 0
    DEPOSIT_ASSET = auto()  # deposit asset in a contract, for staking etc.
    REMOVE_ASSET = auto()  # remove asset from a contract. from staking etc.
    FEE = auto()
    SPEND = auto()
    RECEIVE = auto()
    APPROVE = auto()
    DEPLOY = auto()
    AIRDROP = auto()
    BRIDGE = auto()
    GOVERNANCE_PROPOSE = auto()
    NONE = auto()  # Have a value for None to not get into NULL/None comparison hell
    GENERATE_DEBT = auto()
    PAYBACK_DEBT = auto()
    # receive a wrapped asset of something in any protocol. eg cDAI from DAI
    RECEIVE_WRAPPED = auto()
    # return a wrapped asset of something in any protocol. eg. CDAI to DAI
    RETURN_WRAPPED = auto()
    DONATE = auto()
    # subtype for ENS and other NFTs
    NFT = auto()
    # for DXDAO Mesa, Gnosis cowswap etc.
    PLACE_ORDER = auto()

    def serialize_or_none(self) -> Optional[str]:
        """Serializes the subtype but for the subtype None it returns None"""
        if self == HistoryEventSubType.NONE:
            return None

        return self.serialize()


HISTORY_EVENT_DB_TUPLE_READ = Tuple[
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
    Optional[str],  # counterparty
    Optional[str],  # extra_data
]

HISTORY_EVENT_DB_TUPLE_WRITE = Tuple[
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
    event_identifier: str  # identifier shared between related events
    sequence_index: int  # When this transaction was executed relative to other related events
    timestamp: TimestampMS
    location: Location
    event_type: HistoryEventType
    event_subtype: HistoryEventSubType
    asset: Asset
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
                asset=Asset(entry[6], form_with_incomplete_data=True),
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
                f'event identifier {entry[1]}. {str(e)}',
            ) from e

    def serialize(self) -> Dict[str, Any]:
        return {
            'identifier': self.identifier,
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
            'counterparty': self.counterparty,
        }

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
        if not self.event_identifier.startswith('0x'):
            return False

        ignored_ids = ignored_ids_mapping.get(ActionType.ETHEREUM_TRANSACTION, [])
        return self.event_identifier in ignored_ids

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
    asset: Asset
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
