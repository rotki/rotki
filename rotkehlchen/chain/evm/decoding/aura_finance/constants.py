from typing import Final

from eth_typing import ABI

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID

CPT_AURA_FINANCE: Final = 'aura-finance'

CHAIN_ID_TO_BOOSTER_ADDRESSES: Final = {
    ChainID.BASE: string_to_evm_address('0x98Ef32edd24e2c92525E59afc4475C1242a30184'),
    ChainID.GNOSIS: string_to_evm_address('0x98Ef32edd24e2c92525E59afc4475C1242a30184'),
    ChainID.ETHEREUM: string_to_evm_address('0xA57b8d98dAE62B26Ec3bcC4a365338157060B234'),
    ChainID.OPTIMISM: string_to_evm_address('0x98Ef32edd24e2c92525E59afc4475C1242a30184'),
    ChainID.POLYGON_POS: string_to_evm_address('0x98Ef32edd24e2c92525E59afc4475C1242a30184'),
    ChainID.ARBITRUM_ONE: string_to_evm_address('0x98Ef32edd24e2c92525E59afc4475C1242a30184'),
}

AURA_BOOSTER_ABI: ABI = [
  {
    'inputs': [
      {
        'name': '',
        'type': 'uint256',
      },
    ],
    'name': 'poolInfo',
    'outputs': [
      {
        'name': 'lptoken',
        'type': 'address',
      },
      {
        'name': 'token',
        'type': 'address',
      },
      {
        'name': 'gauge',
        'type': 'address',
      },
      {
        'name': 'crvRewards',
        'type': 'address',
      },
      {
        'name': 'stash',
        'type': 'address',
      },
      {
        'name': 'shutdown',
        'type': 'bool',
      },
    ],
    'stateMutability': 'view',
    'type': 'function',
  },
    {
    'inputs': [],
    'name': 'poolLength',
    'outputs': [
      {
        'name': '',
        'type': 'uint256',
      },
    ],
    'stateMutability': 'view',
    'type': 'function',
  },
]
