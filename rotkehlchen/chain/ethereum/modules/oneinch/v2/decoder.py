from typing import Any

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, ethaddress_to_asset
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import DecoderContext, DecodingOutput
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from ..constants import CPT_ONEINCH_V2


SWAPPED = b'v\xaf"J\x148e\xa5\x0bAIn\x1asb&\x98i,V\\\x12\x14\xbc\x86/\x18\xe2-\x82\x9c^'
DEFAULT_DECODING_OUTPUT = DecodingOutput(counterparty=CPT_ONEINCH_V2)


class Oneinchv2Decoder(DecoderInterface):

    def _decode_swapped(self, context: DecoderContext) -> DecodingOutput:
        tx_log = context.tx_log
        sender = hex_or_bytes_to_address(tx_log.topics[1])
        source_token_address = hex_or_bytes_to_address(tx_log.topics[2])
        destination_token_address = hex_or_bytes_to_address(tx_log.topics[3])

        source_token = ethaddress_to_asset(source_token_address)
        if source_token is None:
            return DEFAULT_DECODING_OUTPUT
        destination_token = ethaddress_to_asset(destination_token_address)
        if destination_token is None:
            return DEFAULT_DECODING_OUTPUT

        receiver = hex_or_bytes_to_address(tx_log.data[0:32])
        spent_amount_raw = hex_or_bytes_to_int(tx_log.data[64:96])
        return_amount_raw = hex_or_bytes_to_int(tx_log.data[96:128])
        spent_amount = asset_normalized_value(amount=spent_amount_raw, asset=source_token)
        return_amount = asset_normalized_value(amount=return_amount_raw, asset=destination_token)

        out_event = in_event = None
        for event in context.decoded_events:
            # Now find the sending and receiving events
            if event.event_type == HistoryEventType.SPEND and event.location_label == sender and spent_amount == event.balance.amount and source_token == event.asset:  # noqa: E501
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.counterparty = CPT_ONEINCH_V2
                event.notes = f'Swap {spent_amount} {source_token.symbol} in {CPT_ONEINCH_V2}'  # noqa: E501
                out_event = event
            elif event.event_type == HistoryEventType.RECEIVE and event.location_label == sender and receiver == event.location_label and return_amount == event.balance.amount and destination_token == event.asset:  # noqa: E501
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.counterparty = CPT_ONEINCH_V2
                event.notes = f'Receive {return_amount} {destination_token.symbol} from {CPT_ONEINCH_V2} swap'  # noqa: E501
                # use this index as the event may be an ETH transfer and appear at the start
                event.sequence_index = tx_log.log_index
                in_event = event

        maybe_reshuffle_events(
            out_event=out_event,
            in_event=in_event,
            events_list=context.decoded_events,
        )
        return DEFAULT_DECODING_OUTPUT

    def decode_action(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == SWAPPED:
            return self._decode_swapped(context=context)

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            string_to_evm_address('0x111111125434b319222CdBf8C261674aDB56F3ae'): (self.decode_action,),  # noqa: E501
        }

    def counterparties(self) -> list[str]:
        return [CPT_ONEINCH_V2]
