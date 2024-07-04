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


OPTIMISM_AIRDROP = string_to_evm_address('0xFeDFAF1A10335448b7FA0268F56D2B44DBD357de')


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
            OPTIMISM_AIRDROP: (
                self._decode_merkle_claim,
                CPT_OPTIMISM,  # counterparty
                self.op_token.identifier,  # token id
                18,  # token decimals
                'OP from the optimism airdrop',  # notes suffix
                'optimism_1',
            ),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (OPTIMISM_CPT_DETAILS,)
