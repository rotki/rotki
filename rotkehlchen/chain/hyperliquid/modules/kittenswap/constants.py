from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from eth_typing import ABI

CPT_KITTENSWAP: Final = 'kittenswap'
KITTENSWAP_FACTORY: Final = string_to_evm_address('0x5f95E92c338e6453111Fc55ee66D4AafccE661A7')
KITTENSWAP_FACTORY_ABI: Final[ABI] = [{
    'inputs': [
        {'name': 'tokenA', 'type': 'address'},
        {'name': 'tokenB', 'type': 'address'},
    ],
    'name': 'poolByPair',
    'outputs': [{'name': 'pool', 'type': 'address'}],
    'stateMutability': 'view',
    'type': 'function',
}]
KITTENSWAP_POOL_ABI: Final[ABI] = [{
    'inputs': [],
    'name': method_name,
    'outputs': [{'name': '', 'type': output_type}],
    'stateMutability': 'view',
    'type': 'function',
} for method_name, output_type in (
    ('factory', 'address'),
    ('token0', 'address'),
    ('token1', 'address'),
)]
