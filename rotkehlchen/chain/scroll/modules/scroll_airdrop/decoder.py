import logging
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.airdrops import match_airdrop_claim
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import DEFAULT_DECODING_OUTPUT
from rotkehlchen.chain.scroll.constants import CPT_SCROLL, SCROLL_CPT_DETAILS
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import bytes_to_address

from .constants import A_SCR, SCROLL_TOKEN_DISTRIBUTOR

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext, DecodingOutput
    from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

CLAIMED_TOPIC: Final = b'\xd8\x13\x8f\x8a?7|RY\xcaT\x8ep\xe4\xc2\xde\x94\xf1)\xf5\xa1\x106\xa1[iQ<\xba+Bj'  # noqa: E501


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

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return {SCROLL_TOKEN_DISTRIBUTOR: (self._decode_airdop_claim,)}

    @staticmethod
    def counterparties() -> tuple['CounterpartyDetails', ...]:
        return (SCROLL_CPT_DETAILS,)
