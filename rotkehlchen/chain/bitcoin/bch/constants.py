from typing import Final

HASKOIN_BASE_URL: Final = 'https://api.haskoin.com'

# With ~130 addresses it starts returning 414 (URI too long)
HASKOIN_BATCH_SIZE: Final = 100
