from typing import Final

BLOCKCHAIN_INFO_BASE_URL: Final = 'https://blockchain.info'
BLOCKCYPHER_BASE_URL: Final = 'https://api.blockcypher.com/v1/btc/main'
BLOCKSTREAM_BASE_URL: Final = 'https://blockstream.info/api'
MEMPOOL_SPACE_BASE_URL: Final = 'https://mempool.space/api'

BLOCKCYPHER_TX_IO_LIMIT: Final = 200
BLOCKCYPHER_TX_LIMIT: Final = 50

# This is rather small as the free rate limit is 3 requests/sec, with each batched item counting
# as a single request. This would appear to mean that there could be 3 batched items, but from
# actual testing it seems only 2 work correctly, so apparently the actual request being made
# is counted as an additional request above the number of items batched.
# See https://www.blockcypher.com/dev/bitcoin/#rate-limits-and-tokens
BLOCKCYPHER_BATCH_SIZE: Final = 2

# Combined with the tx id to create the event identifiers for bitcoin transactions.
BTC_EVENT_IDENTIFIER_PREFIX: Final = 'btc_'
