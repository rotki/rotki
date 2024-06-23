import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.constants import CPT_GITCOIN, GITCOIN_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import DONATION_SENT

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GitcoinOldCommonDecoder(DecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            bulkcheckout_address: ChecksumEvmAddress,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.bulkcheckout_address = bulkcheckout_address

    def _decode_bulkcheckout(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != DONATION_SENT:
            return DEFAULT_DECODING_OUTPUT

        donor_tracked, dst_tracked = False, False
        if self.base.is_tracked(donor := hex_or_bytes_to_address(context.tx_log.topics[3])):
            donor_tracked = True

        if self.base.is_tracked(destination := hex_or_bytes_to_address(context.tx_log.data)):
            dst_tracked = True

        if donor_tracked is False and dst_tracked is False:
            return DEFAULT_DECODING_OUTPUT

        asset = self.base.get_or_create_evm_asset(hex_or_bytes_to_address(context.tx_log.topics[1]))  # this checks for ETH special address inside # noqa: E501
        amount = asset_normalized_value(
            amount=hex_or_bytes_to_int(context.tx_log.topics[2]),
            asset=asset,
        )

        for event in context.decoded_events:
            if event.asset == asset and event.balance.amount == amount:
                if dst_tracked:
                    event.event_type = HistoryEventType.RECEIVE
                    event.event_subtype = HistoryEventSubType.DONATE
                    event.counterparty = CPT_GITCOIN
                    event.location_label = destination
                    event.address = donor
                    event.notes = f'Receive donation of {amount} {asset.resolve_to_asset_with_symbol().symbol} from {donor} via gitcoin'  # noqa: E501
                else:
                    event.event_type = HistoryEventType.SPEND
                    event.event_subtype = HistoryEventSubType.DONATE
                    event.counterparty = CPT_GITCOIN
                    event.location_label = donor
                    event.address = destination
                    event.notes = f'Donate {amount} {asset.resolve_to_asset_with_symbol().symbol} to {destination} via gitcoin'  # noqa: E501

                break

        else:  # not found so transfer event gets decoded later
            if dst_tracked:
                from_event_type = HistoryEventType.RECEIVE
                location_label = destination
                address = donor
                notes = f'Receive donation of {amount} {asset.resolve_to_asset_with_symbol().symbol} from {donor} via gitcoin'  # noqa: E501
            else:
                from_event_type = HistoryEventType.SPEND
                location_label = donor
                address = destination
                notes = f'Donate {amount} {asset.resolve_to_asset_with_symbol().symbol} to {destination} via gitcoin'  # noqa: E501

            action_item = ActionItem(
                action='transform',
                from_event_type=from_event_type,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=asset,
                amount=amount,
                to_event_subtype=HistoryEventSubType.DONATE,
                to_location_label=location_label,
                to_address=address,
                to_notes=notes,
                to_counterparty=CPT_GITCOIN,
            )
            return DecodingOutput(action_items=[action_item])

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            self.bulkcheckout_address: (self._decode_bulkcheckout,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (GITCOIN_CPT_DETAILS,)
