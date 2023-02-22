from rotkehlchen.types import deserialize_evm_tx_hash

from .types import string_to_evm_address

MAX_BLOCKTIME_CACHE = 250  # 55 mins with 13 secs avg block time
ZERO_ADDRESS = string_to_evm_address('0x0000000000000000000000000000000000000000')
ETH_SPECIAL_ADDRESS = string_to_evm_address('0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE')
ZERO_32_BYTES_HEX = '0x' + '0' * 64
GENESIS_HASH = deserialize_evm_tx_hash(ZERO_32_BYTES_HEX)  # hash for transactions in genesis block

# Fake receipt with values taken from ethereum mainnet, to emulate a receipt for the
# genesis transactions
FAKE_GENESIS_TX_RECEIPT = {
    'blockHash': ZERO_32_BYTES_HEX,
    'blockNumber': 0,
    'contractAddress': None,
    'cumulativeGasUsed': 21000,
    'effectiveGasPrice': 50000000000000,
    'from': ZERO_ADDRESS,
    'gasUsed': 21000,
    'logs': [],
    'logsBloom': '0x' + '0' * 512,
    'root': ZERO_32_BYTES_HEX,
    'to': ZERO_ADDRESS,
    'transactionHash': ZERO_32_BYTES_HEX,
    'transactionIndex': 0,
    'type': '0x0',
}
