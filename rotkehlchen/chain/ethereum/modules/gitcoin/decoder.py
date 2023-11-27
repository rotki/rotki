import logging
from collections.abc import Callable

from rotkehlchen.chain.evm.decoding.constants import CPT_GITCOIN, GITCOIN_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    FAILED_ENRICHMENT_OUTPUT,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GitcoinDecoder(DecoderInterface):

    def _maybe_enrich_gitcoin_transfers(
            self,
            context: EnricherContext,
    ) -> TransferEnrichmentOutput:
        """
        May raise:
        - UnknownAsset
        - WrongAssetType
        """
        if context.transaction.to_address not in {
                '0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE',
                '0x7d655c57f71464B6f83811C55D84009Cd9f5221C',
        }:
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

    # -- DecoderInterface methods

    def enricher_rules(self) -> list[Callable]:
        return [
            self._maybe_enrich_gitcoin_transfers,
        ]

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (GITCOIN_CPT_DETAILS,)
