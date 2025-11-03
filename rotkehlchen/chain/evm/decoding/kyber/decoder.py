import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import CryptoAsset
from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.constants import SWAPPED_TOPIC
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    CPT_KYBER,
    KYBER_AGGREGATOR_CONTRACT,
    KYBER_CPT_DETAILS,
)

if TYPE_CHECKING:
    from rotkehlchen.history.events.structures.evm_event import EvmEvent

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class KyberCommonDecoder(EvmDecoderInterface):

    def _maybe_update_events(
            self,
            decoded_events: list['EvmEvent'],
            sender: ChecksumEvmAddress,
            source_asset: CryptoAsset,
            destination_asset: CryptoAsset,
            spent_amount: FVal,
            return_amount: FVal,
            counterparty: str,
    ) -> None:
        """
        Use the information from a trade transaction to modify the HistoryEvents from receive/send
        to trade if the conditions are correct.
        """
        in_event = out_event = None
        for event in decoded_events:
            crypto_asset = event.asset.symbol_or_name()
            # it can happen that a spend event get decoded first by an amm decoder. To make sure
            # that the event matches we check both event type and subtype
            if (event.event_type == HistoryEventType.SPEND or event.event_subtype == HistoryEventSubType.SPEND) and event.location_label == sender and event.asset == source_asset and event.amount == spent_amount:  # noqa: E501
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.counterparty = counterparty
                event.notes = f'Swap {event.amount} {crypto_asset} in kyber'
                out_event = event
            elif (event.event_type == HistoryEventType.RECEIVE or event.event_subtype == HistoryEventSubType.RECEIVE) and event.location_label == sender and event.amount == return_amount and destination_asset == event.asset:  # noqa: E501
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive {event.amount} {crypto_asset} from kyber swap'
                in_event = event

            if out_event is not None and in_event is not None:
                maybe_reshuffle_events(ordered_events=[out_event, in_event], events_list=decoded_events)  # noqa: E501

    def _decode_aggregator_trade(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decodes a kyber aggregator swap, updating the events with proper metadata"""
        if context.tx_log.topics[0] != SWAPPED_TOPIC:
            return DEFAULT_EVM_DECODING_OUTPUT

        sender = bytes_to_address(context.tx_log.data[:32])
        receiver = bytes_to_address(context.tx_log.data[96:128])

        if self.base.any_tracked([sender, receiver]) is False:
            return DEFAULT_EVM_DECODING_OUTPUT

        source_token_address = bytes_to_address(context.tx_log.data[32:64])
        destination_token_address = bytes_to_address(context.tx_log.data[64:96])
        spent_amount_raw = int.from_bytes(context.tx_log.data[128:160])
        return_amount_raw = int.from_bytes(context.tx_log.data[160:192])

        source_asset = self.base.get_or_create_evm_asset(source_token_address)
        destination_asset = self.base.get_or_create_evm_asset(destination_token_address)
        spent_amount = asset_normalized_value(amount=spent_amount_raw, asset=source_asset)
        return_amount = asset_normalized_value(amount=return_amount_raw, asset=destination_asset)
        self._maybe_update_events(
            decoded_events=context.decoded_events,
            sender=sender,
            source_asset=source_asset,
            destination_asset=destination_asset,
            spent_amount=spent_amount,
            return_amount=return_amount,
            counterparty=CPT_KYBER,
        )

        return EvmDecodingOutput(process_swaps=True)

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {KYBER_AGGREGATOR_CONTRACT: (self._decode_aggregator_trade,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_KYBER, **KYBER_CPT_DETAILS),)
