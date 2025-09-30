import logging
from typing import Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.modules.eigenlayer.constants import EIGEN_TOKEN_ID
from rotkehlchen.chain.ethereum.modules.puffer.constants import (
    CPT_PUFFER,
    HEDGEY_DELEGATEDCLAIMS_CAMPAIGN,
    PUFFER_AIRDROP_S1_CAMPAIGN1,
    PUFFER_AIRDROP_S1_CAMPAIGN2,
    PUFFER_AIRDROP_S1_CAMPAIGN3,
    PUFFER_TOKEN_ID,
    PUFFERX_EIGEN_S2_AIRDROP1,
    PUFFERX_EIGEN_S2_AIRDROP2,
    UNLOCKED_TOKENS_CLAIMED,
)
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class PufferDecoder(EvmDecoderInterface):

    def _decode_unlockedtokens_claimed(self, context: DecoderContext) -> DecodingOutput:
        """Decode claiming unlocked tokens (airdrop) from puffer"""
        if context.tx_log.topics[0] != UNLOCKED_TOKENS_CLAIMED:
            return DEFAULT_DECODING_OUTPUT

        if not self.base.is_tracked(claimer := bytes_to_address(context.tx_log.topics[2])):
            return DEFAULT_DECODING_OUTPUT

        if (campaign_id := context.tx_log.topics[1][:16].hex()) in (PUFFERX_EIGEN_S2_AIRDROP1, PUFFERX_EIGEN_S2_AIRDROP2):  # noqa: E501
            asset_id = EIGEN_TOKEN_ID
            campaign_name = 'PufferXEigen S2 airdrop'
        elif campaign_id in (PUFFER_AIRDROP_S1_CAMPAIGN1, PUFFER_AIRDROP_S1_CAMPAIGN2, PUFFER_AIRDROP_S1_CAMPAIGN3):  # noqa: E501
            asset_id = PUFFER_TOKEN_ID
            campaign_name = 'Puffer S1 airdrop'
        else:
            log.error(f'Unknown Puffer delegated tokens campaign with id {campaign_id}. Skipping decoding ...')  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        claimed_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,  # both puffer and eigen got 18 decimals
        )
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.location_label == claimer and
                    event.asset.identifier == asset_id and
                    event.amount == claimed_amount
            ):
                event.event_subtype = HistoryEventSubType.AIRDROP
                event.counterparty = CPT_PUFFER
                event.notes = f'Claim {claimed_amount} {event.asset.resolve_to_asset_with_symbol().symbol} from {campaign_name}'  # noqa: E501
                break
        else:
            log.error(f'Could not find transfer event for a Puffer claim event at {context.transaction.tx_hash.hex()}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {  # The contract in question is for multiple delegated campaigns (https://hedgey.gitbook.io/hedgey-community-docs/for-developers/deployments/token-claims-claimcampaigns) and not only for puffer. If we see more of them we probably would need to abstract this better and out of here and have the protocol variable.  # noqa: E501
            HEDGEY_DELEGATEDCLAIMS_CAMPAIGN: (self._decode_unlockedtokens_claimed,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (
            CounterpartyDetails(
                identifier=CPT_PUFFER,
                label='Puffer',
                image='puffer.svg',
            ),
        )
