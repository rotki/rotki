from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

PARASWAP_AUGUSTUS_V6_ROUTER: Final = string_to_evm_address('0x6A000F20005980200259B80c5102003040001068')  # noqa: E501
PARASWAP_V6_FEE_CLAIMER: Final = string_to_evm_address('0x00700052c0608F670705380a4900e0a8080010CC')  # noqa: E501

PARASWAP_METHODS: Final = {
    b'\xe3\xea\xd5\x9e',  # swapExactAmountIn
    b'\xd8\\\xa1s',  # swapExactAmountInOnBalancerV2
    b'\x1a\x01\xc52',  # swapExactAmountInOnCurveV1
    b'\xe3~\xd2V',  # swapExactAmountInOnCurveV2
    b'\xe8\xbb;l',  # swapExactAmountInOnUniswapV2
    b'\x87j\x02\xf6',  # swapExactAmountInOnUniswapV3
    b'\x7fEvu',  # swapExactAmountOut
    b'\xd6\xed"\xe6',  # swapExactAmountOutOnBalancerV2
    b'\xa7oN\xb6',  # swapExactAmountOutOnUniswapV2
    b'^\x94\xe2\x8d',  # swapExactAmountOutOnUniswapV3
    b'\xda5\xbb\r',  # swapOnAugustusRFQTryBatchFill
}
