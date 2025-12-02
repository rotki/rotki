from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_LUSD

CPT_LIQUITY: Final = 'liquity'

BALANCE_UPDATE: Final = b'\xca#+Z\xbb\x98\x8cT\x0b\x95\x9f\xf6\xc3\xbf\xae>\x97\xff\xf9d\xfd\t\x8cP\x8f\x96\x13\xc0\xa6\xbf\x1a\x80'  # noqa: E501
ACTIVE_POOL: Final = string_to_evm_address('0xDf9Eb223bAFBE5c5271415C75aeCD68C21fE3D7F')
STABILITY_POOL: Final = string_to_evm_address('0x66017D22b0f8556afDd19FC67041899Eb65a21bb')
LIQUITY_STAKING: Final = string_to_evm_address('0x4f9Fbb3f1E99B56e0Fe2892e623Ed36A76Fc605d')
BORROWER_OPERATIONS: Final = string_to_evm_address('0x24179CD81c9e782A4096035f7eC97fB8B783e007')

STABILITY_POOL_GAIN_WITHDRAW: Final = b'QEr"\xeb\xca\x92\xc35\xc9\xc8n+\xaa\x1c\xc0\xe4\x0f\xfa\xa9\x08JQE)\x80\xd5\xba\x8d\xec/c'  # noqa: E501
STABILITY_POOL_LQTY_PAID_TO_DEPOSITOR: Final = b'&\x08\xb9\x86\xa6\xac\x0flb\x9c\xa3p\x18\xe8\n\xf5V\x1e6bR\xae\x93`*\x96\xd3\xab.s\xe4-'  # noqa: E501
STABILITY_POOL_LQTY_PAID_TO_FRONTEND: Final = b'\xcd,\xdc\x1aJ\xf7\x10Q9N\x9co\xac\xd9\xa2f\xb2\xac[\xd6]!\x9ap\x1e\xed\xa0\t\xf4v\x82\xbf'  # noqa: E501
STABILITY_POOL_EVENTS: Final = {STABILITY_POOL_GAIN_WITHDRAW, STABILITY_POOL_LQTY_PAID_TO_DEPOSITOR, STABILITY_POOL_LQTY_PAID_TO_FRONTEND}  # noqa: E501
STAKING_LQTY_CHANGE: Final = b'9\xdf\x0eR\x86\xa3\xef/B\xa0\xbfR\xf3,\xfe,X\xe5\xb0@_G\xfeQ/,$9\xe4\xcf\xe2\x04'  # noqa: E501
STAKING_ETH_SENT: Final = b'a\t\xe2U\x9d\xfavj\xae\xc7\x11\x83Q\xd4\x8aR?\nAW\xf4\x9c\x8dht\x9c\x8a\xc4\x13\x18\xad\x12'  # noqa: E501

STAKING_LQTY_EVENTS: Final = {STAKING_LQTY_CHANGE, STAKING_ETH_SENT}
LUSD_BORROWING_FEE_PAID: Final = b'\xa5\\_H\xfd)H*\xd5_KY\xbf\x07\x0c\xd1\xac\x1aq2\xa3\x1fz\x13n\xbe\x88w\xae7\xe1\xff'  # noqa: E501
STAKING_REWARDS_ASSETS: Final = {A_ETH, A_LUSD}

LIQUITY_V2_WRAPPER: Final = string_to_evm_address('0x807DEf5E7d057DF05C796F4bc75C3Fe82Bd6EeE1')
DEPOSIT_LQTY_V2: Final = b'\\\xd3x\x95\xbb\x92\x87\xe5B\xa4&\xd6\xab\xbc\x93\xd7\xda\xca\ty\xbdC&M2\rO\xd2$\xa5\xfc^'  # noqa: E501
WITHDRAW_LQTY_V2: Final = b"(p\xfe\x17uR\x97k\r\xbc1f\xde\xd2\x16\x9d]s'_\xc5e\xdf0\x89C \xfd6\x08\xf39"  # noqa: E501
DEPLOY_USER_PROXY_LQTY_V2: Final = b'\xdaf\xba#/O\xb8\xc1"\xb7\x02oU\xee\xff\x1d\x0b\x9c\xf2V\x0bxs\xb2\xbb\xa6\xea\xabL=Y\x89'  # noqa: E501
