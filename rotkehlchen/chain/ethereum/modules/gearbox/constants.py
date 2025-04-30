from typing import Final

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address

GEAR_STAKING_CONTRACT: Final = string_to_evm_address('0x2fcbD02d5B1D52FC78d4c02890D7f4f47a459c33')
GEAR_TOKEN: Final = Asset('eip155:1/erc20:0xBa3335588D9403515223F109EdC4eB7269a9Ab5D')
