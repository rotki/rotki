from abc import ABCMeta
from collections.abc import Callable
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.modules.balancer.v2.constants import (
    V2_SWAP as BALANCER_V2_SWAP_SIGNATURE,
)
from rotkehlchen.chain.ethereum.modules.oneinch.constants import CPT_ONEINCH_V4
from rotkehlchen.chain.ethereum.modules.uniswap.v2.constants import (
    SWAP_SIGNATURE as UNISWAP_V2_SWAP_SIGNATURE,
)
from rotkehlchen.chain.ethereum.modules.uniswap.v3.constants import (
    SWAP_SIGNATURE as UNISWAP_V3_SWAP_SIGNATURE,
)
from rotkehlchen.chain.evm.decoding.oneinch.decoder import OneinchCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.optimism.modules.velodrome.decoder import (
    SWAP_V2 as VELODROME_SWAP_SIGNATURE,
)
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.accounting.structures.evm_event import EvmEvent

from rotkehlchen.chain.ethereum.modules.weth.decoder import WETH_DEPOSIT_TOPIC, WETH_WITHDRAW_TOPIC


class Oneinchv3n4DecoderBase(OneinchCommonDecoder, metaclass=ABCMeta):
    """Base class for Oneinch v3 and v4"""

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            counterparty: str,
            router_address: ChecksumEvmAddress,
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
            ],
            counterparty=counterparty,
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
        tx_has_weth_transfer = False
        weth_transfer_tx_log = None
        for tx_log in all_logs:
            if tx_log.topics[0] in [WETH_DEPOSIT_TOPIC, WETH_WITHDRAW_TOPIC]:
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
            elif (
                    event.event_type in (HistoryEventType.SPEND, HistoryEventType.TRADE) and
                    event.event_subtype != HistoryEventSubType.FEE and
                    event.location_label == sender
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.counterparty = self.counterparty
                event.notes = f'Swap {event.balance.amount} {event.asset.symbol_or_name()} in {self.counterparty}'  # noqa: E501
                event.address = self.router_address
                out_event = event

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=decoded_events,
        )
        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return OneinchCommonDecoder.generate_counterparty_details(CPT_ONEINCH_V4)
