from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType

from .constants import CPT_FLYING_TULIP, FLYING_TULIP_CPT_DETAILS, FLYING_TULIP_LABEL

if TYPE_CHECKING:
    from collections.abc import Container, Sequence

    from rotkehlchen.assets.asset import Asset, EvmToken
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction


class FlyingTulipCommonDecoder(EvmDecoderInterface):
    """Shared transfer matching, relayer expenses and Flying Tulip counterparty metadata."""

    @staticmethod
    def _find_matching_transfer(
            context: DecoderContext,
            event_type: HistoryEventType,
            asset: Asset,
            amount: FVal,
            allowed_labels: Sequence[ChecksumEvmAddress] | None,
            allowed_addresses: Container[ChecksumEvmAddress],
    ) -> EvmEvent | None:
        """Find an unchanged wallet transfer involving an allowed protocol contract.

        Matching does not mutate the event, so callers can require both legs before
        decoding a swap or check for a queued payout before decoding a share burn.
        None for allowed_labels accepts any tracked wallet.
        """
        return next((event for event in context.decoded_events if (
            event.event_type == event_type and
            event.event_subtype == HistoryEventSubType.NONE and
            event.asset == asset and
            event.amount == amount and
            (allowed_labels is None or event.location_label in allowed_labels) and
            event.address is not None and
            event.address in allowed_addresses
        )), None)

    def _transform_matching_event(
            self,
            context: DecoderContext,
            from_event_type: HistoryEventType,
            token: EvmToken,
            amount: FVal,
            allowed_labels: Sequence[ChecksumEvmAddress] | None,
            allowed_addresses: Container[ChecksumEvmAddress],
            to_event_type: HistoryEventType,
            to_event_subtype: HistoryEventSubType,
            notes: str,
    ) -> EvmEvent | None:
        """Transform a matching wallet transfer, leaving protocol-internal movements alone."""
        if (event := self._find_matching_transfer(
            context=context,
            event_type=from_event_type,
            asset=token,
            amount=amount,
            allowed_labels=allowed_labels,
            allowed_addresses=allowed_addresses,
        )) is not None:
            event.event_type = to_event_type
            event.event_subtype = to_event_subtype
            event.notes = notes
            event.counterparty = CPT_FLYING_TULIP
            event.address = context.tx_log.address
        return event

    def _make_relayer_fee_event(
            self,
            transaction: EvmTransaction,
            sequence_index: int,
            token: EvmToken,
            fee_amount: FVal,
            location_label: str | None,
            address: ChecksumEvmAddress,
    ) -> EvmEvent:
        """Build a relayer expense using the caller's log or synthetic event index."""
        return self.base.make_event(
            tx_ref=transaction.tx_hash,
            sequence_index=sequence_index,
            timestamp=transaction.timestamp,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=token,
            amount=fee_amount,
            location_label=location_label,
            notes=f'Spend {fee_amount} {token.symbol} as a {FLYING_TULIP_LABEL} relayer fee',
            counterparty=CPT_FLYING_TULIP,
            address=address,
        )

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (FLYING_TULIP_CPT_DETAILS,)
