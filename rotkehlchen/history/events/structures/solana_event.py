import logging
from typing import TYPE_CHECKING, Any, Literal

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.solana.rpc import Signature
from rotkehlchen.history.events.structures.auto_notes import (
    OUTGOING_TRANSFER_TYPES,
    SOLANA_FEE_TEMPLATE,
    SOLANA_TRANSFER_TEMPLATE,
    TRANSFER_VERBS,
    is_plain_transfer,
)
from rotkehlchen.history.events.structures.base import (
    HistoryBaseEntryType,
)
from rotkehlchen.history.events.structures.onchain_event import OnchainEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
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
            asset: Asset,
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

    def auto_notes(self) -> str | None:
        """Notes of the events every Solana transaction produces before protocol specific
        decoding: the transaction fee and plain transfers."""
        if (
            self.counterparty == CPT_GAS and
            self.event_type == HistoryEventType.SPEND and
            self.event_subtype == HistoryEventSubType.FEE
        ):
            return SOLANA_FEE_TEMPLATE.format(amount=self.amount, symbol=self.asset.symbol_or_name())  # noqa: E501

        if is_plain_transfer(self.event_type, self.event_subtype, self.counterparty):
            if (counterparty_or_address := self.counterparty or self.address) is not None:
                suffix = f" {'to' if self.event_type in OUTGOING_TRANSFER_TYPES else 'from'} {counterparty_or_address}"  # noqa: E501
            else:
                suffix = ''

            return SOLANA_TRANSFER_TEMPLATE.format(
                verb=TRANSFER_VERBS[self.event_type],
                amount=self.amount,
                symbol=self.asset.symbol_or_name(),
                suffix=suffix,
            )

        return super().auto_notes()
