from typing import Any, Final

from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.modules.digixdao.constants import (
    A_DGD,
    CPT_DIGIXDAO,
    DIGIX_DGD_ETH_REFUND_CONTRACT,
)
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

REFUND_TOPIC: Final = b's\xf0J\xf9\xdc\xc5\x82\xa9#\xec\x15\xd3\xee\xa9\x90\xfe4\xad\xab\xff\xf2\x87\x9e(\xd4Er\xe0\x1aT\xab\xb6'  # noqa: E501


class DigixdaoDecoder(EvmDecoderInterface):

    def _decode_dgd_eth_refund(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode ETH refund for DGD tokens."""
        if context.tx_log.topics[0] != REFUND_TOPIC:
            return DEFAULT_EVM_DECODING_OUTPUT

        user_address = bytes_to_address(context.tx_log.topics[1])
        dgd_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.topics[2]),
            token_decimals=9,
        )
        eth_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token_decimals=18,
        )
        in_event, out_event = None, None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user_address and
                event.asset == A_DGD and
                event.amount == dgd_amount
            ):
                event.event_subtype = HistoryEventSubType.BURN
                event.notes = f'Burn {event.amount} DGD for ETH'
                event.counterparty = CPT_DIGIXDAO
                out_event = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user_address and
                event.asset == A_ETH and
                event.amount == eth_amount
            ):
                event.event_subtype = HistoryEventSubType.REFUND
                event.notes = f'Receive refund of {event.amount} ETH'
                event.counterparty = CPT_DIGIXDAO
                in_event = event

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {DIGIX_DGD_ETH_REFUND_CONTRACT: (self._decode_dgd_eth_refund,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_DIGIXDAO,
            label='DigixDAO',
            image='digixdao.jpg',
        ),)
