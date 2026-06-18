import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.decoding.clipper.constants import (
    CLIPPER_CPT_DETAILS,
    CLIPPER_LABEL,
    CLIPPER_SWAPPED_TOPIC,
    CPT_CLIPPER,
)
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset, CryptoAsset
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ClipperCommonDecoder(EvmDecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            pool_addresses: set[ChecksumEvmAddress],
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.pool_addresses = pool_addresses
        self.wrapped_native = self.node_inquirer.wrapped_native_token

    def _decode_swapped(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != CLIPPER_SWAPPED_TOPIC:
            return DEFAULT_EVM_DECODING_OUTPUT

        if context.tx_log.address not in self.pool_addresses:
            return DEFAULT_EVM_DECODING_OUTPUT

        in_asset_address = bytes_to_address(context.tx_log.topics[1])
        out_asset_address = bytes_to_address(context.tx_log.topics[2])
        recipient = bytes_to_address(context.tx_log.topics[3])
        if not self.base.any_tracked([recipient, context.transaction.from_address]):
            return DEFAULT_EVM_DECODING_OUTPUT

        in_amount_raw = int.from_bytes(context.tx_log.data[:32])
        out_amount_raw = int.from_bytes(context.tx_log.data[32:64])

        in_asset = self.base.get_or_create_evm_asset(in_asset_address)
        out_asset = self.base.get_or_create_evm_asset(out_asset_address)

        in_amount = asset_normalized_value(amount=in_amount_raw, asset=in_asset)
        out_amount = asset_normalized_value(amount=out_amount_raw, asset=out_asset)

        # If the swap involves the wrapped native token, check whether the user
        # actually sent or received the native currency (e.g. ETH) rather than
        # the wrapped token (e.g. WETH). Clipper emits the wrapped token address
        # in the Swapped event even when the user interacts with native currency.
        if in_asset == self.wrapped_native:
            in_asset = self._maybe_resolve_native_spend(
                decoded_events=context.decoded_events,
                recipient=recipient,
                amount=in_amount,
            )
            in_amount = asset_normalized_value(amount=in_amount_raw, asset=in_asset)

        if out_asset == self.wrapped_native:
            out_asset = self._maybe_resolve_native_receive(
                decoded_events=context.decoded_events,
                recipient=recipient,
                amount=out_amount,
            )
            out_amount = asset_normalized_value(amount=out_amount_raw, asset=out_asset)

        out_event = self._find_and_update_spend_event(
            decoded_events=context.decoded_events,
            recipient=recipient,
            asset=in_asset,
            amount=in_amount,
            pool_address=context.tx_log.address,
        )
        in_event = self._find_and_update_receive_event(
            decoded_events=context.decoded_events,
            recipient=recipient,
            asset=out_asset,
            amount=out_amount,
            pool_address=context.tx_log.address,
        )

        if out_event is None or in_event is None:
            log.warning(
                'Failed to find both out and in events for %s swap transaction %s',
                CLIPPER_LABEL,
                context.transaction,
            )
        else:
            maybe_reshuffle_events(
                ordered_events=[out_event, in_event],
                events_list=context.decoded_events,
            )

        return EvmDecodingOutput(process_swaps=True)

    def _maybe_resolve_native_spend(
            self,
            decoded_events: list['EvmEvent'],
            recipient: ChecksumEvmAddress,
            amount: 'FVal',
    ) -> 'CryptoAsset':
        """If the user spent native currency instead of the wrapped token, return native token."""
        for event in decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == self.node_inquirer.native_token and
                event.amount == amount and
                event.location_label == recipient
            ):
                return self.node_inquirer.native_token
        return self.wrapped_native

    def _maybe_resolve_native_receive(
            self,
            decoded_events: list['EvmEvent'],
            recipient: ChecksumEvmAddress,
            amount: 'FVal',
    ) -> 'CryptoAsset':
        """If the user received native currency instead of the wrapped token, return native token."""  # noqa: E501
        for event in decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == self.node_inquirer.native_token and
                event.amount == amount and
                event.location_label == recipient
            ):
                return self.node_inquirer.native_token
        return self.wrapped_native

    def _find_and_update_spend_event(
            self,
            decoded_events: list['EvmEvent'],
            recipient: ChecksumEvmAddress,
            asset: 'Asset',
            amount: 'FVal',
            pool_address: ChecksumEvmAddress,
    ) -> 'EvmEvent | None':
        for event in decoded_events:
            if (
                (
                    (event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE) or  # noqa: E501
                    (event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.SPEND)  # noqa: E501
                ) and
                event.location_label == recipient and
                event.asset == asset and
                event.amount == amount
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.notes = f'Swap {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} in {CLIPPER_LABEL}'  # noqa: E501
                event.counterparty = CPT_CLIPPER
                event.address = pool_address
                return event
        return None

    def _find_and_update_receive_event(
            self,
            decoded_events: list['EvmEvent'],
            recipient: ChecksumEvmAddress,
            asset: 'Asset',
            amount: 'FVal',
            pool_address: ChecksumEvmAddress,
    ) -> 'EvmEvent | None':
        for event in decoded_events:
            if (
                (
                    (event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE) or  # noqa: E501
                    (event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.RECEIVE)  # noqa: E501
                ) and
                event.location_label == recipient and
                event.asset == asset and
                event.amount == amount
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} as the result of a swap in {CLIPPER_LABEL}'  # noqa: E501
                event.counterparty = CPT_CLIPPER
                event.address = pool_address
                return event
        return None

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return dict.fromkeys(self.pool_addresses, (self._decode_swapped,))

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CLIPPER_CPT_DETAILS,)
