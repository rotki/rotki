from rotkehlchen.fval import FVal
from rotkehlchen.typing import EmptyStr, EventType

S_EMPTYSTR = EmptyStr('')


EV_BUY = EventType('buy')
EV_SELL = EventType('sell')
EV_TX_GAS_COST = EventType('tx_gas_cost')
EV_ASSET_MOVE = EventType('asset_movement')
EV_LOAN_SETTLE = EventType('loan_settlement')
EV_INTEREST_PAYMENT = EventType('interest_rate_payment')
EV_MARGIN_CLOSE = EventType('margin_position_close')
EV_DEFI = EventType('defi_event')
EV_LEDGER_ACTION = EventType('ledger_action')

ZERO = FVal(0)
ONE = FVal(1)

PRICE_HISTORY_DIR = 'price_history'

# API URLS
KRAKEN_BASE_URL = 'https://api.kraken.com'
KRAKEN_API_VERSION = '0'
BINANCE_BASE_URL = 'binance.com/'
BINANCE_US_BASE_URL = 'binance.us/'
# KRAKEN_BASE_URL = 'http://localhost:5001/kraken'
# KRAKEN_API_VERSION = 'mock'
# BINANCE_BASE_URL = 'http://localhost:5001/binance/api/'
