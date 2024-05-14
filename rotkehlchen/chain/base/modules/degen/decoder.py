from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.base.modules.degen.constants import (
    CLAIM_AIRDROP_2_CONTRACT,
    CLAIM_AIRDROP_3_CONTRACT,
    CPT_DEGEN,
    DEGEN_TOKEN_ID,
)
from rotkehlchen.chain.evm.decoding.interfaces import MerkleClaimDecoderInterface
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails

if TYPE_CHECKING:
    from rotkehlchen.types import ChecksumEvmAddress


class DegenDecoder(MerkleClaimDecoderInterface):
    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return {
            CLAIM_AIRDROP_2_CONTRACT: (
                self._decode_indexed_merkle_claim,
                CPT_DEGEN,  # counterparty
                DEGEN_TOKEN_ID,  # token id
                18,  # token decimals
                'DEGEN from Degen airdrop 2',  # notes suffix
            ),
            CLAIM_AIRDROP_3_CONTRACT: (
                self._decode_indexed_merkle_claim,
                CPT_DEGEN,  # counterparty
                DEGEN_TOKEN_ID,  # token id
                18,  # token decimals
                'DEGEN from Degen airdrop 3',  # notes suffix
            ),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_DEGEN,
            label='Degen',
            image='degen.svg',
        ),)
