from rotkehlchen.types import deserialize_evm_tx_hash

from .types import string_to_evm_address

MAX_BLOCKTIME_CACHE = 250  # 55 mins with 13 secs avg block time
ZERO_ADDRESS = string_to_evm_address('0x0000000000000000000000000000000000000000')
ETH_SPECIAL_ADDRESS = string_to_evm_address('0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE')
GENESIS_HASH = deserialize_evm_tx_hash('0x' + '0' * 64)  # hash for transactions in genesis block
