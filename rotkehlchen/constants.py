from typing import cast
from rotkehlchen import typing

ETH_DAO_FORK_TS = 1469020840  # 2016-07-20 13:20:40 UTC
BTC_BCH_FORK_TS = 1501593374  # 2017-08-01 13:16:14 UTC

SUPPORTED_EXCHANGES = ['kraken', 'poloniex', 'bittrex', 'binance','bitmex']
ROTKEHLCHEN_SERVER_TIMEOUT = 5
ALL_REMOTES_TIMEOUT = 20

YEAR_IN_SECONDS = 31536000  # 60 * 60 * 24 * 365

S_EMPTYSTR = typing.EmptyStr('')

S_BTC = cast(typing.NonEthTokenBlockchainAsset, 'BTC')
S_ETH = cast(typing.NonEthTokenBlockchainAsset, 'ETH')
S_DATACOIN = cast(typing.NonEthTokenBlockchainAsset, 'DATAcoin')

S_RDN = cast(typing.EthToken, 'RDN')


S_USD = typing.FiatAsset('USD')
S_EUR = typing.FiatAsset('EUR')
S_GBP = typing.FiatAsset('GBP')
S_JPY = typing.FiatAsset('JPY')
S_CNY = typing.FiatAsset('CNY')
FIAT_CURRENCIES = (S_USD, S_EUR, S_GBP, S_JPY, S_CNY)

EV_BUY = typing.EventType('buy')
EV_SELL = typing.EventType('sell')
EV_TX_GAS_COST = typing.EventType('tx_gas_cost')
EV_ASSET_MOVE = typing.EventType('asset_movement')
EV_LOAN_SETTLE = typing.EventType('loan_settlement')
EV_INTEREST_PAYMENT = typing.EventType('interest_rate_payment')
EV_MARGIN_CLOSE = typing.EventType('margin_position_close')
