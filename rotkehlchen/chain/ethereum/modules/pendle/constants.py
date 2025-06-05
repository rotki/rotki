from typing import Final

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address

VE_PENDLE_CONTRACT_ADDRESS: Final = string_to_evm_address('0x4f30A9D41B80ecC5B94306AB4364951AE3170210')  # noqa: E501
PENDLE_TOKEN: Final = Asset('eip155:1/erc20:0x808507121B80c02388fAd14726482e061B8da827')
NEW_LOCK_POSITION_TOPIC: Final = b'\xb1\xa37\x19V\xc5M\xc1\xd86\x95\xb4\xa0\x06\xb0Q\xc81>\xe9\x86\xe53\xb6\xb9d\xe7|\x90f\xfc,'  # noqa: E501
WITHDRAW_TOPIC: Final = b'\x0e\x1b\xb0T\\\x1e\xbb\x9f\xb6\x80\xbd\xe75\x14\xe5r\x83\x1d\xe9;G\x9c\x08~\xc1\xefl5\xc3\xa1\x9f\xd6'  # noqa: E501
