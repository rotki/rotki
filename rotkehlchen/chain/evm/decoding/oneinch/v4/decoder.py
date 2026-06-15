import logging
from abc import ABC
from collections.abc import Callable
from typing import TYPE_CHECKING

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.modules.oneinch.constants import CPT_ONEINCH_V4
from rotkehlchen.chain.evm.constants import DEPOSIT_TOPIC_V2, SWAPPED_TOPIC
from rotkehlchen.chain.evm.decoding.balancer.v2.constants import (
    V2_SWAP as BALANCER_V2_SWAP_SIGNATURE,
)
from rotkehlchen.chain.evm.decoding.curve.constants import TOKEN_EXCHANGE
from rotkehlchen.chain.evm.decoding.oneinch.decoder import OneinchCommonDecoder
from rotkehlchen.chain.evm.decoding.oneinch.v4.constants import (
    DEFI_PLAZA_SWAPPED,
    LIQUIDITY_BOOK_SWAP,
    ORDERFILLED_RFQ,
    PANCAKE_SWAP_TOPIC,
    WOMBATV2_SWAPPED,
)
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.uniswap.v2.constants import UNISWAP_V2_SWAP_SIGNATURE
from rotkehlchen.chain.evm.decoding.uniswap.v3.constants import (
    SWAP_SIGNATURE as UNISWAP_V3_SWAP_SIGNATURE,
)
from rotkehlchen.chain.evm.decoding.velodrome.decoder import SWAP_V2 as VELODROME_SWAP_SIGNATURE
from rotkehlchen.chain.evm.decoding.weth.decoder import WETH_WITHDRAW_TOPIC
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Oneinchv3n4DecoderBase(OneinchCommonDecoder, ABC):
    """Base class for Oneinch v3 and v4"""

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            counterparty: str,
            router_address: ChecksumEvmAddress,
            limit_order_topics: list[bytes] | None = None,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            router_address=router_address,
            swapped_signatures=[
                VELODROME_SWAP_SIGNATURE,
                UNISWAP_V3_SWAP_SIGNATURE,
                UNISWAP_V2_SWAP_SIGNATURE,  # uniswap v2 is also used by sushiswap
                BALANCER_V2_SWAP_SIGNATURE,
                ORDERFILLED_RFQ,
                TOKEN_EXCHANGE,  # curve is also used by 1inch
                SWAPPED_TOPIC,
                DEFI_PLAZA_SWAPPED,
                LIQUIDITY_BOOK_SWAP,
                PANCAKE_SWAP_TOPIC,
                WOMBATV2_SWAPPED,
            ],
            counterparty=counterparty,
            limit_order_topics=limit_order_topics,
        )

    def _decode_limit_order_swap(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode a 1inch limit order / Fusion swap by pairing the maker's spend and receive
        legs. Unlike _decode_swapped this does not rely on the transaction initiator, since
        these orders can be settled by a resolver on the maker's behalf.

        TODO: Handle resolver fees.
        https://github.com/orgs/rotki/projects/11/views/3?pane=issue&itemId=137038891
        """
        if context.tx_log.topics[0] not in self.limit_order_topics:
            return DEFAULT_EVM_DECODING_OUTPUT

        out_event, in_event = None, None
        for event in context.decoded_events:
            if (
                out_event is None and (
                    (event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE) or  # noqa: E501
                    (event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.SPEND)  # noqa: E501
                ) and event.counterparty != CPT_GAS
            ):
                out_event = event
            elif (
                in_event is None and (
                    (event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE) or  # noqa: E501
                    (event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.RECEIVE)  # noqa: E501
                )
            ):
                in_event = event

        if out_event is None or in_event is None:
            log.warning('Failed to find one leg of 1inch limit order swap in %s', context.transaction)  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        for event, new_event_subtype, notes in [
            (out_event, HistoryEventSubType.SPEND, 'Swap {amount} {symbol} in a 1inch limit order'),  # noqa: E501
            (in_event, HistoryEventSubType.RECEIVE, 'Receive {amount} {symbol} as the result of a 1inch limit order'),  # noqa: E501
        ]:
            event.notes = notes.format(amount=event.amount, symbol=event.asset.resolve_to_asset_with_symbol().symbol)  # noqa: E501
            event.counterparty = self.counterparty
            event.event_subtype = new_event_subtype
            event.event_type = HistoryEventType.TRADE

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput(process_swaps=True)

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
            # Limit order / Fusion settlements need to be handled first and independently of the
            # transaction initiator, since the OrderFilled log may appear before the transfers
            # and the order can be settled by a resolver rather than the maker themselves.
            if tx_log.topics[0] in self.limit_order_topics:
                if any(
                    event.event_type == HistoryEventType.TRADE and
                    event.counterparty == self.counterparty
                    for event in decoded_events
                ):
                    # already paired during decoding (the OrderFilled log was processed after
                    # the transfers via addresses_to_decoders), so there is nothing left to do.
                    return decoded_events

                self._decode_limit_order_swap(DecoderContext(
                    tx_log=tx_log,
                    transaction=transaction,
                    decoded_events=decoded_events,
                    all_logs=all_logs,
                    action_items=[],
                ))
                return decoded_events

        tx_has_weth_transfer = False
        weth_transfer_tx_log = None
        for tx_log in all_logs:
            if tx_log.topics[0] in [DEPOSIT_TOPIC_V2, WETH_WITHDRAW_TOPIC]:
                tx_has_weth_transfer = True
                weth_transfer_tx_log = tx_log

            elif tx_log.topics[0] in self.swapped_signatures:
                context = DecoderContext(
                    tx_log=tx_log,
                    transaction=transaction,
                    decoded_events=decoded_events,
                    all_logs=all_logs,
                    action_items=[],
                )
                self._decode_swapped(context)
                return decoded_events

        if tx_has_weth_transfer is True:
            # If the transaction has a WETH contract deposit or withdraw and no swap event was
            # found, then it is WETH to ETH or ETH to WETH conversion. Decode it as a swap.
            context = DecoderContext(
                tx_log=weth_transfer_tx_log,  # type: ignore
                transaction=transaction,
                decoded_events=decoded_events,
                all_logs=all_logs,
                action_items=[],
            )
            self._decode_swapped(context)

        return decoded_events

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {self.counterparty: [(0, self._handle_post_decoding)]}

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return {self.router_address: self.counterparty}

    def _decode_swapped(self, context: DecoderContext) -> EvmDecodingOutput:
        sender = context.transaction.from_address
        decoded_events = context.decoded_events
        out_event = in_event = None
        for event in decoded_events:
            if event.location_label != sender:
                continue

            if (
                event.event_type == HistoryEventType.RECEIVE or
                (event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.RECEIVE)  # It can happen that a leg of the swap was processed by a previous decoder like uniswap # noqa: E501
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive {event.amount} {event.asset.symbol_or_name()} as a result of a {self.counterparty} swap'  # noqa: E501
                in_event = event
            elif (
                (
                    event.event_type == HistoryEventType.SPEND or
                    (event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.SPEND)  # noqa: E501
                ) and
                event.event_subtype != HistoryEventSubType.FEE
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.counterparty = self.counterparty
                event.notes = f'Swap {event.amount} {event.asset.symbol_or_name()} in {self.counterparty}'  # noqa: E501
                event.address = self.router_address
                out_event = event

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=decoded_events,
        )
        return EvmDecodingOutput(process_swaps=True)

    # -- DecoderInterface methods

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return OneinchCommonDecoder.generate_counterparty_details(CPT_ONEINCH_V4)
