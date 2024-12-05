from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.types import ChainID

CPT_GIVETH: Final = 'giveth'
GIVPOWER_STAKING: Final = string_to_evm_address('0x301C739CF6bfb6B47A74878BdEB13f92F13Ae5E7')
GIV_DISTRO: Final = string_to_evm_address('0xE3Ac7b3e6B4065f4765d76fDC215606483BF3bD1')
GIV_TOKEN_ID: Final = 'eip155:10/erc20:0x528CDc92eAB044E1E39FE43B9514bfdAB4412B98'
GIVPOW_TOKEN_ID: Final = evm_address_to_identifier(
    address=GIVPOWER_STAKING,
    chain_id=ChainID.OPTIMISM,
)
