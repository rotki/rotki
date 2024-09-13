from typing import Any

from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.gnosis.modules.gnosis_pay.constants import (
    CPT_GNOSIS_PAY,
    GNOSIS_PAY_CASHBACK_ADDRESS,
    GNOSIS_PAY_CPT_DETAILS,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress


class GnosisPayDecoder(DecoderInterface):

    def decode_cashback_events(self, context: DecoderContext) -> DecodingOutput:
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset.identifier == 'eip155:100/erc20:0x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb'  # noqa: E501
            ):
                event.counterparty = CPT_GNOSIS_PAY
                event.event_subtype = HistoryEventSubType.CASHBACK
                event.notes = f'Receive cashback of {event.balance.amount} GNO from Gnosis Pay'

        return DEFAULT_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {GNOSIS_PAY_CASHBACK_ADDRESS: (self.decode_cashback_events,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (GNOSIS_PAY_CPT_DETAILS,)
