from typing import Final

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address

VE_PENDLE_CONTRACT_ADDRESS: Final = string_to_evm_address('0x4f30A9D41B80ecC5B94306AB4364951AE3170210')  # noqa: E501
PENDLE_TOKEN: Final = Asset('eip155:1/erc20:0x808507121B80c02388fAd14726482e061B8da827')
