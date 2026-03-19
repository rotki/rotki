import logging
from typing import TYPE_CHECKING, Any, Literal

from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.onchain_event import OnchainEvent
from rotkehlchen.history.events.structures.types import (
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    FVal,
    Location,
    StarknetAddress,
    TimestampMS,
)

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class StarknetEvent(OnchainEvent[str, StarknetAddress]):

    def __init__(
            self,
            tx_ref: str,
            sequence_index: int,
            timestamp: TimestampMS,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            asset: 'Asset',
            amount: FVal,
            location: Literal[Location.STARKNET] = Location.STARKNET,
            location_label: str | None = None,
            notes: str | None = None,
            identifier: int | None = None,
            counterparty: str | None = None,
            address: StarknetAddress | None = None,
            extra_data: dict[str, Any] | None = None,
            group_identifier: str | None = None,
    ) -> None:
        super().__init__(
            tx_ref=tx_ref,
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
            counterparty=counterparty,
            address=address,
            extra_data=extra_data,
            group_identifier=group_identifier,
        )

    @staticmethod
    def _calculate_group_identifier(tx_ref: str, location: Location) -> str:
        return tx_ref

    @staticmethod
    def _serialize_tx_ref_for_db(tx_ref: str) -> bytes:
        return tx_ref.encode('utf-8')

    @staticmethod
    def _deserialize_tx_ref(tx_ref_data: Any) -> str:
        if isinstance(tx_ref_data, bytes):
            return tx_ref_data.decode('utf-8')
        return str(tx_ref_data)

    @staticmethod
    def deserialize_address(address_data: Any) -> StarknetAddress:
        return StarknetAddress(address_data)

    @property
    def entry_type(self) -> HistoryBaseEntryType:
        return HistoryBaseEntryType.STARKNET_EVENT
