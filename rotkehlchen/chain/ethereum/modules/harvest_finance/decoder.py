import logging
from typing import Any

from rotkehlchen.chain.evm.decoding.interfaces import MerkleClaimDecoderInterface
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

from .constants import CPT_HARVEST_FINANCE, GRAIN_TOKEN_ID, HARVEST_GRAIN_CLAIM

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
