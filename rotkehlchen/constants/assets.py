from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.typing import FiatAsset

S_USD = FiatAsset('USD')
S_EUR = FiatAsset('EUR')
S_GBP = FiatAsset('GBP')
S_JPY = FiatAsset('JPY')
S_CNY = FiatAsset('CNY')
S_CAD = FiatAsset('CAD')
S_KRW = FiatAsset('KRW')
FIAT_CURRENCIES = (S_USD, S_EUR, S_GBP, S_JPY, S_CNY, S_CAD, S_KRW)

S_BTC = 'BTC'
S_ETH = 'ETH'

A_BTC = Asset(S_BTC)
A_BCH = Asset('BCH')
A_BSV = Asset('BSV')
A_ETH = Asset(S_ETH)
A_ETC = Asset('ETC')
A_USD = Asset(S_USD)
A_EUR = Asset(S_EUR)
A_DAI = EthereumToken('DAI')
A_SAI = EthereumToken('SAI')
