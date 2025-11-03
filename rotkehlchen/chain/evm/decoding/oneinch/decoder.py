from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

from .constants import CPT_ONEINCH, ONEINCH_ICON


class OneinchCommonDecoder(EvmDecoderInterface, ABC):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            router_address: 'ChecksumEvmAddress',
            swapped_signatures: list[bytes],
            counterparty: str = CPT_ONEINCH,
    ) -> None:
        super().__init__(evm_inquirer, base_tools, msg_aggregator)
        self.router_address = router_address
        self.swapped_signatures = swapped_signatures
        self.counterparty = counterparty

    def _create_swapped_events(
            self,
            context: DecoderContext,
            sender: ChecksumEvmAddress,
            receiver: ChecksumEvmAddress,
            source_token_address: ChecksumEvmAddress,
            destination_token_address: ChecksumEvmAddress,
            spent_amount_raw: int,
            return_amount_raw: int,
    ) -> EvmDecodingOutput:
        """Function to abstract the functionality of oneinch decoding where Once
        the data has been pulled from the log we create the decoded events"""
        if not self.base.any_tracked([sender, receiver]):
            return DEFAULT_EVM_DECODING_OUTPUT

        source_token = self.base.get_or_create_evm_asset(source_token_address)
        destination_token = self.base.get_or_create_evm_asset(destination_token_address)
        spent_amount = asset_normalized_value(amount=spent_amount_raw, asset=source_token)
        return_amount = asset_normalized_value(amount=return_amount_raw, asset=destination_token)

        out_event = in_event = None
        for event in context.decoded_events:
            # Now find the sending and receiving events
            if event.event_type == HistoryEventType.SPEND and event.location_label == sender and spent_amount == event.amount and source_token == event.asset:  # noqa: E501
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.counterparty = self.counterparty
                event.notes = f'Swap {spent_amount} {source_token.symbol} in {self.counterparty}'
                event.address = self.router_address
                out_event = event
            elif event.event_type == HistoryEventType.RECEIVE and event.location_label == sender and receiver == event.location_label and return_amount == event.amount and destination_token == event.asset:  # noqa: E501
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive {return_amount} {destination_token.symbol} from {self.counterparty} swap'  # noqa: E501
                # use this index as the event may be an ETH transfer and appear at the start
                event.sequence_index = context.tx_log.log_index
                in_event = event

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput(process_swaps=True)

    @staticmethod
    def generate_counterparty_details(counterparty: str) -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=counterparty,
            label=counterparty.replace('-v', ' V'),
            image=ONEINCH_ICON,
        ),)

    @abstractmethod
    def _decode_swapped(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode the swapped log for the particular 1inch version"""

    def decode_action(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] in self.swapped_signatures:
            return self._decode_swapped(context=context)

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            self.router_address: (self.decode_action,),
        }
