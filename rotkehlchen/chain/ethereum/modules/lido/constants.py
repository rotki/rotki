from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.fval import FVal

CPT_LIDO: Final = 'lido'
WITHDRAWAL_QUEUE: Final = string_to_evm_address('0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1')

LIDO_STETH_SUBMITTED: Final = b'\x96\xa2\\\x8c\xe0\xba\xab\xc1\xfd\xef\xd9>\x9e\xd2]\x8e\t*32\xf3\xaa\x9aAr+V\x97#\x1d\x1d\x1a'  # noqa: E501
LIDO_STETH_TRANSFER_SHARES: Final = b'\x9d\x9c\x90\x92\x96\xd9\xc6tE\x1c\x0c$\xf0,\xb6I\x81\xeb;r\x7f\x99\x86Y9\x19/\x88\nu]\xcb'  # noqa: E501
LIDO_WITHDRAWAL_REQUESTED: Final = b'\xf0\xcbG\x1f#\xfbt\xeaD\xb8%.\xb1\x88\x1a-\xcaTb\x88\xd9\xf6\xe9\r\x1a\x0e\x82\xfe\x0e\xd3B\xab'  # noqa: E501
LIDO_WITHDRAWAL_CLAIMED: Final = b"j\xd2l^#\x8e}\x00'\x99\xf9\xa5\xdb\x07\xe8\x1e\xf1N78j\xe04\x96\xd7\xa7\xef\x04q>\x14["  # noqa: E501

# https://github.com/lidofinance/lido-dao/issues/442 . TODO: find constant we should use in the project. Temp 8 # noqa: E501
STETH_MAX_ROUND_ERROR_WEI: Final = FVal(8)
