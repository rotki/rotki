
import re
from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address


POOL_ADDRESS: Final = string_to_evm_address('0x794a61358D6845594F94dc1DB02A252b5b4814aD')
AAVE_V3_DATA_PROVIDER: Final = string_to_evm_address('0x69FA688f1Dc47d4B5d8029D5a35FB7a548310654')
DEPOSIT: Final = b'+bw6\xbc\xa1\\\xd58\x1d\xcf\x80\xb0\xbf\x11\xfd\x19}\x01\xa07\xc5+\x92z\x88\x1a\x10\xfbs\xbaa'  # noqa: E501
BORROW: Final = b'\xb3\xd0\x84\x82\x0f\xb1\xa9\xde\xcf\xfb\x17d6\xbd\x02U\x8d\x15\xfa\xc9\xb0\xdd\xfe\xd8\xc4e\xbcsY\xd7\xdc\xe0'  # noqa: E501
REPAY: Final = b'\xa54\xc8\xdb\xe7\x1f\x87\x1f\x9f50\xe9zt`\x1f\xea\x17\xb4&\xca\xe0.\x1cZ\xeeB\xc9lx@Q'  # noqa: E501
BURN: Final = b'L\xf2[\xc1\xd9\x91\xc1u)\xc2R\x13\xd3\xcc\x0c\xda)^\xea\xad_\x13\xf3a\x96\x9b\x12\xeaH\x01_\x90'  # noqa: E501
DEBT_TOKEN_SYMBOL_REGEX: Final = re.compile(r'^(stableDebt|variableDebt)\w+$')
