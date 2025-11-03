from abc import ABC

from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import CLAIMED_TOPIC
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import DecoderContext
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address


class CliqueAirdropDecoderInterface(EvmDecoderInterface, ABC):
    """Decoders of protocols using clique airdrop claim"""

    def _decode_claim(self, context: DecoderContext) -> tuple[ChecksumEvmAddress, FVal] | None:
        """Just decode the claim part of a clique claim and return the amount and address"""
        if context.tx_log.topics[0] != CLAIMED_TOPIC:
            return None

        if not self.base.is_tracked(claiming_address := bytes_to_address(context.tx_log.topics[1])):  # noqa: E501
            return None

        claimed_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data),
            token_decimals=18,  # both omni and eigen have 18 decimals
        )
        return claiming_address, claimed_amount
