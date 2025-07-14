from typing import Final

HASKOIN_BASE_URL: Final = 'https://api.haskoin.com'

# With ~130 addresses it starts returning 414 (URI too long)
HASKOIN_BATCH_SIZE: Final = 100

# Combined with the tx id to create the event identifiers for bitcoin cash transactions.
BCH_EVENT_IDENTIFIER_PREFIX: Final = 'bch_'
