from typing import Any

from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.modules.constants import AMM_POSSIBLE_COUNTERPARTIES
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.oneinch.constants import ONEINCH_ICON, ONEINCH_LABEL
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from ..constants import CPT_ONEINCH_V1

HISTORY = b'\x89M\xbf\x12b\x19\x9c$\xe1u\x02\x98\xa3\x84\xc7\t\x16\x0fI\xd1cB,\xc6\xce\xe6\x94\xc77\x13\xf1\xd2'  # noqa: E501
SWAPPED = b'\xe2\xce\xe3\xf6\x83`Y\x82\x0bg9C\x85:\xfe\xbd\x9b0&\x12]\xab\rwB\x84\xe6\xf2\x8aHU\xbe'  # noqa: E501


class Oneinchv1Decoder(EvmDecoderInterface):

    def _decode_history(self, context: DecoderContext) -> EvmDecodingOutput:
        sender = bytes_to_address(context.tx_log.topics[1])
        if not self.base.is_tracked(sender):
            return DEFAULT_EVM_DECODING_OUTPUT

        from_token_address = bytes_to_address(context.tx_log.data[0:32])
        to_token_address = bytes_to_address(context.tx_log.data[32:64])
        from_asset = self.base.get_or_create_evm_asset(from_token_address)
        to_asset = self.base.get_or_create_evm_asset(to_token_address)

        from_raw = int.from_bytes(context.tx_log.data[64:96])
        from_amount = asset_normalized_value(from_raw, from_asset)
        to_raw = int.from_bytes(context.tx_log.data[96:128])
        to_amount = asset_normalized_value(to_raw, to_asset)

        out_event = in_event = None
        for event in context.decoded_events:
            if (  # Check for spend and trade/spend since it may have already been decoded by another amm such as uniswap  # noqa: E501
                (event.event_type == HistoryEventType.SPEND or (
                    event.event_type == HistoryEventType.TRADE and
                    event.event_subtype == HistoryEventSubType.SPEND and
                    event.counterparty in AMM_POSSIBLE_COUNTERPARTIES
                )) and
                event.location_label == sender and
                from_amount == event.amount and
                from_asset == event.asset
            ):
                # find the send event
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.counterparty = CPT_ONEINCH_V1
                event.notes = f'Swap {from_amount} {from_asset.symbol} in {CPT_ONEINCH_V1} from {event.location_label}'  # noqa: E501
                out_event = event
            elif event.event_type == HistoryEventType.RECEIVE and event.location_label == sender and to_amount == event.amount and to_asset == event.asset:  # noqa: E501
                # find the receive event
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.counterparty = CPT_ONEINCH_V1
                event.notes = f'Receive {to_amount} {to_asset.symbol} from {CPT_ONEINCH_V1} swap in {event.location_label}'  # noqa: E501
                # use this index as the event may be an ETH transfer and appear at the start
                event.sequence_index = context.tx_log.log_index
                in_event = event

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput(process_swaps=True)

    def _decode_swapped(self, context: DecoderContext) -> EvmDecodingOutput:
        """We use the Swapped event to get the fee kept by 1inch"""
        to_token_address = bytes_to_address(context.tx_log.topics[2])
        to_asset = self.base.get_or_create_evm_asset(to_token_address)
        to_raw = int.from_bytes(context.tx_log.data[32:64])
        fee_raw = int.from_bytes(context.tx_log.data[96:128])
        if fee_raw == 0:
            return DEFAULT_EVM_DECODING_OUTPUT  # no need to do anything for zero fee taken

        full_amount = asset_normalized_value(to_raw + fee_raw, to_asset)
        sender_address = None
        for event in context.decoded_events:
            # Edit the full amount in the swap's receive event
            crypto_asset = event.asset.resolve_to_crypto_asset()
            if event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.RECEIVE and event.counterparty == CPT_ONEINCH_V1:  # noqa: E501
                event.amount = full_amount
                event.notes = f'Receive {full_amount} {crypto_asset.symbol} from {CPT_ONEINCH_V1} swap in {event.location_label}'  # noqa: E501
                sender_address = event.location_label
                break

        if sender_address is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        # And now create a new event for the fee
        fee_amount = asset_normalized_value(fee_raw, to_asset)
        fee_event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=to_asset,
            amount=fee_amount,
            notes=f'Deduct {fee_amount} {to_asset.symbol} from {sender_address} as {CPT_ONEINCH_V1} fees',  # noqa: E501
        )
        return EvmDecodingOutput(events=[fee_event], process_swaps=True)

    def decode_action(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == HISTORY:
            return self._decode_history(context=context)
        if context.tx_log.topics[0] == SWAPPED:
            return self._decode_swapped(context=context)

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            string_to_evm_address('0x11111254369792b2Ca5d084aB5eEA397cA8fa48B'): (self.decode_action,),  # noqa: E501
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_ONEINCH_V1,
            label=ONEINCH_LABEL,
            image=ONEINCH_ICON,
        ),)
