from typing import Final

from eth_typing import ABI

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_UMAMI: Final = 'umami'
UMAMI_STAKING_CONTRACT: Final = string_to_evm_address('0x52F6159dCAE4CE617A3d50aEb7fAB617526d9D8F')
UMAMI_MASTERCHEF_ABI: ABI = [
    {
        'inputs': [
            {
                'name': '',
                'type': 'uint256',
            },
            {
                'name': '',
                'type': 'address',
            },
        ],
        'name': 'userInfo',
        'outputs': [
            {
                'name': 'amount',
                'type': 'uint256',
            },
            {
                'name': 'rewardDebt',
                'type': 'uint256',
            },
        ],
        'stateMutability': 'view',
        'type': 'function',
    },
]
