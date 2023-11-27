import json
import logging
from enum import auto
from typing import TYPE_CHECKING, Any, Final, cast

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.types import ActionType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.base import (
    HISTORY_EVENT_DB_TUPLE_WRITE,
    HistoryBaseEntry,
    HistoryBaseEntryType,
    get_event_type_identifier,
)
from rotkehlchen.history.events.structures.types import (
    EVM_EVENT_DB_TUPLE_READ,
    EVM_EVENT_FIELDS,
    HistoryEventSubType,
    HistoryEventType,
)
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
    from more_itertools import peekable

    from rotkehlchen.accounting.mixins.event import AccountingEventMixin
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


class EvmEvent(HistoryBaseEntry):  # noqa: PLW1641  # hash in superclass
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
            location_label: str | None = None,
            notes: str | None = None,
            identifier: int | None = None,
            counterparty: str | None = None,
            product: EvmProduct | None = None,
            address: ChecksumEvmAddress | None = None,
            extra_data: dict[str, Any] | None = None,
            event_identifier: str | None = None,
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

    def _serialize_evm_event_tuple_for_db(self) -> tuple[
            tuple[str, str, HISTORY_EVENT_DB_TUPLE_WRITE],
            tuple[str, str, EVM_EVENT_FIELDS],
    ]:
        return (
            self._serialize_base_tuple_for_db(),
            (
                (
                    'evm_events_info(identifier, tx_hash, counterparty, product,'
                    'address, extra_data) VALUES (?, ?, ?, ?, ?, ?)'
                ), (
                    'UPDATE evm_events_info SET tx_hash=?, counterparty=?, product=?, address=?, extra_data=?'  # noqa: E501
                ), (
                    self.tx_hash,
                    self.counterparty,
                    self.product.serialize() if self.product is not None else None,
                    self.address,
                    json.dumps(self.extra_data) if self.extra_data else None,
                ),
            ),
        )

    def serialize_for_db(self) -> tuple[
            tuple[str, str, HISTORY_EVENT_DB_TUPLE_WRITE],
            tuple[str, str, EVM_EVENT_FIELDS],
    ]:
        return self._serialize_evm_event_tuple_for_db()

    def serialize(self) -> dict[str, Any]:
        return super().serialize() | {
            'tx_hash': self.tx_hash.hex(),
            'counterparty': self.counterparty,
            'product': self.product.serialize() if self.product is not None else None,
            'address': self.address,
            'extra_data': self.extra_data,
        }

    def serialize_for_api(
            self,
            customized_event_ids: list[int],
            ignored_ids_mapping: dict[ActionType, set[str]],
            hidden_event_ids: list[int],
            missing_accounting_rule: bool,
            grouped_events_num: int | None = None,
    ) -> dict[str, Any]:
        result = super().serialize_for_api(
            customized_event_ids=customized_event_ids,
            ignored_ids_mapping=ignored_ids_mapping,
            hidden_event_ids=hidden_event_ids,
            missing_accounting_rule=missing_accounting_rule,
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

    def get_details(self) -> dict[str, Any] | None:
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

    def __eq__(self, other: object) -> bool:
        return (  # ignores are due to object and type checks in super not recognized
            HistoryBaseEntry.__eq__(self, other) is True and
            self.counterparty == other.counterparty and  # type: ignore
            self.tx_hash == other.tx_hash and  # type: ignore
            self.product == other.product and  # type: ignore
            self.address == other.address and  # type: ignore
            self.extra_data == other.extra_data  # type: ignore
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

    def process(
            self,
            accounting: 'AccountingPot',
            events_iterator: "peekable['AccountingEventMixin']",  # pylint: disable=unused-argument
    ) -> int:
        return accounting.events_accountant.process(self, events_iterator)
