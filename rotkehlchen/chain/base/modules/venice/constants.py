from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_VENICE: Final = 'venice'
DIEM_BURNED: Final = (
    b'w\xe8\xc1`\x8e\x07\xb1\xa49_\xc9\x07@}bD\xa5\x0b\x86\xee'
    b'\xad\x91\x9f>\xe6\x1d\x8c\xe9\x9e K\xd6'
)
DIEM_MINTED: Final = (
    b'\xd0\x81\xa6I\xef/\x950I\x0e\x16\xb4\xffMn\x1f'
    b'FF\x0e\x01\x10}\x1e\xcf|Wl\xca<\xf9\xd3W'
)
DIEM_TOKEN_ID: Final = 'eip155:8453/erc20:0xF4d97F2da56e8c3098f3a8D538DB630A2606a024'
VENICE_AIRDROP_CONTRACT: Final = string_to_evm_address('0xf4940c7dEE63d885C8Fb20123e9C8e5c49a3Ef41')  # noqa: E501
VENICE_CLAIMED: Final = (
    b"R\x897\xb30\x08-\x89*\x98\xd4\xe4(\xab-\xcc\xa7\x84KQ\xd2'"
    b'\xa1\xc0\xaeg\xf0\xb5&\x1a\xcb\xd9'
)
VENICE_STAKING_CONTRACT: Final = string_to_evm_address('0x321b7ff75154472B18EDb199033fF4D116F340Ff')  # noqa: E501
VENICE_STAKING_REWARD_CLAIMED: Final = (
    b'\xd8\x13\x8f\x8a?7|RY\xcaT\x8ep\xe4\xc2\xde\x94\xf1)'
    b'\xf5\xa1\x106\xa1[iQ<\xba+Bj'
)
SVVV_TOKEN_ID: Final = 'eip155:8453/erc20:0x321b7ff75154472B18EDb199033fF4D116F340Ff'
VVV_TOKEN_ID: Final = 'eip155:8453/erc20:0xacfE6019Ed1A7Dc6f7B508C02d1b04ec88cC21bf'
