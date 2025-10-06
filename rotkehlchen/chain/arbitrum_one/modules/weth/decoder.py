from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.structures import DEFAULT_EVM_DECODING_OUTPUT
from rotkehlchen.chain.evm.decoding.weth.decoder import WethDecoder as EthBaseWethDecoder
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext, EvmDecodingOutput


class WethDecoder(EthBaseWethDecoder):

    def _decode_wrapper(self, context: 'DecoderContext') -> 'EvmDecodingOutput':
        """WETH on Arbitrum is deployed as proxy, check for transfers to/from ZERO_ADDRESS."""
        if context.tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER:
            from_address = bytes_to_address(context.tx_log.topics[1])
            to_address = bytes_to_address(context.tx_log.topics[2])
            if from_address == ZERO_ADDRESS and self.base.is_tracked(to_address):
                return self._decode_deposit_event(context)
            elif to_address == ZERO_ADDRESS and self.base.is_tracked(from_address):
                return self._decode_withdrawal_event(context)

        return DEFAULT_EVM_DECODING_OUTPUT
