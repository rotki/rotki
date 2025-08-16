from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_EXTRAFI: Final = 'extrafi'
VOTE_ESCROW: Final = string_to_evm_address('0xe0BeC4F45aEF64CeC9dCB9010d4beFfB13e91466')
EXTRAFI_FARMING_CONTRACT = string_to_evm_address('0xf9cFB8a62f50e10AdDE5Aa888B44cF01C5957055')
EXTRAFI_DISTRIBUTOR: Final = string_to_evm_address('0xB7D8613728efCfbB18bCD63dEeC06F64441D322a')
EXTRAFI_POOL_CONTRACT: Final = string_to_evm_address('0xBB505c54D71E9e599cB8435b4F0cEEc05fC71cbD')
EXTRAFI_STAKING_CONTRACT: Final = string_to_evm_address('0x78D49Baa0FaE8CfB1CA2e51B2eA5C03fDdDFa4D5')  # noqa: E501

DEPOSITED: Final = b'\x80\xdb\xbd\xe6\xb5\xd5\xb7v#\x17\xd4\x9ewl\xfeG&\x9bn9,\xfd\xc7e@\xb0\xcd\xe8\xc8*#\xce'  # noqa: E501
REDEEM: Final = b'\x9d\x01\xc3\x05\xbdc~?\xd8]z\xba\xf4X\x8e\xfd\xd3p\x00\xdaGz0>\xaa\xa4\xfb\xc4Q\x02\x13\xd9'  # noqa: E501
CLAIM: Final = b'\xd6\xcd\n\xf7\xb90\x15\xe7\x04\x9cH\xebE\x10\xc3\xad&<36\xa6\xbf3(\x86\xe9\xe7\xf1R\xd4\x9a-'  # noqa: E501
USER_CHECKPOINT: Final = b'\x14]f\xd9\x1f\x92\xd1\xa0b\xbfr6\xac`h\xacu\xf0\x83\x01\xbd\xbewn:\x87u\x13nHj\xa8'  # noqa: E501
EXACT_REPAY: Final = b'\xa4\xbcT\x1a\x91S\xac\xe6\xa2\x9c,?I%G\xca\x7f \xec\xcb\xbf\xabV\x0f\xae}d\xbf\x91\xb49\xf6'  # noqa: E501
CLOSE_POSITION_PARTIALLY: Final = b"\xcaSh\x8fG\tB\xa5\x8en'r\xcd\xb6b\xda\x92m>%\xfa\xed\xceZ\x1diD\xf6\xbf\x1b\xc0\xcb"  # noqa: E501
INVEST_TO_VAULT_POSITION: Final = b'\x1cz\x199$\xce\x89\xc0\x97\xe2L,V:\xe4\x05\x93\xa6\xa6M\xf2\xa8SO\xdd\x99(c1\xfa\x97\x00'  # noqa: E501
