from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import Asset

A_SCR: Final = Asset('eip155:534352/erc20:0xd29687c813D741E2F938F4aC377128810E217b1b')
SCROLL_TOKEN_DISTRIBUTOR: Final = string_to_evm_address('0xE8bE8eB940c0ca3BD19D911CD3bEBc97Bea0ED62')  # noqa: E501
SCROLL_OFFCHAIN_TOKEN_DISTRIBUTOR: Final = string_to_evm_address('0x3b04F9398Ce7aBa9e34a789dC5632002A3Dc9953')  # noqa: E501
