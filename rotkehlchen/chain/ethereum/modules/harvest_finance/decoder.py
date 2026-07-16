import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.interfaces import MerkleClaimDecoderInterface
from rotkehlchen.logging import RotkehlchenLogsAdapter

from .constants import CPT_HARVEST_FINANCE, GRAIN_TOKEN_ID, HARVEST_GRAIN_CLAIM

if TYPE_CHECKING:
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class HarvestFinanceDecoder(MerkleClaimDecoderInterface):

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            HARVEST_GRAIN_CLAIM: (
                self._decode_merkle_claim,
                CPT_HARVEST_FINANCE,  # counterparty
                GRAIN_TOKEN_ID,  # token id
                18,  # token decimals
                'GRAIN from the harvest finance hack compensation airdrop',  # notes suffix
                'grain',
            ),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_HARVEST_FINANCE,
            label='Harvest Finance',
            image='harvest.svg',
        ),)
