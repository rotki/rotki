import logging
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.accounting.entry_type_mappings import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.oneinch.constants import CPT_ONEINCH_V6, ONEINCH_V6_ROUTER
from rotkehlchen.chain.evm.decoding.oneinch.decoder import OneinchCommonDecoder
from rotkehlchen.chain.evm.decoding.oneinch.v4.decoder import Oneinchv3n4DecoderBase
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    EvmDecodingOutput,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.decoding.decoder import DecoderContext
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
ORDER_FILLED_TOPIC: Final = b'\xfe\xc315\x0f\xcex\xbae\x8e\x08*q\xda \xac\x9f\x8dy\x8a\x99\xb3\xc7\x96\x81\xc8D\x0c\xbf\xe7~\x07'  # noqa: E501


class Oneinchv6Decoder(Oneinchv3n4DecoderBase):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            router_address=ONEINCH_V6_ROUTER,
            counterparty=CPT_ONEINCH_V6,
        )

    def _decode_limit_order_swap(self, context: 'DecoderContext') -> EvmDecodingOutput:
        """Decode 1inch v6 limit order swap transactions.

        TODO: Handle resolver fees.
        https://github.com/orgs/rotki/projects/11/views/3?pane=issue&itemId=137038891
        """
        if context.tx_log.topics[0] != ORDER_FILLED_TOPIC:
            return DEFAULT_EVM_DECODING_OUTPUT

        out_event, in_event = None, None
        for event in context.decoded_events:
            if (
                    out_event is None and
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.counterparty != CPT_GAS
            ):
                out_event = event
            elif (
                    in_event is None and
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE
            ):
                in_event = event

        if out_event is None or in_event is None:
            log.warning(f'Failed to find one leg of 1inch limit order swap in {context.transaction}')  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        for event, new_event_subtype, notes in [
            (out_event, HistoryEventSubType.SPEND, 'Swap {amount} {symbol} in a 1inch limit order'),  # noqa: E501
            (in_event, HistoryEventSubType.RECEIVE, 'Receive {amount} {symbol} as the result of a 1inch limit order'),  # noqa: E501
        ]:
            event.notes = notes.format(amount=event.amount, symbol=event.asset.resolve_to_asset_with_symbol().symbol)  # noqa: E501
            event.counterparty = self.counterparty
            event.event_subtype = new_event_subtype
            event.event_type = HistoryEventType.TRADE

        return EvmDecodingOutput(process_swaps=True)

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return super().addresses_to_decoders() | {
            self.router_address: (self._decode_limit_order_swap,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return OneinchCommonDecoder.generate_counterparty_details(CPT_ONEINCH_V6)
