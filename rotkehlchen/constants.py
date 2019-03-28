from typing import cast

from rotkehlchen import typing
from rotkehlchen.assets import Asset
from rotkehlchen.fval import FVal

ETH_DAO_FORK_TS = 1469020840  # 2016-07-20 13:20:40 UTC
BTC_BCH_FORK_TS = 1501593374  # 2017-08-01 13:16:14 UTC

SUPPORTED_EXCHANGES = ['kraken', 'poloniex', 'bittrex', 'bitmex', 'binance']
ROTKEHLCHEN_SERVER_TIMEOUT = 5
ALL_REMOTES_TIMEOUT = 20

YEAR_IN_SECONDS = 31536000  # 60 * 60 * 24 * 365

S_EMPTYSTR = typing.EmptyStr('')

S_USD = typing.FiatAsset('USD')
S_EUR = typing.FiatAsset('EUR')
S_GBP = typing.FiatAsset('GBP')
S_JPY = typing.FiatAsset('JPY')
S_CNY = typing.FiatAsset('CNY')
S_CAD = typing.FiatAsset('CAD')
S_KRW = typing.FiatAsset('KRW')
FIAT_CURRENCIES = (S_USD, S_EUR, S_GBP, S_JPY, S_CNY, S_CAD, S_KRW)

S_ETC = 'ETC'
S_BCH = 'BCH'
S_BTC = 'BTC'
S_ETH = 'ETH'

A_BTC = Asset(S_BTC)
A_BCH = Asset(S_BCH)
S_BSV = cast(typing.NonEthTokenBlockchainAsset, 'BSV')
A_ETH = Asset(S_ETH)
A_ETC = Asset(S_ETC)
S_DATACOIN = cast(typing.NonEthTokenBlockchainAsset, 'DATAcoin')
S_XMR = cast(typing.NonEthTokenBlockchainAsset, 'XMR')
S_NANO = cast(typing.NonEthTokenBlockchainAsset, 'NANO')
S_RAIBLOCKS = cast(typing.NonEthTokenBlockchainAsset, 'XRB')
S_MLN_OLD = typing.EthToken('MLN (old)')
S_MLN_NEW = typing.EthToken('MLN (new)')
S_MLN = typing.EthToken('MLN')
S_YOYOW = cast(typing.NonEthTokenBlockchainAsset, 'YOYOW')
S_RDN = cast(typing.EthToken, 'RDN')
A_USD = Asset(S_USD)
A_EUR = Asset(S_EUR)

EV_BUY = typing.EventType('buy')
EV_SELL = typing.EventType('sell')
EV_TX_GAS_COST = typing.EventType('tx_gas_cost')
EV_ASSET_MOVE = typing.EventType('asset_movement')
EV_LOAN_SETTLE = typing.EventType('loan_settlement')
EV_INTEREST_PAYMENT = typing.EventType('interest_rate_payment')
EV_MARGIN_CLOSE = typing.EventType('margin_position_close')

CURRENCYCONVERTER_API_KEY = '7ad371210f296db27c19'


ZERO = FVal(0)

# Seconds for which cached api queries will be cached
# By default 10 minutes.
# TODO: Make configurable!
CACHE_RESPONSE_FOR_SECS = 600

# API URLS
KRAKEN_BASE_URL = 'https://api.kraken.com'
KRAKEN_API_VERSION = '0'
BINANCE_BASE_URL = 'https://api.binance.com/api/'
# KRAKEN_BASE_URL = 'http://localhost:5001/kraken'
# KRAKEN_API_VERSION = 'mock'
# BINANCE_BASE_URL = 'http://localhost:5001/binance/api/'
