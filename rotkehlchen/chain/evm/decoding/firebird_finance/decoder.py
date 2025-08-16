import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import SWAPPED_TOPIC
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CPT_FIREBIRD_FINANCE, FIREBIRD_FINANCE_LABEL

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class FirebirdFinanceCommonDecoder(DecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            router_address: ChecksumEvmAddress,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.router_address = router_address

    def _decode_swapped(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != SWAPPED_TOPIC:
            return DEFAULT_DECODING_OUTPUT

        sender = bytes_to_address(context.tx_log.data[:32])
        receiver = bytes_to_address(context.tx_log.data[96:128])
        if self.base.any_tracked([sender, receiver]) is False:
            return DEFAULT_DECODING_OUTPUT

        from_token = self.base.get_or_create_evm_asset(bytes_to_address(context.tx_log.data[32:64]))  # noqa: E501
        to_token = self.base.get_or_create_evm_asset(bytes_to_address(context.tx_log.data[64:96]))
        out_amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[128:160]),
            asset=from_token,
        )
        in_amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[160:192]),
            asset=to_token,
        )

        in_event = out_event = None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == sender and
                event.asset == from_token and
                event.amount == out_amount
            ):
                out_event = event
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.notes = f'Swap {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} in {FIREBIRD_FINANCE_LABEL}'  # noqa: E501
                event.counterparty = CPT_FIREBIRD_FINANCE

            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == receiver and
                event.amount == in_amount and
                event.asset == to_token
            ):
                in_event = event
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} as the result of a swap in {FIREBIRD_FINANCE_LABEL}'  # noqa: E501

        if in_event is None or out_event is None:
            log.warning(f'Failed to find both out and in events for {FIREBIRD_FINANCE_LABEL} swap transaction {context.transaction}')  # noqa: E501

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return DecodingOutput(process_swaps=True)

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {self.router_address: (self._decode_swapped,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
                identifier=CPT_FIREBIRD_FINANCE,
                label=FIREBIRD_FINANCE_LABEL,
                image='firebird-finance.png',
        ),)
