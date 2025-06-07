from typing import Final

BLOCKCHAIN_INFO_BASE_URL: Final = 'https://blockchain.info'
BLOCKSTREAM_BASE_URL: Final = 'https://blockstream.info/api'
MEMPOOL_SPACE_BASE_URL: Final = 'https://mempool.space/api'

BLOCKSTREAM_MEMPOOL_TX_PAGE_LENGTH: Final = 25

# Combined with the tx id to create the event identifiers for bitcoin transactions.
BTC_EVENT_IDENTIFIER_PREFIX: Final = 'btc_'
