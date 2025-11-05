import logging
from typing import TYPE_CHECKING, Any, Literal

from solders.solders import Signature

from rotkehlchen.history.events.structures.base import (
    HistoryBaseEntryType,
)
from rotkehlchen.history.events.structures.onchain_event import OnchainEvent
from rotkehlchen.history.events.structures.types import (
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_tx_signature
from rotkehlchen.types import (
    FVal,
    Location,
    SolanaAddress,
    TimestampMS,
)

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SolanaEvent(OnchainEvent[Signature, SolanaAddress]):  # hash in superclass

    def __init__(
            self,
            tx_ref: Signature,
            sequence_index: int,
            timestamp: TimestampMS,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            asset: 'Asset',
            amount: FVal,
            # Keep location param to reuse parent's deserialize methods
            location: Literal[Location.SOLANA] = Location.SOLANA,
            location_label: str | None = None,
            notes: str | None = None,
            identifier: int | None = None,
            counterparty: str | None = None,
            address: SolanaAddress | None = None,
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
    def _calculate_group_identifier(tx_ref: Signature, location: Location) -> str:
        return str(tx_ref)

    @staticmethod
    def _serialize_tx_ref_for_db(tx_ref: Signature) -> bytes:
        return tx_ref.to_bytes()

    @staticmethod
    def _deserialize_tx_ref(tx_ref_data: Any) -> Signature:
        return deserialize_tx_signature(tx_ref_data)

    @staticmethod
    def deserialize_address(address_data: Any) -> SolanaAddress:
        return SolanaAddress(address_data)

    @property
    def entry_type(self) -> HistoryBaseEntryType:
        return HistoryBaseEntryType.SOLANA_EVENT
