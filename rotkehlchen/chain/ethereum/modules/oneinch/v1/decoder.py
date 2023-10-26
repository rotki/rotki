from typing import Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.modules.constants import AMM_POSSIBLE_COUNTERPARTIES
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.oneinch.constants import ONEINCH_ICON, ONEINCH_LABEL
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from ..constants import CPT_ONEINCH_V1

HISTORY = b'\x89M\xbf\x12b\x19\x9c$\xe1u\x02\x98\xa3\x84\xc7\t\x16\x0fI\xd1cB,\xc6\xce\xe6\x94\xc77\x13\xf1\xd2'  # noqa: E501
SWAPPED = b'\xe2\xce\xe3\xf6\x83`Y\x82\x0bg9C\x85:\xfe\xbd\x9b0&\x12]\xab\rwB\x84\xe6\xf2\x8aHU\xbe'  # noqa: E501


class Oneinchv1Decoder(DecoderInterface):

    def _decode_history(self, context: DecoderContext) -> DecodingOutput:
        sender = hex_or_bytes_to_address(context.tx_log.topics[1])
        if not self.base.is_tracked(sender):
            return DEFAULT_DECODING_OUTPUT

        from_token_address = hex_or_bytes_to_address(context.tx_log.data[0:32])
        to_token_address = hex_or_bytes_to_address(context.tx_log.data[32:64])
        from_asset = self.base.get_or_create_evm_asset(from_token_address)
        to_asset = self.base.get_or_create_evm_asset(to_token_address)

        from_raw = hex_or_bytes_to_int(context.tx_log.data[64:96])
        from_amount = asset_normalized_value(from_raw, from_asset)
        to_raw = hex_or_bytes_to_int(context.tx_log.data[96:128])
        to_amount = asset_normalized_value(to_raw, to_asset)

        out_event = in_event = None
        for event in context.decoded_events:
            if event.event_type == HistoryEventType.SPEND and event.location_label == sender and from_amount == event.balance.amount and from_asset == event.asset:  # noqa: E501
                # find the send event
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.counterparty = CPT_ONEINCH_V1
                event.notes = f'Swap {from_amount} {from_asset.symbol} in {CPT_ONEINCH_V1} from {event.location_label}'  # noqa: E501
                out_event = event
            elif event.event_type == HistoryEventType.RECEIVE and event.location_label == sender and to_amount == event.balance.amount and to_asset == event.asset:  # noqa: E501
                # find the receive event
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.counterparty = CPT_ONEINCH_V1
                event.notes = f'Receive {to_amount} {to_asset.symbol} from {CPT_ONEINCH_V1} swap in {event.location_label}'  # noqa: E501
                # use this index as the event may be an ETH transfer and appear at the start
                event.sequence_index = context.tx_log.log_index
                in_event = event
            elif (
                event.event_type == HistoryEventType.TRADE and
                event.event_subtype == HistoryEventSubType.SPEND and
                event.counterparty in AMM_POSSIBLE_COUNTERPARTIES
            ):
                # It is possible that in the same transaction we find events decoded by another amm
                # such as uniswap and then the 1inch decoder (as it appears at the end). In those
                # cases we need to take the out event as the other amm event
                out_event = event

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return DEFAULT_DECODING_OUTPUT

    def _decode_swapped(self, context: DecoderContext) -> DecodingOutput:
        """We use the Swapped event to get the fee kept by 1inch"""
        to_token_address = hex_or_bytes_to_address(context.tx_log.topics[2])
        to_asset = self.base.get_or_create_evm_asset(to_token_address)
        to_raw = hex_or_bytes_to_int(context.tx_log.data[32:64])
        fee_raw = hex_or_bytes_to_int(context.tx_log.data[96:128])
        if fee_raw == 0:
            return DEFAULT_DECODING_OUTPUT  # no need to do anything for zero fee taken

        full_amount = asset_normalized_value(to_raw + fee_raw, to_asset)
        sender_address = None
        for event in context.decoded_events:
            # Edit the full amount in the swap's receive event
            crypto_asset = event.asset.resolve_to_crypto_asset()
            if event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.RECEIVE and event.counterparty == CPT_ONEINCH_V1:  # noqa: E501
                event.balance.amount = full_amount
                event.notes = f'Receive {full_amount} {crypto_asset.symbol} from {CPT_ONEINCH_V1} swap in {event.location_label}'  # noqa: E501
                sender_address = event.location_label
                break

        if sender_address is None:
            return DEFAULT_DECODING_OUTPUT

        # And now create a new event for the fee
        fee_amount = asset_normalized_value(fee_raw, to_asset)
        fee_event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=to_asset,
            balance=Balance(amount=fee_amount),
            location_label=sender_address,
            notes=f'Deduct {fee_amount} {to_asset.symbol} from {sender_address} as {CPT_ONEINCH_V1} fees',  # noqa: E501
            counterparty=CPT_ONEINCH_V1,
            address=context.transaction.to_address,
        )
        return DecodingOutput(event=fee_event)

    def decode_action(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == HISTORY:
            return self._decode_history(context=context)
        if context.tx_log.topics[0] == SWAPPED:
            return self._decode_swapped(context=context)

        return DEFAULT_DECODING_OUTPUT

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
