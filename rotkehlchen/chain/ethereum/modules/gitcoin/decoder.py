import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.ethereum.modules.gitcoin.constants import (
    DONATION_SENT,
    GITCOIN_GOVERNOR_ALPHA,
    GITCOIN_GRANTS_BULKCHECKOUT,
    GITCOIN_GRANTS_OLD1,
)
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.constants import CPT_GITCOIN, GITCOIN_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.interfaces import GovernableDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    FAILED_ENRICHMENT_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GitcoinDecoder(GovernableDecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            protocol=CPT_GITCOIN,
            proposals_url='https://www.tally.xyz/gov/gitcoin/proposal',
        )

    def _maybe_enrich_gitcoin_transfers(
            self,
            context: EnricherContext,
    ) -> TransferEnrichmentOutput:
        """
        This is using enrichment output since the GITCOIN_GRANTS_OLD1 contract
        emits no longs and just transfers the tokens.

        May raise:
        - UnknownAsset
        - WrongAssetType
        """
        if context.transaction.to_address != GITCOIN_GRANTS_OLD1:
            return FAILED_ENRICHMENT_OUTPUT

        crypto_asset = context.event.asset.resolve_to_crypto_asset()
        if context.event.event_type == HistoryEventType.SPEND:
            to_address = context.event.address
            context.event.notes = f'Donate {context.event.balance.amount} {crypto_asset.symbol} to {to_address} via gitcoin'  # noqa: E501
        else:  # can only be RECEIVE
            from_address = context.event.address
            context.event.notes = f'Receive donation of {context.event.balance.amount} {crypto_asset.symbol} from {from_address} via gitcoin'  # noqa: E501

        context.event.event_subtype = HistoryEventSubType.DONATE
        context.event.counterparty = CPT_GITCOIN
        return TransferEnrichmentOutput(matched_counterparty=CPT_GITCOIN)

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
            GITCOIN_GOVERNOR_ALPHA: (self._decode_governance,),
            GITCOIN_GRANTS_BULKCHECKOUT: (self._decode_bulkcheckout,),
        }

    def enricher_rules(self) -> list[Callable]:
        return [
            self._maybe_enrich_gitcoin_transfers,
        ]

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (GITCOIN_CPT_DETAILS,)
