import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.gitcoin.constants import (
    FUNDS_CLAIMED,
    GITCOIN_GOVERNOR_ALPHA,
    GITCOIN_GRANTS_OLD1,
)
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
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
from rotkehlchen.constants.assets import A_DAI, A_GRT
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

    def _decode_matching_claim(self, context: DecoderContext, name: str, asset: Asset) -> DecodingOutput:  # noqa: E501
        """Decode the matching funds claim based on the given name and asset. We need
        to provide the name and the asset as this is based per contract and does not change.

        For the token we could query it but the name we can't. Still since it's hard
        coded per contract and we have a hard coded list it's best to not ask the chain
        and do an extra network query since this is immutable."""
        if context.tx_log.topics[0] != FUNDS_CLAIMED:
            return DEFAULT_DECODING_OUTPUT

        if not self.base.is_tracked(claimee := hex_or_bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_DECODING_OUTPUT

        asset = asset.resolve_to_crypto_asset()
        amount = asset_normalized_value(
            amount=hex_or_bytes_to_int(context.tx_log.topics[2]),
            asset=asset,
        )
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == asset and
                    event.balance.amount == amount and
                    event.location_label == claimee
            ):
                event.event_subtype = HistoryEventSubType.DONATE
                event.counterparty = CPT_GITCOIN
                event.notes = f'Claim {amount} {asset.symbol} as matching funds payout for gitcoin {name}'  # noqa: E501
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
        } | {
            address: (self._decode_matching_claim, name, asset) for address, name, asset in [
                (string_to_evm_address('0xC8AcA0b50F3Ca9A0cBe413d8a110a7aab7d4C1aE'), 'grants 15 main round', A_DAI),  # noqa: E501
                (string_to_evm_address('0x2878883dD4345C7b35c13FefC5096dd400814D91'), 'grants 14 main round', A_DAI),  # noqa: E501
                (string_to_evm_address('0xa640830aFAa6455E198eDa49E085C4C377789ddd'), 'grants 14 graph protocol round', A_GRT),  # noqa: E501
            ]

        } | super().addresses_to_decoders()

    def enricher_rules(self) -> list[Callable]:
        return [
            self._maybe_enrich_gitcoin_transfers,
        ]
