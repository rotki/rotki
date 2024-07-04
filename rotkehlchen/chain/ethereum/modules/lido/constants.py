from typing import Final

from rotkehlchen.fval import FVal

CPT_LIDO: Final = 'lido'

LIDO_STETH_SUBMITTED: Final = b'\x96\xa2\\\x8c\xe0\xba\xab\xc1\xfd\xef\xd9>\x9e\xd2]\x8e\t*32\xf3\xaa\x9aAr+V\x97#\x1d\x1d\x1a'  # noqa: E501

# https://github.com/lidofinance/lido-dao/issues/442 . TODO: find constant we should use in the project. Temp 8 # noqa: E501
STETH_MAX_ROUND_ERROR_WEI: Final = FVal(8)
