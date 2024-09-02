from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.evm.decoding.structures import DEFAULT_DECODING_OUTPUT
from rotkehlchen.chain.evm.decoding.weth.decoder import WethDecoder as EthBaseWethDecoder

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext, DecodingOutput


WETH_DEPOSIT_METHOD: Final = b'\xd0\xe3\r\xb0'
WETH_WITHDRAW_METHOD: Final = b'.\x1a}M'


class WethDecoder(EthBaseWethDecoder):

    def _decode_wrapper(self, context: 'DecoderContext') -> 'DecodingOutput':
        """WETH on Arbitrum is deployed as proxy, we need to check the method"""
        if (input_data := context.transaction.input_data).startswith(WETH_DEPOSIT_METHOD):
            return self._decode_deposit_event(context)
        elif input_data.startswith(WETH_WITHDRAW_METHOD):
            return self._decode_withdrawal_event(context)

        return DEFAULT_DECODING_OUTPUT
