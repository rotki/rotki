import logging
from typing import TYPE_CHECKING, Any, cast

from solders.solders import Signature

from rotkehlchen.accounting.types import EventAccountingRuleStatus
from rotkehlchen.assets.asset import Asset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.base import (
    HISTORY_EVENT_DB_TUPLE_WRITE,
    HistoryBaseEntry,
    HistoryBaseEntryType,
    HistoryEventWithCounterparty,
)
from rotkehlchen.history.events.structures.types import (
    CHAIN_EVENT_FIELDS_TYPE,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval, deserialize_optional
from rotkehlchen.types import (
    FVal,
    Location,
    SolanaAddress,
    TimestampMS,
)
from rotkehlchen.utils.misc import timestamp_to_date, ts_ms_to_sec

if TYPE_CHECKING:
    from rotkehlchen.history.events.structures.types import SOLANA_EVENT_DB_TUPLE_READ


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SolanaEvent(HistoryEventWithCounterparty):  # hash in superclass
    """Represents a solana event, extending HistoryBaseEntry with solana specific metadata.

    Additional fields:
        - counterparty: optional protocol identifier (e.g., 'raydium', 'orca').
        - address: optional program address for filtering events by specific
          programs or protocol versions.
    """

    # need explicitly define due to also changing eq: https://stackoverflow.com/a/53519136/110395
    __hash__ = HistoryBaseEntry.__hash__

    def __init__(
            self,
            signature: Signature,
            sequence_index: int,
            timestamp: TimestampMS,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            asset: Asset,
            amount: FVal,
            location_label: str | None = None,
            notes: str | None = None,
            identifier: int | None = None,
            counterparty: str | None = None,
            address: SolanaAddress | None = None,
            extra_data: dict[str, Any] | None = None,
            event_identifier: str | None = None,
    ) -> None:
        self.location = Location.SOLANA
        HistoryEventWithCounterparty.__init__(  # explicitly calling constructor due to some events having  # noqa: E501
            self=self,  # diamond shaped inheritance. Which calls unexpected super()
            event_identifier=str(signature) if event_identifier is None else event_identifier,
            sequence_index=sequence_index,
            timestamp=timestamp,
            location=self.location,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=asset,
            amount=amount,
            location_label=location_label,
            notes=notes,
            identifier=identifier,
            extra_data=extra_data,
            counterparty=counterparty,
        )
        self.address = address
        self.signature = signature

    @property
    def entry_type(self) -> HistoryBaseEntryType:
        return HistoryBaseEntryType.SOLANA_EVENT

    def _serialize_solana_event_tuple_for_db(self) -> tuple[
            tuple[str, str, HISTORY_EVENT_DB_TUPLE_WRITE],
            tuple[str, str, CHAIN_EVENT_FIELDS_TYPE],
    ]:
        return (
            self._serialize_base_tuple_for_db(),
            (
                'chain_events_info(identifier, tx_ref, counterparty, address) VALUES (?, ?, ?, ?)',
                'UPDATE chain_events_info SET tx_ref=?, counterparty=?, address=?', (
                    self.signature.to_bytes(),
                    self.counterparty,
                    self.address,
                ),
            ),
        )

    def serialize_for_db(self) -> tuple[
            tuple[str, str, HISTORY_EVENT_DB_TUPLE_WRITE],
            tuple[str, str, CHAIN_EVENT_FIELDS_TYPE],
    ]:
        return self._serialize_solana_event_tuple_for_db()

    def serialize(self) -> dict[str, Any]:
        return HistoryBaseEntry.serialize(self) | {  # not using super() since it has unexpected results due to diamond shaped inheritance.  # noqa: E501
            'signature': str(self.signature),
            'counterparty': self.counterparty,
            'address': self.address,
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
        result['has_details'] = False
        return result

    @classmethod
    def deserialize_from_db(cls: type['SolanaEvent'], entry: tuple) -> 'SolanaEvent':
        entry = cast('SOLANA_EVENT_DB_TUPLE_READ', entry)
        amount = deserialize_fval(entry[7], 'amount', 'solana event')
        return cls(
            identifier=entry[0],
            event_identifier=entry[1],
            sequence_index=entry[2],
            timestamp=TimestampMS(entry[3]),
            location_label=entry[5],
            asset=Asset(entry[6]).check_existence(),
            amount=amount,
            notes=entry[8],
            event_type=HistoryEventType.deserialize(entry[9]),
            event_subtype=HistoryEventSubType.deserialize(entry[10]),
            extra_data=cls.deserialize_extra_data(entry=entry, extra_data=entry[11]),
            signature=Signature.from_bytes(entry[13]),
            counterparty=entry[14],
            address=deserialize_optional(input_val=entry[15], fn=SolanaAddress),
        )

    @classmethod
    def deserialize(cls: type['SolanaEvent'], data: dict[str, Any]) -> 'SolanaEvent':
        base_data = cls._deserialize_base_history_data(data)
        base_data.pop('location')  # type: ignore[misc]  # remove the location key.
        try:
            return cls(  # type: ignore[misc]  # location is already removed.
                **base_data,
                signature=Signature.from_bytes(data['signature']),
                address=deserialize_optional(data['address'], SolanaAddress),
                counterparty=deserialize_optional(data['counterparty'], str),
            )
        except KeyError as e:
            raise DeserializationError(f'Did not find key {e!s} in Solana Event data') from e

    def __eq__(self, other: object) -> bool:
        return (  # ignores are due to object and type checks in super not recognized
            HistoryBaseEntry.__eq__(self, other) is True and
            self.counterparty == other.counterparty and  # type: ignore
            self.signature == other.signature and  # type: ignore
            self.address == other.address  # type: ignore
        )

    def __repr__(self) -> str:
        fields = self._history_base_entry_repr_fields() + [
            f'{self.signature=}',
            f'{self.counterparty=}',
            f'{self.address=}',
        ]
        return f'SolanaEvent({", ".join(fields)})'

    def __str__(self) -> str:
        return (
            f'{self.event_type} / {self.event_subtype} SolanaEvent with '
            f'signature={self.signature} and time '
            f'{timestamp_to_date(ts_ms_to_sec(self.timestamp))} using {self.asset}'
        )
