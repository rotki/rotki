from typing import Final

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address

GEAR_STAKING_CONTRACT: Final = string_to_evm_address('0xf3599BEfe8E79169Afd5f0b7eb0A1aA322F193D9')
GEAR_TOKEN_ARB: Final = Asset('eip155:42161/erc20:0x2F26337576127efabEEc1f62BE79dB1bcA9148A4')
