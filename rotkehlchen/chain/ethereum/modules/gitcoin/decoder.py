import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.ethereum.modules.gitcoin.constants import (
    GITCOIN_GOVERNOR_ALPHA,
    GITCOIN_GRANTS_OLD1,
)
from rotkehlchen.chain.evm.decoding.constants import CPT_GITCOIN
from rotkehlchen.chain.evm.decoding.gitcoin.decoder import GitcoinOldCommonDecoder
from rotkehlchen.chain.evm.decoding.interfaces import GovernableDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    FAILED_ENRICHMENT_OUTPUT,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import (
    A_AURORA,
    A_DAI,
    A_FORT,
    A_GOHM,
    A_GRT,
    A_MASK,
    A_UDT,
    A_UNI,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GitcoinDecoder(GovernableDecoderInterface, GitcoinOldCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        """Some sources for merkle payouts can be seen here:
        https://github.com/thelostone-mc/merkle_payouts
        Sources for some other payouts:
        https://github.com/gitcoinco/matching_contracts
        """
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
            funds_claimed_matching_contracts=[
                (string_to_evm_address('0xC8AcA0b50F3Ca9A0cBe413d8a110a7aab7d4C1aE'), 'grants 15 main round', A_DAI),  # noqa: E501
                (string_to_evm_address('0x2878883dD4345C7b35c13FefC5096dd400814D91'), 'grants 14 main round', A_DAI),  # noqa: E501
                (string_to_evm_address('0xa640830aFAa6455E198eDa49E085C4C377789ddd'), 'grants 14 graph protocol round', A_GRT),  # noqa: E501
                (string_to_evm_address('0x0019863771b57FBA997cF6602CB2dD572A43e977'), 'grants 13 uniswap round', A_UNI),  # noqa: E501
                (string_to_evm_address('0xF63FD0739cB68651eFbD06BCcb23F1A1623D5520'), 'grants 13 main round', A_DAI),  # noqa: E501
                (string_to_evm_address('0x868CBca73915f842A70cD9584D80a57DB5E690C1'), 'grants 13 Olympus Dao round', A_GOHM),  # noqa: E501
                (string_to_evm_address('0x22fDA1F97F2fD078F4609AaF74914ddf436de8e8'), 'grants 14 Unlock protocol round', A_UDT),  # noqa: E501
                (string_to_evm_address('0x62a5A2E85619c0922B32243165B9BAAB27Bc7E63'), 'grants 14 Mask network round', A_MASK),  # noqa: E501
                (string_to_evm_address('0xeFc138E4e0Fdcd7C9E616cC3E5c356C3ce23B1f2'), 'grants 14 Aurora round', A_AURORA),  # noqa: E501
                (string_to_evm_address('0xf52Bc0cCD2C6174dbB962bc4e71a97F965FcaFC8'), 'grants 15 Forta round', A_FORT),  # noqa: E501
                (string_to_evm_address('0xb40FF1af8E4894884cf060daC15D73385460a99B'), 'grants 15 Aurora round', A_AURORA),  # noqa: E501
                (string_to_evm_address('0x36BAdAd9D2509Ac373f98b936f6d6748dB82F160'), 'grants 15 Mark network round', A_MASK),  # noqa: E501
                (string_to_evm_address('0x302b9286E831Ee6fEB9387978CFB4342c86Ef225'), 'grants 15 Unlock protocol round', A_UDT),  # UDT token # noqa: E501
            ],
            payout_claimed_matching_contracts1=[
                (string_to_evm_address('0xAB8d71d59827dcc90fEDc5DDb97f87eFfB1B1A5B'), 'grants 12 main round', A_DAI),  # noqa: E501
            ],
            payout_claimed_matching_contracts2=[
                (string_to_evm_address('0x0EbD2E2130b73107d0C45fF2E16c93E7e2e10e3a'), 'grants 11 main round', A_DAI),  # noqa: E501
                (string_to_evm_address('0x3ebAFfe01513164e638480404c651E885cCA0AA4'), 'grants 10 main round', A_DAI),  # noqa: E501
                (string_to_evm_address('0x3342E3737732D879743f2682A3953a730ae4F47C'), 'grants 9 main round', A_DAI),  # noqa: E501
                (string_to_evm_address('0xf2354570bE2fB420832Fb7Ff6ff0AE0dF80CF2c6'), 'grants 8 main round', A_DAI),  # noqa: E501
            ],
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
            context.event.notes = f'Donate {context.event.amount} {crypto_asset.symbol} to {to_address} via gitcoin'  # noqa: E501
        else:  # can only be RECEIVE
            from_address = context.event.address
            context.event.notes = f'Receive donation of {context.event.amount} {crypto_asset.symbol} from {from_address} via gitcoin'  # noqa: E501

        context.event.event_subtype = HistoryEventSubType.DONATE
        context.event.counterparty = CPT_GITCOIN
        return TransferEnrichmentOutput(matched_counterparty=CPT_GITCOIN)

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            GITCOIN_GOVERNOR_ALPHA: (self._decode_governance,),
        } | super().addresses_to_decoders()

    def enricher_rules(self) -> list[Callable]:
        return [
            self._maybe_enrich_gitcoin_transfers,
        ]
