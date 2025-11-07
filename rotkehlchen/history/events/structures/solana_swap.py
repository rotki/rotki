from typing import TYPE_CHECKING, Any, Literal, cast

from solders.solders import Signature

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.serialization.deserialize import deserialize_fval, deserialize_optional
from rotkehlchen.types import SolanaAddress, TimestampMS
from rotkehlchen.utils.misc import timestamp_to_date, ts_ms_to_sec

from .solana_event import SolanaEvent
from .swap import SwapEvent

if TYPE_CHECKING:
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.types import CHAIN_EVENT_DB_TUPLE_READ


class SolanaSwapEvent(SolanaEvent, SwapEvent):

    def __init__(
            self,
            tx_ref: Signature,
            sequence_index: int,
            timestamp: TimestampMS,
            event_subtype: Literal[
                HistoryEventSubType.SPEND,
                HistoryEventSubType.RECEIVE,
                HistoryEventSubType.FEE,
            ],
            asset: Asset,
            amount: 'FVal',
            event_type: Literal[
                HistoryEventType.TRADE,
                HistoryEventType.MULTI_TRADE,
            ] = HistoryEventType.TRADE,
            location_label: str | None = None,
            notes: str | None = None,
            identifier: int | None = None,
            counterparty: str | None = None,
            address: SolanaAddress | None = None,
            extra_data: dict[str, Any] | None = None,
            group_identifier: str | None = None,
    ):
        """Combines SolanaEvent with SwapEvent to represent solana swaps.

        The group_identifier is initialized from SolanaEvent constructor
        """
        super().__init__(
            tx_ref=tx_ref,
            sequence_index=sequence_index,
            timestamp=timestamp,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=asset,
            amount=amount,
            location_label=location_label,
            notes=notes,
            identifier=identifier,
            counterparty=counterparty,
            address=address,
            extra_data=extra_data,
            group_identifier=group_identifier,
        )

    @property
    def entry_type(self) -> HistoryBaseEntryType:
        return HistoryBaseEntryType.SOLANA_SWAP_EVENT

    @classmethod
    def deserialize_from_db(cls: type['SolanaSwapEvent'], entry: tuple) -> 'SolanaSwapEvent':
        """Deserialize a SolanaSwapEvent DB tuple.
        May raise:
        - DeserializationError
        - UnknownAsset
        But these exceptions shouldn't normally happen since
        the data from the db should already be correct.
        """
        entry = cast('CHAIN_EVENT_DB_TUPLE_READ', entry)
        amount = deserialize_fval(entry[7], 'amount', 'solana swap event')
        return cls(
            identifier=entry[0],
            group_identifier=entry[1],
            sequence_index=entry[2],
            timestamp=TimestampMS(entry[3]),
            location_label=entry[5],
            asset=Asset(entry[6]).check_existence(),
            amount=amount,
            notes=entry[8] or None,
            event_type=HistoryEventType.deserialize(entry[9]),  # type: ignore  # event type and subtype should always be correct from the DB
            event_subtype=HistoryEventSubType.deserialize(entry[10]),  # type: ignore
            extra_data=cls.deserialize_extra_data(entry=entry, extra_data=entry[11]),
            tx_ref=Signature.from_bytes(entry[13]),
            counterparty=entry[14],
            address=SolanaAddress(entry[15]) if entry[15] is not None else None,
        )

    def serialize(self) -> dict[str, Any]:
        """Serialize the event for api."""
        return SolanaEvent.serialize(self)

    @classmethod
    def deserialize(cls: type['SolanaSwapEvent'], data: dict[str, Any]) -> 'SolanaSwapEvent':
        swap_data = cls._deserialize_swap_data(cls._deserialize_base_history_data(data))
        swap_data.pop('location')  # type: ignore[misc]  # remove the location key.
        try:
            return cls(  # type: ignore[misc]  # remove the location key.
                **swap_data,
                tx_ref=Signature.from_string(data['tx_ref']),
                counterparty=deserialize_optional(data['counterparty'], str),
                address=SolanaAddress(data['address']) if data.get('address') is not None else None,  # noqa: E501
            )
        except KeyError as e:
            raise DeserializationError(f'Did not find key {e!s} in SolanaSwapEvent data') from e

    def __repr__(self) -> str:
        fields = self._history_base_entry_repr_fields() + [
            f'self.tx_ref={self.tx_ref!s}',  # convert to string to avoid newlines from solders library  # noqa: E501
            f'{self.counterparty=}',
            f'{self.address=}',
        ]
        return f'SolanaSwapEvent({", ".join(fields)})'

    def __str__(self) -> str:
        return (
            f'{self.event_subtype} SolanaSwapEvent in {self.location} with '
            f'tx_ref={self.tx_ref} and time '
            f'{timestamp_to_date(ts_ms_to_sec(self.timestamp))} using {self.asset}'
        )

    # -- Methods of AccountingEventMixin

    @staticmethod
    def get_accounting_event_type() -> AccountingEventType:
        return AccountingEventType.TRADE
