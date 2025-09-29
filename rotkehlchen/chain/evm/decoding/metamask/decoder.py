from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.modules.constants import AMM_POSSIBLE_COUNTERPARTIES
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CPT_METAMASK_SWAPS, METAMASK_FEE_TOPIC, SWAP_SIGNATURE

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class MetamaskCommonDecoder(DecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            router_address: ChecksumEvmAddress,
            fee_receiver_address: ChecksumEvmAddress,
    ) -> None:
        super().__init__(evm_inquirer, base_tools, msg_aggregator)
        self.router_address = router_address
        self.fee_receiver_address = fee_receiver_address

    def _decode_swap(self, context: DecoderContext) -> DecodingOutput:
        """
        This function is used to decode the swap done by metamask.

        By reading the contract code: https://etherscan.io/address/0x881d40237659c251811cec9c364ef91dc08d300c#code#F18#L95
        the spending address and the receiving address seems to always be the same,
        so it doesn't check for that.
        """

        if context.tx_log.topics[0] != SWAP_SIGNATURE:
            return DEFAULT_DECODING_OUTPUT

        sender = bytes_to_address(context.tx_log.topics[2])
        if not self.base.is_tracked(sender):
            return DEFAULT_DECODING_OUTPUT

        fee_raw = fee_asset_address = fee_asset = None  # extract the fee info
        for log in context.all_logs:
            if log.topics[0] == METAMASK_FEE_TOPIC:
                fee_raw = int.from_bytes(log.data)
                fee_asset = self.evm_inquirer.native_token
                fee_asset_address = log.address
                break
            if (
                log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                bytes_to_address(log.topics[2]) == self.fee_receiver_address
            ):
                fee_raw = int.from_bytes(log.data)
                fee_asset_address = log.address
                break

        out_event = in_event = None
        for event in context.decoded_events:
            if (
                    (event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.SPEND) or  # noqa: E501
                    (event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE and event.location_label == sender)  # noqa: E501
            ):  # find the send event
                event.counterparty = CPT_METAMASK_SWAPS
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.notes = f'Swap {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} in metamask'  # noqa: E501
                event.address = self.router_address
                out_event = event
            elif (
                    (event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.RECEIVE) or  # noqa: E501
                    (event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and event.location_label == sender)  # noqa: E501
            ):  # find the receive event
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} as the result of a metamask swap'  # noqa: E501
                # use this index as the event may be a native currency transfer
                # and appear at the start
                event.sequence_index = context.tx_log.log_index
                in_event = event
            elif (
                    event.event_type == HistoryEventType.TRADE and
                    event.event_subtype == HistoryEventSubType.SPEND and
                    event.counterparty in AMM_POSSIBLE_COUNTERPARTIES
            ):  # It is possible that in the same transaction we find events
                # decoded by another amm such as uniswap and then the metamask decoder
                # (as it appears at the end). In those cases we need to
                # take the out event as the other amm event
                out_event = event

        if not (out_event and in_event):
            return DEFAULT_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )

        if not (fee_raw and fee_asset_address):
            # if fee is not found then we have already updated the events so exit
            return DecodingOutput(process_swaps=True)

        if fee_asset is None:  # if fee_asset is not determined yet
            if (  # determine it from in_event/out_event
                in_event.asset.is_evm_token() and
                fee_asset_address == in_event.asset.resolve_to_evm_token().evm_address
            ):
                fee_asset = in_event.asset.resolve_to_evm_token()
            else:
                fee_asset = out_event.asset.resolve_to_evm_token()

        # update the in_event/out_event to adjust their balance with fees
        fee_amount = asset_normalized_value(amount=fee_raw, asset=fee_asset)
        if in_event.asset == fee_asset:
            in_event.amount += fee_amount
            in_event.notes = f'Receive {in_event.amount} {fee_asset.symbol} as the result of a metamask swap'  # noqa: E501
        elif out_event.asset == fee_asset:
            out_event.amount -= fee_amount
            out_event.notes = f'Swap {out_event.amount} {fee_asset.symbol} in metamask'

        # And now create a new event for the fee
        fee_event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.FEE,
            asset=fee_asset,
            amount=fee_amount,
            notes=f'Spend {fee_amount} {fee_asset.symbol} as metamask fees',
        )

        return DecodingOutput(events=[fee_event], process_swaps=True)

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            self.router_address: (self._decode_swap,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_METAMASK_SWAPS,
            label='metamask swaps',
            image='metamask.svg',
        ),)
