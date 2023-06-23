from typing import TYPE_CHECKING, Callable

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.decoding.oneinch.decoder import OneinchCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.accounting.structures.evm_event import EvmEvent

from rotkehlchen.chain.ethereum.modules.balancer.v2.decoder import (
    V2_SWAP as BALANCER_V2_SWAP_SIGNATURE,
)
from rotkehlchen.chain.ethereum.modules.uniswap.v2.decoder import (
    SWAP_SIGNATURE as UNISWAP_V2_SWAP_SIGNATURE,
)
from rotkehlchen.chain.ethereum.modules.uniswap.v3.decoder import (
    SWAP_SIGNATURE as UNISWAP_V3_SWAP_SIGNATURE,
)

from ..constants import CPT_ONEINCH_V4
from .constants import ONEINCH_V4_MAINNET_ROUTER


class Oneinchv4Decoder(OneinchCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            router_address=ONEINCH_V4_MAINNET_ROUTER,
            swapped_signatures=[
                UNISWAP_V3_SWAP_SIGNATURE,
                UNISWAP_V2_SWAP_SIGNATURE,  # uniswap v2 is also used by sushiswap
                BALANCER_V2_SWAP_SIGNATURE,
            ],
            counterparty=CPT_ONEINCH_V4,
        )

    def _handle_post_decoding(
            self,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            all_logs: list[EvmTxReceiptLog],
    ) -> list['EvmEvent']:
        """
        It handles the case where a swap is done via 1inch v4 on any of the known pool contracts.
        In that case there are 3 simple decoded events already created: Fee, spend and receive.
        If Spend and receive events are not decoded by the swap decoder (for example from uniswap
        v3 decoder), they should be decoded by this aggregator decoder.
        The decoding is done with this post decoding rule and not from
        addresses_to_decoders mapping because the 1inch v4 router is not in the addresses of the
        logs of the transaction, and consequently it can't be extracted and mapped.
        """
        for tx_log in all_logs:
            if tx_log.topics[0] in self.swapped_signatures:
                context = DecoderContext(
                    tx_log=tx_log,
                    transaction=transaction,
                    decoded_events=decoded_events,
                    all_logs=all_logs,
                    action_items=[],
                )
                self._decode_swapped(context)
        return decoded_events

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_ONEINCH_V4: [(0, self._handle_post_decoding)]}

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return {ONEINCH_V4_MAINNET_ROUTER: CPT_ONEINCH_V4}

    def _decode_swapped(self, context: DecoderContext) -> DecodingOutput:
        sender = context.transaction.from_address
        decoded_events = context.decoded_events
        out_event = in_event = None
        for event in decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.location_label == sender:
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.counterparty = self.counterparty
                event.notes = f'Receive {event.balance.amount} {event.asset.symbol_or_name()} as a result of a {self.counterparty} swap'  # noqa: E501
                in_event = event
            elif event.event_type == HistoryEventType.SPEND and event.event_subtype != HistoryEventSubType.FEE and event.location_label == sender:  # noqa: E501
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.counterparty = self.counterparty
                event.notes = f'Swap {event.balance.amount} {event.asset.symbol_or_name()} in {self.counterparty}'  # noqa: E501
                event.address = None
                out_event = event

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=decoded_events,
        )
        return DEFAULT_DECODING_OUTPUT
