from typing import Final

HASKOIN_BASE_URL: Final = 'https://api.haskoin.com'
BLOCKCHAIN_INFO_HASKOIN_BASE_URL: Final = 'https://api.blockchain.info/haskoin-store'
MELROY_BASE_URL: Final = 'https://explorer.melroy.org/api'

# Number of txs returned per request. The docs mention 25, but 10 is the actual number returned.
MELROY_TX_PAGE_SIZE: Final = 10

# With ~130 addresses it starts returning 414 (URI too long)
HASKOIN_BATCH_SIZE: Final = 100

# Combined with the tx id to create the event identifiers for bitcoin cash transactions.
BCH_EVENT_IDENTIFIER_PREFIX: Final = 'bch_'
