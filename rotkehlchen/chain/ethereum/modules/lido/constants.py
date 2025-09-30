from typing import Final

from rotkehlchen.fval import FVal

CPT_LIDO: Final = 'lido'

LIDO_STETH_SUBMITTED: Final = b'\x96\xa2\\\x8c\xe0\xba\xab\xc1\xfd\xef\xd9>\x9e\xd2]\x8e\t*32\xf3\xaa\x9aAr+V\x97#\x1d\x1d\x1a'  # noqa: E501
LIDO_TRANSFER_SHARES: Final = b'\x9d\x9c\x90\x92\x96\xd9\xc6\x74\x45\x1c\x0c\x24\xf0\x2c\xb6\x49\x81\xeb\x3b\x72\x7f\x99\x86\x59\x39\x19\x2f\x88\x0a\x75\x5d\xcb'  # noqa: E501

# https://github.com/lidofinance/lido-dao/issues/442 . TODO: find constant we should use in the project. Temp 8 # noqa: E501
STETH_MAX_ROUND_ERROR_WEI: Final = FVal(8)
