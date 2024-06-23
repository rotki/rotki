from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

GITCOIN_GOVERNOR_ALPHA: Final = string_to_evm_address('0xDbD27635A534A3d3169Ef0498beB56Fb9c937489')
GITCOIN_GRANTS_OLD1: Final = string_to_evm_address('0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE')
GITCOIN_GRANTS_BULKCHECKOUT: Final = string_to_evm_address('0x7d655c57f71464B6f83811C55D84009Cd9f5221C')  # noqa: E501

DONATION_SENT: Final = b';\xb7B\x8b%\xf9\xbd\xad\x9b\xd2\xfa\xa4\xc6\xa7\xa9\xe5\xd5\x88&W\xe9l\x1d$\xccA\xc1\xd6\xc1\x91\n\x98'  # noqa: E501
