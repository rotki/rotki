from typing import Final

CPT_GAS: Final = 'gas'
# How many logs of one transaction to decode before voluntarily releasing the GIL.
# Decoding a log is 0.1-1ms of pure Python, so this keeps GIL monopolies of huge
# transactions in the low milliseconds and lets concurrent DB readers (e.g. the
# history page) interleave instead of waiting out the switch interval per row.
MIN_LOGS_PROCESSED_TO_SLEEP: Final[int] = 25
