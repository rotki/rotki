from rotkehlchen.chain.ethereum.types import string_to_ethereum_address

MODULES_PACKAGE = 'rotkehlchen.chain.ethereum.modules'
MODULES_PREFIX = MODULES_PACKAGE + '.'
MODULES_PREFIX_LENGTH = len(MODULES_PREFIX)

ZERO_ADDRESS = string_to_ethereum_address('0x0000000000000000000000000000000000000000')

CPT_GAS = 'gas'
CPT_KRAKEN = 'kraken'
