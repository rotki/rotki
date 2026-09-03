from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType

from .constants import CPT_FLYING_TULIP, FLYING_TULIP_CPT_DETAILS

if TYPE_CHECKING:
    from collections.abc import Container, Sequence

    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress


class FlyingTulipCommonDecoder(EvmDecoderInterface):
    """Shared base for the Flying Tulip product decoders.

    Each product (ftUSD, lending, puts) has its own decoder inheriting from
    this class so they all expose the same counterparty metadata.
    """

    def _transform_matching_event(
            self,
            context: DecoderContext,
            from_event_type: HistoryEventType,
            token: EvmToken,
            amount: FVal,
            allowed_labels: Sequence[ChecksumEvmAddress] | None,  # None allows any tracked wallet
            allowed_addresses: Container[ChecksumEvmAddress],
            to_event_type: HistoryEventType,
            to_event_subtype: HistoryEventSubType,
            notes: str,
    ) -> EvmEvent | None:
        """Match the wallet transfer belonging to a protocol event and turn it
        into the protocol movement, returning it. Only transfers with a known
        protocol counterparty are eligible, so an unrelated equal-amount
        transfer in the same transaction can never be claimed. Nothing is
        created when no transfer matches, since such events move funds inside
        the protocol without touching the wallet.
        """
        for event in context.decoded_events:
            if (
                    event.event_type == from_event_type and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == token and
                    event.amount == amount and
                    (allowed_labels is None or event.location_label in allowed_labels) and
                    event.address is not None and
                    event.address in allowed_addresses
            ):
                event.event_type = to_event_type
                event.event_subtype = to_event_subtype
                event.notes = notes
                event.counterparty = CPT_FLYING_TULIP
                event.address = context.tx_log.address
                return event

        return None

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (FLYING_TULIP_CPT_DETAILS,)
