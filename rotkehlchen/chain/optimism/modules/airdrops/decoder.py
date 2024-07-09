from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.evm.decoding.constants import OPTIMISM_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.interfaces import MerkleClaimDecoderInterface
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.constants import CPT_OPTIMISM
from rotkehlchen.constants.assets import A_OP
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator


OPTIMISM_AIRDROP_1 = string_to_evm_address('0xFeDFAF1A10335448b7FA0268F56D2B44DBD357de')
OPTIMISM_AIRDROP_4 = string_to_evm_address('0xFb4D5A94b516DF77Fbdbcf3CfeB262baAF7D4dB7')


class AirdropsDecoder(MerkleClaimDecoderInterface):

    def __init__(
            self,
            optimism_inquirer: 'OptimismInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=optimism_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.op_token = A_OP.resolve_to_evm_token()

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            distributor_address: (
                self._decode_merkle_claim,
                CPT_OPTIMISM,  # counterparty
                self.op_token.identifier,  # token id
                18,  # token decimals
                f'OP from the optimism airdrop {note_suffix}',  # notes suffix
                airdrop_identifier,
            )
            for airdrop_identifier, distributor_address, note_suffix in (
                ('optimism_1', OPTIMISM_AIRDROP_1, '1'),
                ('optimism_4', OPTIMISM_AIRDROP_4, '4'),
            )
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (OPTIMISM_CPT_DETAILS,)
