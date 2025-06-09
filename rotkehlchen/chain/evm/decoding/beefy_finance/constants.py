from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID, ChecksumEvmAddress

CPT_BEEFY_FINANCE: Final = 'beefy_finance'
TOKEN_RETURNED_TOPIC: Final = b'\xea\xf4I1\x9c\x04,\x9b\xa3GO\xa0\xc52\x9e\xb5\x8c\xd1\xf2;\xe1\x10\xcd\xbf\x9di{\x8d0=\xac\x15'  # noqa: E501

# Data is retrieved from: https://github.com/beefyfinance/beefy-v2/blob/56a9ad002f97b1dbda04cf900aaba0aa04e3b378/src/config/zap/zaps.json
SUPPORTED_BEEFY_CHAINS: Final[dict[ChainID, ChecksumEvmAddress]] = {
    ChainID.ARBITRUM_ONE: string_to_evm_address('0xf49F7bB6F4F50d272A0914a671895c4384696E5A'),
    ChainID.ETHEREUM: string_to_evm_address('0x5Cc9400FfB4Da168Cf271e912F589462C3A00d1F'),
    ChainID.BASE: string_to_evm_address('0x6F19Da51d488926C007B9eBaa5968291a2eC6a63'),
    ChainID.SCROLL: string_to_evm_address('0x75c9D65e7C0d6b40F356452f8A11aeD525B67197'),
    ChainID.POLYGON_POS: string_to_evm_address('0xE90053b8136f18206fcf4F48E0C3B6AeD9b1aD71'),
    ChainID.OPTIMISM: string_to_evm_address('0xE82343A116d2179F197111D92f9B53611B43C01c'),
    ChainID.BINANCE_SC: string_to_evm_address('0x1C482130A1205213ad130404221Dc9b5350Fe4BD'),
    ChainID.GNOSIS: string_to_evm_address('0x992Ccc9D9b8b76310E044660E96171116820F019'),
}
