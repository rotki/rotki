import logging
from typing import Any

from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CPT_MAGPIE, MAGPIE_ICON, MAGPIE_LABEL, MAGPIE_ROUTER, SWAPPED

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class MagpieDecoder(DecoderInterface):
    """Decoder for Magpie protocol swaps"""

    def _decode_swap(self, context: DecoderContext) -> DecodingOutput:
        """Decode a swap event from Magpie protocol"""
        if context.tx_log.topics[0] != SWAPPED:
            return DEFAULT_DECODING_OUTPUT

        if len(context.tx_log.topics) != 3:
            log.warning(
                f'Magpie swap event at {context.transaction.tx_hash.hex()} has '
                f'{len(context.tx_log.topics)} topics instead of 3',
            )
            return DEFAULT_DECODING_OUTPUT

        # Extract swap data from event
        # Event structure: topics[1] = sender, topics[2] = receiver (usually same as sender)
        # Data: fromToken, toToken, fromAmount, toAmount
        sender = bytes_to_address(context.tx_log.topics[1])

        # Parse data field - 4 fields of 32 bytes each
        if len(context.tx_log.data) < 128:  # 4 * 32 bytes
            log.warning(
                f'Magpie swap event at {context.transaction.tx_hash.hex()} has '
                f'insufficient data length: {len(context.tx_log.data)}',
            )
            return DEFAULT_DECODING_OUTPUT

        data = context.tx_log.data
        source_token_address = bytes_to_address(data[:32])
        destination_token_address = bytes_to_address(data[32:64])
        spent_amount_raw = int.from_bytes(data[64:96])
        received_amount_raw = int.from_bytes(data[96:128])

        # Get tokens - handle ETH represented as zero address
        if source_token_address == ZERO_ADDRESS:
            source_token = self.evm_inquirer.native_token
        else:
            source_token = self.base.get_or_create_evm_asset(source_token_address)

        if destination_token_address == ZERO_ADDRESS:
            destination_token = self.evm_inquirer.native_token
        else:
            destination_token = self.base.get_or_create_evm_asset(destination_token_address)

        # Normalize amounts
        spent_amount = asset_normalized_value(amount=spent_amount_raw, asset=source_token)
        received_amount = asset_normalized_value(
            amount=received_amount_raw,
            asset=destination_token,
        )

        # Find and modify the transfer events
        out_event = in_event = None
        spending_events = []

        for event in context.decoded_events:
            # Skip if event doesn't belong to the sender
            if event.location_label != sender:
                continue

            # Find spending events of the source token
            if (
                event.asset == source_token and
                event.event_type in (HistoryEventType.SPEND, HistoryEventType.TRADE) and
                event.event_subtype in (HistoryEventSubType.NONE, HistoryEventSubType.SPEND)
            ):
                spending_events.append(event)

            # Find the receiving event
            elif (
                event.asset == destination_token and
                event.amount == received_amount and
                event.event_type in (HistoryEventType.RECEIVE, HistoryEventType.TRADE) and
                event.event_subtype in (HistoryEventSubType.NONE, HistoryEventSubType.RECEIVE)
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.counterparty = CPT_MAGPIE
                event.notes = (
                    f'Receive {received_amount} {destination_token.symbol} '
                    f'from {MAGPIE_LABEL} swap'
                )
                event.address = MAGPIE_ROUTER
                in_event = event

        fee_events = []
        # Process spending events
        if spending_events:
            total_spent = sum(event.amount for event in spending_events)

            # Check if total matches the swap amount
            if total_spent == spent_amount:

                for event in spending_events:
                    if event.address == MAGPIE_ROUTER:
                        # Main swap event
                        event.event_type = HistoryEventType.TRADE
                        event.event_subtype = HistoryEventSubType.SPEND
                        event.counterparty = CPT_MAGPIE
                        event.notes = (
                            f'Swap {event.amount} {source_token.symbol} in {MAGPIE_LABEL}'
                        )
                        out_event = event
                    else:
                        # Fee event
                        event.event_type = HistoryEventType.TRADE
                        event.event_subtype = HistoryEventSubType.FEE
                        event.counterparty = CPT_MAGPIE

                        # Special note for Rabby fee
                        if event.address == string_to_evm_address(
                            '0x39041F1B366fE33F9A5a79dE5120F2Aee2577ebc',
                        ):
                            event.notes = (
                                f'Pay {event.amount} {source_token.symbol} as Rabby interface fee'
                            )
                        else:
                            event.notes = (
                                f'Pay {event.amount} {source_token.symbol} as {MAGPIE_LABEL} fee'
                            )

                        fee_events.append(event)
            else:
                # Single event case - check if it's the exact swap amount
                for event in spending_events:
                    if event.amount == spent_amount:
                        event.event_type = HistoryEventType.TRADE
                        event.event_subtype = HistoryEventSubType.SPEND
                        event.counterparty = CPT_MAGPIE
                        event.notes = (
                            f'Swap {spent_amount} {source_token.symbol} in {MAGPIE_LABEL}'
                        )
                        event.address = MAGPIE_ROUTER
                        out_event = event
                        break

        # Include fee events in reshuffling so they are part of the swap group
        all_trade_events = [out_event, in_event]
        if len(fee_events) != 0:
            all_trade_events.extend(fee_events)

        maybe_reshuffle_events(
            ordered_events=[event for event in all_trade_events if event is not None],
            events_list=context.decoded_events,
        )
        return DecodingOutput(process_swaps=True)

    def decode_action(self, context: DecoderContext) -> DecodingOutput:
        """Main decoding function for Magpie protocol"""
        if context.transaction.to_address != MAGPIE_ROUTER:
            return DEFAULT_DECODING_OUTPUT
        return self._decode_swap(context)

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            MAGPIE_ROUTER: (self._decode_swap,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_MAGPIE,
            label=MAGPIE_LABEL,
            image=MAGPIE_ICON,
        ),)
