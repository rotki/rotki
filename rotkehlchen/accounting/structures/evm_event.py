import json
import logging
import typing
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Final, Optional, cast

from rotkehlchen.accounting.mixins.event import AccountingEventMixin
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_optional
from rotkehlchen.types import ChecksumEvmAddress, Location, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


EVM_EVENT_FIELDS = tuple[
    Optional[str],  # counterparty
    Optional[str],  # product
    Optional[str],  # address
    Optional[str],  # extra_data
]

EVM_EVENT_FIELDS_NO_EXTRA_DATA = tuple[
    Optional[str],  # counterparty
    Optional[str],  # product
    Optional[str],  # address
]

EVM_EVENT_FIELDS_COUNT = len(typing.get_args(EVM_EVENT_FIELDS))


EVM_EVENT_DB_TUPLE_READ = tuple[
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
    str,            # address
    Optional[str],  # counterparty
    Optional[str],  # product
    Optional[str],  # extra_data
]


SUB_SWAPS_DETAILS: Final = 'sub_swaps'
LIQUITY_STAKING_DETAILS: Final = 'liquity_staking'

ALL_DETAILS_KEYS = {
    SUB_SWAPS_DETAILS,
    LIQUITY_STAKING_DETAILS,
}


def get_tx_event_type_identifier(event_type: HistoryEventType, event_subtype: HistoryEventSubType, counterparty: str) -> str:  # noqa: E501
    return str(event_type) + '__' + str(event_subtype) + '__' + counterparty


class EvmEvent(HistoryBaseEntry):
    """This is a class for storing evm events data and it extends HistoryBaseEntry.

    It adds the following fields:

    1. counterparty: Optional[str] -- Used to mark the protocol name, for example curve or liquity.

    2. product: Optional[str] -- For example if we are interacting with a pool, staking contract
    or others. This will help when filtering the events adding easier granularity to the searches.

    3. Optional[address]: ChecksumEvmAddress -- If we are working with evm information this would
    be the address of the contract. This would help to filter by older versions or limit searches
    to certain subsets of contracts. For example this would help filtering interactions with
    curve gauges.

    4. extra_data: Optional[dict[str, Any]] -- Contains event specific extra data. Optional, only
    for events that need to keep extra information such as the CDP ID of a makerdao vault etc.
    """

    def __init__(
            self,
            event_identifier: bytes,
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
            counterparty: Optional[str] = None,
            product: Optional[str] = None,
            address: Optional[ChecksumEvmAddress] = None,
            extra_data: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize EvmEvent.

        Using explicit init instead of a dataclass because dataclasses in python 3.9 don't support
        mandatory fields (address field in this case) after fields with default values
        (e.g. `location_label` in HistoryBaseEntry).
        """
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
        self.address = address
        self.counterparty = counterparty
        self.product = product
        self.extra_data = extra_data

    def serialize_evm_event_for_db_without_extra_data(self) -> EVM_EVENT_FIELDS_NO_EXTRA_DATA:
        """
        Serialize information for the database excluding the extra data field.
        This is used when writting information edited by the user
        """
        return (
            self.counterparty,
            self.product,
            self.address,
        )

    def serialize_evm_event_for_db(self) -> EVM_EVENT_FIELDS:
        extra_data = json.dumps(self.extra_data) if self.extra_data else None
        return self.serialize_evm_event_for_db_without_extra_data() + (extra_data,)

    def serialize(self) -> dict[str, Any]:
        return super().serialize() | {
            'counterparty': self.counterparty,
            'product': self.product,
            'address': self.address,
            'extra_data': self.extra_data,
        }

    def serialize_without_extra_data(self) -> dict[str, Any]:
        result = self.serialize()
        result.pop('extra_data')
        return result

    @classmethod
    def deserialize_evm_event_from_db(cls, entry: EVM_EVENT_DB_TUPLE_READ) -> 'EvmEvent':
        extra_data = None
        if entry[15] is not None:
            try:
                extra_data = json.loads(entry[15])
            except json.JSONDecodeError as e:
                log.debug(
                    f'Failed to read extra_data when reading EvmEvent entry '
                    f'{entry} from the DB due to {str(e)}. Setting it to null',
                )

        try:
            return cls(
                identifier=entry[0],
                event_identifier=entry[1],
                sequence_index=entry[2],
                timestamp=TimestampMS(entry[3]),
                location=Location.deserialize_from_db(entry[4]),
                location_label=entry[5],
                asset=Asset(entry[6]).check_existence(),
                balance=Balance(
                    amount=FVal(entry[7]),
                    usd_value=FVal(entry[8]),
                ),
                notes=entry[9],
                event_type=HistoryEventType.deserialize(entry[10]),
                event_subtype=HistoryEventSubType.deserialize(entry[11]),
                counterparty=entry[12],
                product=entry[13],
                address=deserialize_optional(input_val=entry[14], fn=string_to_evm_address),
                extra_data=extra_data,
            )
        except ValueError as e:
            raise DeserializationError(
                f'Failed to read FVal value from database history event with '
                f'event identifier {str(entry[1])}. {str(e)}',
            ) from e

    def has_details(self) -> bool:
        if self.extra_data is None:
            return False
        return len(self.extra_data.keys() & ALL_DETAILS_KEYS) > 0

    def get_details(self) -> Optional[dict[str, Any]]:
        if self.extra_data is None:
            return None

        details = {k: v for k, v in self.extra_data.items() if k in ALL_DETAILS_KEYS}
        return details if len(details) > 0 else None

    @classmethod
    def deserialize_evm_event(cls, data: dict[str, Any]) -> 'EvmEvent':
        instance = super().deserialize(data)
        # since we call super the type for the linter is HistoryBaseEntry, but in fact is EvmEvent
        instance = cast(EvmEvent, instance)
        instance.address = deserialize_optional(data['address'], string_to_evm_address)
        instance.counterparty = deserialize_optional(data['counterparty'], str)
        instance.product = deserialize_optional(data['product'], str)
        return instance

    def get_type_identifier(self) -> str:
        type_identifier = super().get_type_identifier()
        if self.counterparty is not None:
            type_identifier += '__' + self.counterparty

        return type_identifier

    def process(
            self,
            accounting: 'AccountingPot',
            events_iterator: Iterator['AccountingEventMixin'],
    ) -> int:
        return accounting.transactions.process(self, events_iterator)

    def __eq__(self, other: Any) -> bool:
        """Performs a comparison.

        If `other` is a history base entry but not an evm event then compares only fields of
        history base entry. Otherwise compates evm event fields too.
        """
        if isinstance(other, EvmEvent) is False:
            return False  # Can't comapre with a non-evm-event

        return (
            HistoryBaseEntry.__eq__(self, other) is True and
            (
                isinstance(other, EvmEvent) is False or
                all([
                    self.counterparty == other.counterparty,
                    self.product == other.product,
                    self.address == other.address,
                    self.extra_data == other.extra_data,
                ])
            )
        )

    def __repr__(self) -> str:
        fields = self._history_base_entry_repr_fields() + [
            f'{self.counterparty=}',
            f'{self.product=}',
            f'{self.address=}',
            f'{self.extra_data=}',
        ]
        return f'EvmEvent({",".join(fields)})'
