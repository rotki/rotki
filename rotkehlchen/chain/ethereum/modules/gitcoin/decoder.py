import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.ethereum.modules.gitcoin.constants import (
    FUNDS_CLAIMED,
    GITCOIN_GC15_MATCHING,
    GITCOIN_GOVERNOR_ALPHA,
    GITCOIN_GRANTS_OLD1,
)
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.decoding.constants import CPT_GITCOIN
from rotkehlchen.chain.evm.decoding.gitcoin.decoder import GitcoinOldCommonDecoder
from rotkehlchen.chain.evm.decoding.interfaces import GovernableDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    FAILED_ENRICHMENT_OUTPUT,
    DecoderContext,
    DecodingOutput,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DAI
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


class GitcoinDecoder(GovernableDecoderInterface, GitcoinOldCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        GovernableDecoderInterface.__init__(
            self,
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            protocol=CPT_GITCOIN,
            proposals_url='https://www.tally.xyz/gov/gitcoin/proposal',
        )
        GitcoinOldCommonDecoder.__init__(
            self,
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            bulkcheckout_address=string_to_evm_address('0x7d655c57f71464B6f83811C55D84009Cd9f5221C'),
        )

    def _maybe_enrich_gitcoin_transfers(
            self,
            context: EnricherContext,
    ) -> TransferEnrichmentOutput:
        """
        This is using enrichment output since the GITCOIN_GRANTS_OLD1 contract
        emits no logs and just transfers the tokens.

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

    def _decode_matching_claim(self, context: DecoderContext, name: str) -> DecodingOutput:
        if context.tx_log.topics[0] != FUNDS_CLAIMED:
            return DEFAULT_DECODING_OUTPUT

        if not self.base.is_tracked(claimee := hex_or_bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_DECODING_OUTPUT

        amount = token_normalized_value_decimals(
            token_amount=hex_or_bytes_to_int(context.tx_log.topics[2]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,  # it's always DAI here, so 18
        )
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == A_DAI and
                    event.balance.amount == amount and
                    event.location_label == claimee
            ):
                event.event_subtype = HistoryEventSubType.DONATE
                event.counterparty = CPT_GITCOIN
                event.notes = f'Claim {amount} DAI as matching funds payout for gitcoin {name}'
                break

        else:
            log.error(
                f'Failed to find the gitcoin matching receive transfer for {self.evm_inquirer.chain_name} transaction {context.transaction.tx_hash.hex()}.',  # noqa: E501
            )

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            GITCOIN_GOVERNOR_ALPHA: (self._decode_governance,),
            GITCOIN_GC15_MATCHING: (self._decode_matching_claim, 'round 15'),

        } | super().addresses_to_decoders()

    def enricher_rules(self) -> list[Callable]:
        return [
            self._maybe_enrich_gitcoin_transfers,
        ]
