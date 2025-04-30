from typing import Final

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address

GEAR_STAKING_CONTRACT: Final = string_to_evm_address('0x8D2622f1CA3B42b637e2ff6753E6b69D3ab9Adfd')
GEAR_TOKEN_OPT: Final = Asset('eip155:10/erc20:0x39E6C2E1757ae4354087266E2C3EA9aC4257C1eb')
