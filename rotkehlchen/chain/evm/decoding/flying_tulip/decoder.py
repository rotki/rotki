from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType

from .constants import CPT_FLYING_TULIP, FLYING_TULIP_CPT_DETAILS

if TYPE_CHECKING:
    from collections.abc import Container

    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext
    from rotkehlchen.fval import FVal
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
            allowed_labels: Container[ChecksumEvmAddress],
            allowed_addresses: Container[ChecksumEvmAddress],
            to_event_type: HistoryEventType,
            to_event_subtype: HistoryEventSubType,
            notes: str,
    ) -> bool:
        """Match the wallet transfer belonging to a protocol event and turn it
        into the protocol movement. Only transfers with a known protocol
        counterparty are eligible, so an unrelated equal-amount transfer in the
        same transaction can never be claimed. Nothing is created when no
        transfer matches, since such events move funds inside the protocol
        without touching the wallet.
        """
        for event in context.decoded_events:
            if (
                    event.event_type == from_event_type and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == token and
                    event.amount == amount and
                    event.location_label in allowed_labels and
                    event.address in allowed_addresses
            ):
                event.event_type = to_event_type
                event.event_subtype = to_event_subtype
                event.notes = notes
                event.counterparty = CPT_FLYING_TULIP
                event.address = context.tx_log.address
                return True

        return False

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (FLYING_TULIP_CPT_DETAILS,)
