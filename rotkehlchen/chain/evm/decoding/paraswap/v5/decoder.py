from abc import ABC
from collections.abc import Callable
from typing import Any

from rotkehlchen.chain.evm.decoding.paraswap.decoder import ParaswapCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.uniswap.v2.constants import UNISWAP_V2_SWAP_SIGNATURE
from rotkehlchen.chain.evm.decoding.uniswap.v3.constants import DIRECT_SWAP_SIGNATURE
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    BUY_ON_UNISWAP_V2_FORK,
    BUY_SIGNATURE,
    SWAP_ON_UNISWAP_V2_FACTORY,
    SWAP_ON_UNISWAP_V2_FORK,
    SWAP_ON_UNISWAP_V2_FORK_WITH_PERMIT,
    SWAP_SIGNATURE as PARASWAP_SWAP_SIGNATURE,
)


class Paraswapv5CommonDecoder(ParaswapCommonDecoder, ABC):

    def _decode_paraswap_swap(self, context: DecoderContext) -> DecodingOutput:
        """This decodes the following types of trades:
        - Simple Buy
        - Simple Swap
        - Multi Swap
        - Mega Swap
        - Direct Swap on Uniswap V3
        - Direct Swap on Curve V1 and V2
        - Direct Swap on Balancer V2
        """
        if context.tx_log.topics[0] not in {PARASWAP_SWAP_SIGNATURE, BUY_SIGNATURE, DIRECT_SWAP_SIGNATURE}:  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        return self._decode_swap(
            context=context,
            receiver=bytes_to_address(context.tx_log.topics[1]),
            sender=bytes_to_address(context.tx_log.data[96:128]),
        )

    def _decode_uniswap_v2_swap(self, context: DecoderContext) -> DecodingOutput:
        """This decodes swaps done directly on Uniswap V2 pools"""
        return self._decode_swap(
            context=context,
            receiver=bytes_to_address(context.tx_log.topics[2]),
            sender=context.transaction.from_address,
        )

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {self.router_address: (self._decode_paraswap_swap,)}

    def decoding_by_input_data(self) -> dict[bytes, dict[bytes, Callable]]:
        return {
            method_id: {UNISWAP_V2_SWAP_SIGNATURE: self._decode_uniswap_v2_swap}
            for method_id in (
                SWAP_ON_UNISWAP_V2_FORK,
                SWAP_ON_UNISWAP_V2_FACTORY,
                SWAP_ON_UNISWAP_V2_FORK_WITH_PERMIT,
                BUY_ON_UNISWAP_V2_FORK,
            )
        }
