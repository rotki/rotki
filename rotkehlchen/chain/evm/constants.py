import re
from typing import Final

from rotkehlchen.types import deserialize_evm_tx_hash

from .types import string_to_evm_address

DEFAULT_TOKEN_DECIMALS: Final = 18

ZERO_ADDRESS: Final = string_to_evm_address('0x0000000000000000000000000000000000000000')
ETH_SPECIAL_ADDRESS: Final = string_to_evm_address('0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE')
BALANCE_SCANNER_ADDRESS: Final = string_to_evm_address('0x54eCF3f6f61F63fdFE7c27Ee8A86e54899600C92')  # noqa: E501
ZERO_32_BYTES_HEX: Final = '0x' + '0' * 64
GENESIS_HASH: Final = deserialize_evm_tx_hash(ZERO_32_BYTES_HEX)  # hash for transactions in genesis block # noqa: E501
EVM_ADDRESS_REGEX: Final = re.compile(r'\b0x[a-fA-F0-9]{40}\b')
LAST_SPAM_TXS_CACHE: Final = 'SPAM_TXS'

# Fake receipt with values taken from ethereum mainnet, to emulate a receipt for the
# genesis transactions
FAKE_GENESIS_TX_RECEIPT: Final = {
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

ERC20_PROPERTIES: Final = ('decimals', 'symbol', 'name')
ERC20_PROPERTIES_NUM: Final = len(ERC20_PROPERTIES)
ERC721_PROPERTIES: Final = ('symbol', 'name')

# uniswap like merkle distributor claimed signature
MERKLE_CLAIM: Final = b'N\xc9\x0e\x96U\x19\xd9&\x81&tg\xf7u\xad\xa5\xbd!J\xa9,\r\xc9=\x90\xa5\xe8\x80\xce\x9e\xd0&'  # noqa: E501
# simple claim for address and amount used by multiple protocols
SIMPLE_CLAIM: Final = b'G\xce\xe9|\xb7\xac\xd7\x17\xb3\xc0\xaa\x145\xd0\x04\xcd[<\x8cW\xd7\r\xbc\xebNDX\xbb\xd6\x0e9\xd4'  # noqa: E501
