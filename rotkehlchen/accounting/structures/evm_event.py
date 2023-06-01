import json
import logging
from collections.abc import Iterator
from enum import auto
from typing import TYPE_CHECKING, Any, Final, Literal, Optional, cast

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
from rotkehlchen.types import (
    ChecksumEvmAddress,
    EVMTxHash,
    Location,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.mixins.enums import SerializableEnumNameMixin

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


class EvmProduct(SerializableEnumNameMixin):
    """The type of EVM product we interact with"""
    POOL = auto()
    STAKING = auto()
    GAUGE = auto()


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
            tx_hash: EVMTxHash,
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
            event_identifier: Optional[str] = None,
    ) -> None:
        if event_identifier is None:
            calculated_event_identifier = f'{location.to_chain_id()}{tx_hash.hex()}'
        else:
            calculated_event_identifier = event_identifier
        HistoryBaseEntry.__init__(  # explicitly calling constructor due to some events having
            self=self,  # diamond shaped inheritance. Which calls unexpected super()
            event_identifier=calculated_event_identifier,
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
        self.tx_hash = tx_hash
        self.counterparty = counterparty
        self.product = product
        self.extra_data = extra_data

    @property
    def entry_type(self) -> HistoryBaseEntryType:
        return HistoryBaseEntryType.EVM_EVENT

    def _serialize_evm_event_tuple_for_db(
            self,
            entry_type: Literal[HistoryBaseEntryType.EVM_EVENT, HistoryBaseEntryType.ETH_DEPOSIT_EVENT],  # noqa: E501
    ) -> tuple[HISTORY_EVENT_DB_TUPLE_WRITE, EVM_EVENT_FIELDS]:
        base_tuple = self._serialize_base_tuple_for_db(entry_type)
        extra_data = json.dumps(self.extra_data) if self.extra_data else None
        return (
            base_tuple,
            (
                self.tx_hash,
                self.counterparty,
                self.product.serialize() if self.product is not None else None,
                self.address,
                extra_data,
            ),
        )

    def serialize_for_db(self) -> tuple[HISTORY_EVENT_DB_TUPLE_WRITE, EVM_EVENT_FIELDS]:
        return self._serialize_evm_event_tuple_for_db(HistoryBaseEntryType.EVM_EVENT)

    def serialize(self) -> dict[str, Any]:
        return super().serialize() | {
            'tx_hash': self.tx_hash.hex(),
            'counterparty': self.counterparty,
            'product': self.product.serialize() if self.product is not None else None,
            'address': self.address,
        }

    def serialize_for_api(
            self,
            customized_event_ids: list[int],
            ignored_ids_mapping: dict[ActionType, set[str]],
            hidden_event_ids: list[int],
            grouped_events_num: Optional[int] = None,
    ) -> dict[str, Any]:
        result = super().serialize_for_api(
            customized_event_ids=customized_event_ids,
            ignored_ids_mapping=ignored_ids_mapping,
            hidden_event_ids=hidden_event_ids,
            grouped_events_num=grouped_events_num,
        )
        if self.has_details():
            result['has_details'] = True
        return result

    @classmethod
    def deserialize_from_db(cls: type['EvmEvent'], entry: tuple) -> 'EvmEvent':
        entry = cast(EVM_EVENT_DB_TUPLE_READ, entry)
        extra_data = None
        if entry[16] is not None:
            try:
                extra_data = json.loads(entry[16])
            except json.JSONDecodeError as e:
                log.debug(
                    f'Failed to read extra_data when reading EvmEvent entry '
                    f'{entry} from the DB due to {e!s}. Setting it to null',
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
            tx_hash=deserialize_evm_tx_hash(entry[12]),
            counterparty=entry[13],
            product=EvmProduct.deserialize(entry[14]) if entry[14] is not None else None,
            address=deserialize_optional(input_val=entry[15], fn=string_to_evm_address),
            extra_data=extra_data,
        )

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
        try:
            return cls(
                **base_data,
                tx_hash=deserialize_evm_tx_hash(data['tx_hash']),
                address=deserialize_optional(data['address'], string_to_evm_address),
                counterparty=deserialize_optional(data['counterparty'], str),
                product=deserialize_optional(data['product'], EvmProduct.deserialize),
            )
        except KeyError as e:
            raise DeserializationError(f'Did not find key {e!s} in Evm Event data') from e

    def get_type_identifier(self, include_counterparty: bool = True, **kwargs: Any) -> str:
        """
        Computes the identifier from event type, event subtype and counterparty if
        `include_counterparty` is True.
        """
        type_identifier = super().get_type_identifier()
        if include_counterparty is True and self.counterparty is not None:
            type_identifier += '__' + self.counterparty

        return type_identifier

    def __eq__(self, other: Any) -> bool:
        return (
            HistoryBaseEntry.__eq__(self, other) is True and
            self.counterparty == other.counterparty and
            self.tx_hash == other.tx_hash and
            self.product == other.product and
            self.address == other.address and
            self.extra_data == other.extra_data
        )

    def __repr__(self) -> str:
        fields = self._history_base_entry_repr_fields() + [
            f'{self.tx_hash=}',
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
        ignored_ids = ignored_ids_mapping.get(ActionType.EVM_TRANSACTION, set())
        return self.event_identifier in ignored_ids

    def process(
            self,
            accounting: 'AccountingPot',
            events_iterator: Iterator['AccountingEventMixin'],  # pylint: disable=unused-argument
    ) -> int:
        return accounting.history_base_entries.process(self, events_iterator)
