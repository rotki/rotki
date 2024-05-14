from abc import ABC

from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.decoding.clique.constants import CLIQUE_CLAIMED
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import DecoderContext
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int


class CliqueAirdropDecoderInterface(DecoderInterface, ABC):
    """Decoders of protocols using clique airdrop claim"""

    def _decode_claim(self, context: DecoderContext) -> tuple[ChecksumEvmAddress, FVal] | None:
        """Just decode the claim part of a clique claim and return the amount and address"""
        if context.tx_log.topics[0] != CLIQUE_CLAIMED:
            return None

        if not self.base.is_tracked(claiming_address := hex_or_bytes_to_address(context.tx_log.topics[1])):  # noqa: E501
            return None

        claimed_amount = token_normalized_value_decimals(
            token_amount=hex_or_bytes_to_int(context.tx_log.data),
            token_decimals=18,  # both omni and eigen have 18 decimals
        )
        return claiming_address, claimed_amount
