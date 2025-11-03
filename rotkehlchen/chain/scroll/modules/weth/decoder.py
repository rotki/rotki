import logging
from typing import TYPE_CHECKING

from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.decoding.structures import DEFAULT_EVM_DECODING_OUTPUT
from rotkehlchen.chain.evm.decoding.weth.decoder import WethDecoder as EthBaseWethDecoder
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext, EvmDecodingOutput


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class WethDecoder(EthBaseWethDecoder):
    def _decode_deposit_event(self, context: 'DecoderContext') -> 'EvmDecodingOutput':
        depositor = bytes_to_address(context.tx_log.topics[1])
        deposited_amount_raw = int.from_bytes(context.tx_log.data[:32])
        deposited_amount = asset_normalized_value(
            amount=deposited_amount_raw,
            asset=self.base_asset,
        )

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.address == self.wrapped_token.evm_address and
                event.amount == deposited_amount and
                event.asset == self.base_asset
            ):
                event.counterparty = self.counterparty
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.notes = f'Wrap {deposited_amount} ETH in WETH'
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == deposited_amount and
                event.asset == self.wrapped_token
            ):  # scroll WETH does emit an event on transfer so we can edit the event instead of creating a new one  # noqa: E501
                event.notes = f'Receive {deposited_amount} WETH'
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = self.counterparty
                event.location_label = depositor
                event.address = context.transaction.to_address

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_withdrawal_event(self, context: 'DecoderContext') -> 'EvmDecodingOutput':
        if not self.base.is_tracked(withdrawer := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        withdrawn_amount_raw = int.from_bytes(context.tx_log.data[:32])
        withdrawn_amount = asset_normalized_value(
            amount=withdrawn_amount_raw,
            asset=self.base_asset,
        )
        in_event = out_event = None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.address == self.wrapped_token.evm_address and
                event.amount == withdrawn_amount and
                event.asset == self.base_asset
            ):
                in_event = event
                event.notes = f'Receive {withdrawn_amount} ETH'
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.counterparty = self.counterparty
            elif (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == withdrawn_amount and
                event.asset == self.wrapped_token
            ):  # scroll WETH does emit an event on transfer so we can edit the event instead of creating a new one  # noqa: E501
                event.notes = f'Unwrap {withdrawn_amount} WETH'
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = self.counterparty
                event.location_label = withdrawer
                event.address = context.transaction.to_address
                out_event = event

        if in_event is None or out_event is None:
            log.error(f'Could not find the corresponding events when decoding weth scroll withdrawal {context.transaction.tx_hash!s}')  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return DEFAULT_EVM_DECODING_OUTPUT
