import logging
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.chain.ethereum.airdrops import AIRDROP_IDENTIFIER_KEY
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import CLAIMED_TOPIC
from rotkehlchen.chain.evm.decoding.airdrops import match_airdrop_claim
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import DEFAULT_DECODING_OUTPUT
from rotkehlchen.chain.scroll.constants import CPT_SCROLL, SCROLL_CPT_DETAILS
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import bytes_to_address

from .constants import A_SCR, SCROLL_OFFCHAIN_TOKEN_DISTRIBUTOR, SCROLL_TOKEN_DISTRIBUTOR

if TYPE_CHECKING:
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext, DecodingOutput
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

EXECUTION_SUCCESS_TOPIC: Final = b"D.q_bcF\xe8\xc5C\x81\x00-\xa6\x14\xf6+\xee\x8d'8e5\xb2R\x1e\xc8T\x08\x98Un"  # noqa: E501


class ScrollAirdropDecoder(DecoderInterface):

    def _decode_airdop_claim(self, context: 'DecoderContext') -> 'DecodingOutput':
        """Decodes scroll SCR airdrop claim event."""
        if context.tx_log.topics[0] != CLAIMED_TOPIC:
            return DEFAULT_DECODING_OUTPUT

        user_address = bytes_to_address(context.tx_log.topics[1])
        amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[0:32]),
            asset=A_SCR.resolve_to_crypto_asset(),
        )
        for event in context.decoded_events:
            if match_airdrop_claim(
                event=event,
                user_address=user_address,
                amount=amount,
                asset=A_SCR,
                counterparty=CPT_SCROLL,
                airdrop_identifier='scroll',
            ):
                break
        else:
            log.error(f'Failed to find scroll airdrop claim event for {context.transaction}')

        return DEFAULT_DECODING_OUTPUT

    def _decode_scroll_batch_airdrop(
            self,
            context: 'DecoderContext',
    ) -> 'DecodingOutput':
        """Decodes SCR token airdrop claims from Scroll's offchain distributor.

        Handles batch distributions for GitHub/email-based claims that are processed
        periodically rather than instant on-chain claims.

        See https://scroll-faqs.gitbook.io/faq#23-when-will-i-receive-my-scr-tokens-after-claiming
        """
        if context.tx_log.topics[0] != EXECUTION_SUCCESS_TOPIC:
            return DEFAULT_DECODING_OUTPUT

        for event in context.decoded_events:
            if (
                    event.address == SCROLL_OFFCHAIN_TOKEN_DISTRIBUTOR and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.event_type == HistoryEventType.RECEIVE and
                    event.asset == A_SCR
            ):
                event.counterparty = CPT_SCROLL
                event.event_subtype = HistoryEventSubType.AIRDROP
                event.extra_data = {AIRDROP_IDENTIFIER_KEY: 'scroll'}
                event.notes = f'Receive {event.amount} SCR from scroll airdrop'

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return {
            SCROLL_TOKEN_DISTRIBUTOR: (self._decode_airdop_claim,),
            SCROLL_OFFCHAIN_TOKEN_DISTRIBUTOR: (self._decode_scroll_batch_airdrop,),
        }

    @staticmethod
    def counterparties() -> tuple['CounterpartyDetails', ...]:
        return (SCROLL_CPT_DETAILS,)
