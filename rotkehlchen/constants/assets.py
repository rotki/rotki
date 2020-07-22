from rotkehlchen.assets.asset import Asset, EthereumToken

A_USD = Asset('USD')
A_EUR = Asset('EUR')
A_GBP = Asset('GBP')
A_JPY = Asset('JPY')
A_CNY = Asset('CNY')
A_CAD = Asset('CAD')
A_KRW = Asset('KRW')
A_RUB = Asset('RUB')
A_CHF = Asset('CHF')
A_TRY = Asset('TRY')
A_ZAR = Asset('ZAR')
A_AUD = Asset('AUD')
FIAT_CURRENCIES = (
    A_USD,
    A_EUR,
    A_GBP,
    A_JPY,
    A_CNY,
    A_CAD,
    A_KRW,
    A_RUB,
    A_CHF,
    A_TRY,
    A_ZAR,
    A_AUD,
)

S_BTC = 'BTC'
S_ETH = 'ETH'

A_BTC = Asset(S_BTC)
A_BCH = Asset('BCH')
A_BSV = Asset('BSV')
A_ETH = Asset(S_ETH)
A_ETC = Asset('ETC')
A_REP = EthereumToken('REP')
A_DAI = EthereumToken('DAI')
A_SAI = EthereumToken('SAI')
