import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.modules.paraswap.constants import PARASWAP_AUGUSTUS_ROUTER
from rotkehlchen.chain.ethereum.modules.uniswap.v2.constants import SWAP_SIGNATURE
from rotkehlchen.chain.ethereum.modules.uniswap.v3.constants import DIRECT_SWAP_SIGNATURE
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
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
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import BUY_SIGNATURE, CPT_PARASWAP, SWAP_SIGNATURE as PARASWAP_SWAP_SIGNATURE

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ParaswapCommonDecoder(DecoderInterface):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            router_address: ChecksumEvmAddress,
            fee_receiver_address: ChecksumEvmAddress,
    ) -> None:
        super().__init__(evm_inquirer, base_tools, msg_aggregator)
        self.router_address = router_address
        self.fee_receiver_address = fee_receiver_address

    def _decode_swap(
            self,
            context: DecoderContext,
            receiver: ChecksumEvmAddress,
            sender: ChecksumEvmAddress,
    ) -> DecodingOutput:
        """This function is used to decode the swap done by paraswap.
        At the moment it does not decode the fee in ETH. For example:
        etherscan.io/tx/0xeeea20b39f157fe59fa4904fd4b62f8971188b53d05c6831e0ed67ee157e40c2
        TODO Note: https://github.com/orgs/rotki/projects/11?pane=issue&itemId=49582891"""
        if not self.base.any_tracked((sender, receiver)):
            return DEFAULT_DECODING_OUTPUT

        out_event: EvmEvent | None = None
        in_event: EvmEvent | None = None
        partial_refund_event: EvmEvent | None = None
        fee_event: EvmEvent | None = None
        for event in context.decoded_events:
            if sender != event.location_label:  # in this case, it's not a valid send/receive event
                continue
            if (
                event.event_type == HistoryEventType.TRADE and
                event.event_subtype == HistoryEventSubType.SPEND or
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE
            ):  # find the send event
                event.counterparty = CPT_PARASWAP
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.address = self.router_address
                # not modifying event.notes here since that's done after partial refund below
                out_event = event
            elif (
                event.event_type == HistoryEventType.TRADE and
                event.event_subtype == HistoryEventSubType.RECEIVE or
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE
            ):  # find the receive event
                event.counterparty = CPT_PARASWAP
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive {event.balance.amount} {event.asset.resolve_to_asset_with_symbol().symbol} as the result of a swap in paraswap'  # noqa: E501
                event.address = self.router_address
                if in_event is None:
                    in_event = event
                else:  # if another in_event is found, then it is a partial refund of in_asset
                    partial_refund_event = event

        if in_event is None or out_event is None:
            log.error(f'Could not find the corresponding events when decoding paraswap swap {context.transaction.tx_hash.hex()}')  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        if partial_refund_event is not None:  # if some in_asset is returned back
            if in_event.asset == out_event.asset:  # check the similarity of asset with out_event
                # due to order of events it can happen that this two get mislabeled and need to be swapped  # noqa: E501
                partial_refund_event, in_event = in_event, partial_refund_event
            out_event.balance.amount -= partial_refund_event.balance.amount  # adjust the amount
            context.decoded_events.remove(partial_refund_event)  # and remove it from the list
        out_event.notes = f'Swap {out_event.balance.amount} {out_event.asset.resolve_to_asset_with_symbol().symbol} in paraswap'  # noqa: E501

        fee_raw = fee_asset = None  # extract the fee info
        if in_event.asset.is_evm_token():
            fee_asset = in_event.asset.resolve_to_evm_token()
            for log_event in context.all_logs:
                if (
                    log_event.topics[0] == ERC20_OR_ERC721_TRANSFER and
                    hex_or_bytes_to_address(log_event.topics[1]) == PARASWAP_AUGUSTUS_ROUTER and
                    hex_or_bytes_to_address(log_event.topics[2]) == self.fee_receiver_address and
                    log_event.address == fee_asset.evm_address
                ):
                    fee_raw = hex_or_bytes_to_int(log_event.data)
                    break

        if fee_raw is not None and fee_asset is not None:
            # update the in_event to adjust its balance since the amount used in fees
            # was also received as part of the swap
            fee_amount = asset_normalized_value(amount=fee_raw, asset=fee_asset)
            in_event.balance.amount += fee_amount
            in_event.notes = f'Receive {in_event.balance.amount} {fee_asset.symbol} as the result of a swap in paraswap'  # noqa: E501

            # And now create a new event for the fee
            fee_event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=fee_asset,
                balance=Balance(amount=fee_amount),
                location_label=sender,
                notes=f'Spend {fee_amount} {fee_asset.symbol} as a paraswap fee',
                counterparty=CPT_PARASWAP,
                address=context.transaction.to_address,
            )
            context.decoded_events.append(fee_event)

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event, fee_event],
            events_list=context.decoded_events,
        )
        return DEFAULT_DECODING_OUTPUT

    def _decode_paraswap_swap(self, context: DecoderContext) -> DecodingOutput:
        """This decodes the following types of trades:
        - Simple Buy
        - Simple Swap
        - Multi Swap
        - Mega Swap"""
        if context.tx_log.topics[0] not in {PARASWAP_SWAP_SIGNATURE, BUY_SIGNATURE}:
            return DEFAULT_DECODING_OUTPUT

        return self._decode_swap(
            context=context,
            receiver=hex_or_bytes_to_address(context.tx_log.topics[1]),
            sender=hex_or_bytes_to_address(context.tx_log.data[96:128]),
        )

    def _decode_uniswap_v2_swap(self, context: DecoderContext) -> DecodingOutput:
        """This decodes swaps done directly on Uniswap V2 pools"""
        return self._decode_swap(
            context=context,
            receiver=hex_or_bytes_to_address(context.tx_log.topics[2]),
            sender=context.transaction.from_address,
        )

    def _decode_uniswap_v3_swap(self, context: DecoderContext) -> DecodingOutput:
        """This decodes swaps done directly on Uniswap V3 pools"""
        return self._decode_swap(
            context=context,
            receiver=hex_or_bytes_to_address(context.tx_log.topics[1]),
            sender=hex_or_bytes_to_address(context.tx_log.data[96:128]),
        )

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            self.router_address: (self._decode_paraswap_swap,),
        }

    def decoding_by_input_data(self) -> dict[bytes, dict[bytes, Callable]]:
        return {  # swapOnUniswapV2Fork, swapOnUniswapV2ForkWithPermit, buyOnUniswapV2Fork
            method_id: {SWAP_SIGNATURE: self._decode_uniswap_v2_swap}
            for method_id in (b'\x0b\x86\xa4\xc1', b'n\x91S\x8b', b'\xb2\xf1\xe6\xdb')
        } | {  # directUniV3Swap, directCurveV1Swap, directCurveV2Swap, directBalancerV2GivenInSwap
            method_id: {DIRECT_SWAP_SIGNATURE: self._decode_uniswap_v3_swap}
            for method_id in (b'\xa6\x88m\xa9', b'8e\xbd\xe6', b'X\xf1Q\x00', b'\xb2/M\xb8')
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_PARASWAP,
            label='Paraswap',
            image='paraswap.svg',
        ),)
