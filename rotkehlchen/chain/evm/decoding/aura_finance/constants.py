from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from eth_typing import ABI

CPT_AURA_FINANCE: Final = 'aura-finance'

AURA_BOOSTER_ABI: Final[ABI] = [
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
