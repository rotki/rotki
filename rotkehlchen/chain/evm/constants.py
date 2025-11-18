import re
from typing import Final

from rotkehlchen.types import deserialize_evm_tx_hash

from .types import string_to_evm_address

DEFAULT_TOKEN_DECIMALS: Final = 18

ZERO_ADDRESS: Final = string_to_evm_address('0x0000000000000000000000000000000000000000')
ETH_SPECIAL_ADDRESS: Final = string_to_evm_address('0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE')
BALANCE_SCANNER_ADDRESS: Final = string_to_evm_address('0x54eCF3f6f61F63fdFE7c27Ee8A86e54899600C92')  # noqa: E501
ZERO_32_BYTES_HEX_NO_PREFIX: Final = '0' * 64
ZERO_32_BYTES_HEX: Final = '0x' + ZERO_32_BYTES_HEX_NO_PREFIX
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
STAKE_TOPIC: Final = b'\x90\x89\x08\t\xc6T\xf1\x1dnr\xa2\x8f\xa6\x01Iw\n\r\x11\xecl\x921\x9dl\xeb+\xb0\xa4\xea\x1a\x15'  # noqa: E501
REWARD_PAID_TOPIC: Final = b'T\x07\x98\xdfF\x8d{#\xd1\x1f\x15o\xdb\x95L\xb1\x9a\xd4\x14\xd1Pr*{mU\xba6\x9d\xeay.'  # noqa: E501
REWARD_PAID_TOPIC_V2: Final = b'\xe2@6@\xbah\xfe\xd3\xa2\xf8\x8buWU\x1d\x19\x93\xf8K\x99\xbb\x10\xff\x83?\x0c\xf8\xdb\x0c^\x04\x86'  # noqa: E501
WITHDRAWN_TOPIC: Final = b'\x92\xcc\xf4P\xa2\x86\xa9W\xafRP\x9b\xc1\xc9\x93\x9d\x1ajH\x17\x83\xe1B\xe4\x1e$\x99\xf0\xbbf\xeb\xc6'  # noqa: E501
WITHDRAW_TOPIC: Final = b'\x9b\x1b\xfa\x7f\xa9\xeeB\n\x16\xe1$\xf7\x94\xc3Z\xc9\xf9\x04r\xac\xc9\x91@\xeb/dG\xc7\x14\xca\xd8\xeb'  # noqa: E501
STAKED_TOPIC: Final = b']\xac\x0c\x1b\x11\x12VJ\x04[\xa9C\xc9\xd5\x02p\x89>\x8e\x82lI\xbe\x8eps\xad\xc7\x13\xab{\xd7'  # noqa: E501
WITHDRAW_TOPIC_V2: Final = b'\x88N\xda\xd9\xceo\xa2D\r\x8aT\xcc\x124\x90\xeb\x96\xd2v\x84y\xd4\x9f\xf9\xc76a%\xa9BCd'  # noqa: E501
WITHDRAW_TOPIC_V3: Final = b'\xfb\xdey} \x1ch\x1b\x91\x05e)\x11\x9e\x0b\x02@|{\xb9jJ,u\xc0\x1f\xc9fr2\xc8\xdb'  # noqa: E501
UNSTAKE_TOPIC: Final = b'\xf2y\xe6\xa1\xf5\xe3 \xcc\xa9\x115gm\x9c\xb6\xe4L\xa8\xa0\x8c\x0b\x884+\xcd\xb1\x14Oe\x11\xb5h'  # noqa: E501
ADD_LIQUIDITY_DYNAMIC_ASSETS: Final = b'\x18\x9cb;fk\x1bE\xb8=qx\xf3\x9b\x8c\x08|\xb0\x97t1|\xa2\xf5<-<7&\xf2"\xa2'  # noqa: E501
CLAIMED_TOPIC: Final = b'\xd8\x13\x8f\x8a?7|RY\xcaT\x8ep\xe4\xc2\xde\x94\xf1)\xf5\xa1\x106\xa1[iQ<\xba+Bj'  # noqa: E501
DEPOSIT_TOPIC: Final = b'\xdc\xbc\x1c\x05$\x0f1\xff:\xd0g\xef\x1e\xe3\\\xe4\x99wbu.:\tR\x84uED\xf4\xc7\t\xd7'  # noqa: E501
DEPOSIT_TOPIC_V2: Final = b'\xe1\xff\xfc\xc4\x92=\x04\xb5Y\xf4\xd2\x9a\x8b\xfcl\xda\x04\xeb[\r<F\x07Q\xc2@,\\\\\xc9\x10\x9c'  # noqa: E501
BURN_TOPIC: Final = b'\xdc\xcdA/\x0b\x12R\x81\x9c\xb1\xfd3\x0b\x93"L\xa4&\x12\x89+\xb3\xf4\xf7\x89\x97nm\x81\x93d\x96'  # noqa: E501
SWAPPED_TOPIC: Final = b'\xd6\xd4\xf5h\x1c$l\x9fB\xc2\x03\xe2\x87\x97Z\xf1`\x1f\x8d\xf8\x03Z\x92Q\xf7\x9a\xab\\\x8f\t\xe2\xf8'  # noqa: E501
MINT_TOPIC: Final = b'L \x9b_\xc8\xadPu\x8f\x13\xe2\xe1\x08\x8b\xa5jV\r\xffi\n\x1co\xef&9OL\x03\x82\x1cO'  # noqa: E501
STAKING_DEPOSIT: Final = b'\xf9C\xcf\x10\xefM\x1e29\xf4qm\xde\xcd\xf5F\xe8\xba\x8a\xb0\xe4\x1d\xea\xfd\x9aq\xa9\x996\x82~E'  # noqa: E501
REWARDS_CLAIMED_TOPIC: Final = b'V7\xd7\xf9b$\x8a\x7f\x05\xa7\xabi\xee\xc6Dn1\xf3\xd0\xa2\x99\xd9\x97\xf15\xa6\\b\x80nx\x91'  # noqa: E501
