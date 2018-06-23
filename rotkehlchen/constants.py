from typing import cast
from rotkehlchen import typing

ETH_DAO_FORK_TS = 1469020840  # 2016-07-20 13:20:40 UTC
BTC_BCH_FORK_TS = 1501593374  # 2017-08-01 13:16:14 UTC

SUPPORTED_EXCHANGES = ['kraken', 'poloniex', 'bittrex', 'binance']
ROTKEHLCHEN_SERVER_TIMEOUT = 5
ALL_REMOTES_TIMEOUT = 20

YEAR_IN_SECONDS = 31536000  # 60 * 60 * 24 * 365

S_BTC = cast(typing.NonEthTokenBlockchainAsset, 'BTC')
S_ETH = cast(typing.NonEthTokenBlockchainAsset, 'ETH')
S_DATACOIN = cast(typing.NonEthTokenBlockchainAsset, 'DATAcoin')

S_RDN = cast(typing.EthToken, 'RDN')


S_USD = cast(typing.FiatAsset, 'USD')
S_EUR = cast(typing.FiatAsset, 'EUR')
S_GBP = cast(typing.FiatAsset, 'GBP')
S_JPY = cast(typing.FiatAsset, 'JPY')
S_CNY = cast(typing.FiatAsset, 'CNY')
FIAT_CURRENCIES = (S_USD, S_EUR, S_GBP, S_JPY, S_CNY)
