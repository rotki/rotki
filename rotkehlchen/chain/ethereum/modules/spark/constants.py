from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

SPARK_DATA_PROVIDER: Final = string_to_evm_address('0xFc21d6d146E6086B8359705C8b28512a983db0cb')
SPARK_AIRDROP_DISTRIBUTOR: Final = string_to_evm_address(
    '0xCBA0C0a2a0B6Bb11233ec4EA85C5bFfea33e724d',
)
SPARK_STAKE_TOKEN: Final = string_to_evm_address('0xc6132FAF04627c8d05d6E759FAbB331Ef2D8F8fD')
