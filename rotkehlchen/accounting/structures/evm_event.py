import json
import logging
from collections.abc import Iterator
from enum import auto
from typing import TYPE_CHECKING, Any, Final, Optional, cast

from rotkehlchen.accounting.mixins.event import AccountingEventMixin, AccountingEventType
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import (
    HISTORY_EVENT_DB_TUPLE_WRITE,
    HistoryBaseEntry,
    HistoryBaseEntryType,
)
from rotkehlchen.accounting.structures.types import (
    EVM_EVENT_DB_TUPLE_READ,
    EVM_EVENT_FIELDS,
    ActionType,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval, deserialize_optional
from rotkehlchen.types import ChecksumEvmAddress, Location, TimestampMS
from rotkehlchen.utils.hexbytes import hexstring_to_bytes
from rotkehlchen.utils.misc import is_valid_ethereum_tx_hash
from rotkehlchen.utils.mixins.serializableenum import SerializableEnumMixin

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


SUB_SWAPS_DETAILS: Final = 'sub_swaps'
LIQUITY_STAKING_DETAILS: Final = 'liquity_staking'

ALL_DETAILS_KEYS = {
    SUB_SWAPS_DETAILS,
    LIQUITY_STAKING_DETAILS,
}


class EvmProduct(SerializableEnumMixin):
    """The type of EVM product we interact with"""
    POOL = auto()
    STAKING = auto()
    CURVE_GAUGE = auto()
    CONVEX_GAUGE = auto()


def get_tx_event_type_identifier(event_type: HistoryEventType, event_subtype: HistoryEventSubType, counterparty: str) -> str:  # noqa: E501
    return str(event_type) + '__' + str(event_subtype) + '__' + counterparty


class EvmEvent(HistoryBaseEntry):
    """This is a class for storing evm events data and it extends HistoryBaseEntry.

    It adds the following fields:

    1. counterparty: Optional[str] -- Used to mark the protocol name, for example curve or liquity.

    2. product: Optional[EvmProduct] -- For example if we are interacting with a
    pool, staking contract
    or others. This will help when filtering the events adding easier granularity to the searches.

    3. Optional[address]: ChecksumEvmAddress -- If we are working with evm information this would
    be the address of the contract. This would help to filter by older versions or limit searches
    to certain subsets of contracts. For example this would help filtering interactions with
    curve gauges.

    4. extra_data: Optional[dict[str, Any]] -- Contains event specific extra data. Optional, only
    for events that need to keep extra information such as the CDP ID of a makerdao vault etc.
    """

    # need explicitly define due to also changing eq: https://stackoverflow.com/a/53519136/110395
    __hash__ = HistoryBaseEntry.__hash__

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
            product: Optional[EvmProduct] = None,
            address: Optional[ChecksumEvmAddress] = None,
            extra_data: Optional[dict[str, Any]] = None,
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
        self.address = address
        self.counterparty = counterparty
        self.product = product
        self.extra_data = extra_data

    def serialize_for_db(self) -> tuple[HISTORY_EVENT_DB_TUPLE_WRITE, EVM_EVENT_FIELDS]:
        base_tuple = self._serialize_base_tuple_for_db(HistoryBaseEntryType.EVM_EVENT)
        extra_data = json.dumps(self.extra_data) if self.extra_data else None
        return (
            base_tuple,
            (
                self.counterparty,
                self.product.serialize() if self.product is not None else None,
                self.address,
                extra_data,
            ),
        )

    def serialize(self) -> dict[str, Any]:
        return super().serialize() | {
            'counterparty': self.counterparty,
            'product': self.product.serialize() if self.product is not None else None,
            'address': self.address,
        }

    def serialize_for_api(
            self,
            customized_event_ids: list[int],
            grouped_events_num: Optional[int] = None,
    ) -> dict[str, Any]:
        result = super().serialize_for_api(customized_event_ids, grouped_events_num)
        result['has_details'] = self.has_details()
        return result

    @classmethod
    def deserialize_from_db(cls: type['EvmEvent'], entry: tuple) -> 'EvmEvent':
        entry = cast(EVM_EVENT_DB_TUPLE_READ, entry)
        extra_data = None
        if entry[15] is not None:
            try:
                extra_data = json.loads(entry[15])
            except json.JSONDecodeError as e:
                log.debug(
                    f'Failed to read extra_data when reading EvmEvent entry '
                    f'{entry} from the DB due to {str(e)}. Setting it to null',
                )

        amount = deserialize_fval(entry[7], 'amount', 'evm event')
        usd_value = deserialize_fval(entry[8], 'usd_value', 'evm event')
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
            counterparty=entry[12],
            product=EvmProduct.deserialize(entry[13]) if entry[13] is not None else None,
            address=deserialize_optional(input_val=entry[14], fn=string_to_evm_address),
            extra_data=extra_data,
        )

    @property
    def serialized_event_identifier(self) -> str:
        hex_representation = self.event_identifier.hex()
        if hex_representation.startswith('0x') is True:
            return hex_representation
        return '0x' + hex_representation

    @classmethod
    def deserialize_event_identifier(cls: type['EvmEvent'], val: str) -> bytes:
        if is_valid_ethereum_tx_hash(val) is False:
            raise DeserializationError(f'{val} was expected to be an evm tx hash string')

        return hexstring_to_bytes(val)

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
    def deserialize(cls: type['EvmEvent'], data: dict[str, Any]) -> 'EvmEvent':
        base_data = cls._deserialize_base_history_data(data)
        return cls(
            **base_data,
            address=deserialize_optional(data['address'], string_to_evm_address),
            counterparty=deserialize_optional(data['counterparty'], str),
            product=deserialize_optional(data['product'], EvmProduct.deserialize),
        )

    def get_type_identifier(self, include_counterparty: bool = True) -> str:
        """
        Computes the identifier from event type, event subtype and counterparty if
        `include_counterparty` is True.
        """
        type_identifier = str(self.event_type) + '__' + str(self.event_subtype)
        if include_counterparty is True and self.counterparty is not None:
            type_identifier += '__' + self.counterparty

        return type_identifier

    def __eq__(self, other: Any) -> bool:
        return (
            HistoryBaseEntry.__eq__(self, other) is True and
            self.counterparty == other.counterparty and
            self.product == other.product and
            self.address == other.address and
            self.extra_data == other.extra_data
        )

    def __repr__(self) -> str:
        fields = self._history_base_entry_repr_fields() + [
            f'{self.counterparty=}',
            f'{self.product=}',
            f'{self.address=}',
            f'{self.extra_data=}',
        ]
        return f'EvmEvent({", ".join(fields)})'

    # -- Methods of AccountingEventMixin

    @staticmethod
    def get_accounting_event_type() -> AccountingEventType:
        return AccountingEventType.TRANSACTION_EVENT

    def should_ignore(self, ignored_ids_mapping: dict[ActionType, set[str]]) -> bool:
        serialized_event_identifier = self.serialized_event_identifier
        ignored_ids = ignored_ids_mapping.get(ActionType.EVM_TRANSACTION, set())
        result = f'{self.location.to_chain_id()}{serialized_event_identifier}' in ignored_ids
        return result

    def process(
            self,
            accounting: 'AccountingPot',
            events_iterator: Iterator['AccountingEventMixin'],  # pylint: disable=unused-argument
    ) -> int:
        return accounting.transactions.process(self, events_iterator)
