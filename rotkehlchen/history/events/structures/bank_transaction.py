from typing import TYPE_CHECKING, Any, NotRequired, TypedDict, cast

from rotkehlchen.history.events.structures.base import HistoryBaseEntryType, HistoryEvent

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
    from rotkehlchen.types import Location, TimestampMS


class BankTransactionExtraData(TypedDict):
    """What a bank transaction carries beyond the common event columns"""
    bank_account_id: str
    kind: str  # the serialized BankTransactionKind
    counterparty_account: NotRequired[str]  # IBAN or whatever the bank shows
    reference: NotRequired[str]  # the payment reference


class BankTransactionEvent(HistoryEvent):
    """A settled transaction of a connected bank account.

    A history event in everything but its entry type: it prices, filters and accounts like one,
    and the entry type is what lets the history view show or hide bank transactions as a group,
    apart from exchange events which share the plain history event type.
    """

    def __init__(
            self,
            group_identifier: str,
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
            extra_data: BankTransactionExtraData | dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
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
            extra_data=cast('dict[str, Any] | None', extra_data),
        )

    @property
    def entry_type(self) -> HistoryBaseEntryType:
        return HistoryBaseEntryType.BANK_TRANSACTION_EVENT

    def __repr__(self) -> str:
        return f'BankTransactionEvent({", ".join(self._history_base_entry_repr_fields())})'

    @classmethod
    def deserialize(cls: type[BankTransactionEvent], data: dict[str, Any]) -> BankTransactionEvent:
        return cls(**cls._deserialize_base_history_data(data))
