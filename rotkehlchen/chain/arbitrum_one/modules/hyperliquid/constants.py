from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_HYPER: Final = 'hyperliquid'
BRIDGE_ADDRESS: Final = string_to_evm_address('0x2Df1c51E09aECF9cacB7bc98cB1742757f163dF7')
FINALIZE_WITHDRAWAL: Final = b'\xe5\xc7\xfe:O\xfc\xa1Y\x0f&\xd7L\x8b\xa8\xb0\xdbiU\x7f\x7fF\x07\xa2\xa4?\x82\xe90Aa\x19x'  # noqa: E501
