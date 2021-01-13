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
A_NZD = Asset('NZD')
A_BRL = Asset('BRL')
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
    A_NZD,
    A_BRL,
)

S_BTC = 'BTC'
S_ETH = 'ETH'
S_KSM = 'KSM'

A_BTC = Asset(S_BTC)
A_BCH = Asset('BCH')
A_BAL = Asset('BAL')
A_BSV = Asset('BSV')
A_ETH = Asset(S_ETH)
A_ETH2 = Asset('ETH2')
A_ETC = Asset('ETC')
A_KSM = Asset(S_KSM)
A_BAT = EthereumToken('BAT')
A_UNI = EthereumToken('UNI')
A_1INCH = EthereumToken('1INCH')
A_DAI = EthereumToken('DAI')
A_SAI = EthereumToken('SAI')
A_YFI = EthereumToken('YFI')
A_USDT = EthereumToken('USDT')
A_USDC = EthereumToken('USDC')
A_TUSD = EthereumToken('TUSD')
A_ALINK = EthereumToken('aLINK')
A_GUSD = EthereumToken('GUSD')
A_CRV = EthereumToken('CRV')
A_KNC = EthereumToken('KNC')
A_WBTC = EthereumToken('WBTC')
A_WETH = EthereumToken('WETH')
A_ZRX = EthereumToken('ZRX')
A_MANA = EthereumToken('MANA')
A_PAX = EthereumToken('PAX')
A_COMP = EthereumToken('COMP')
A_LRC = EthereumToken('LRC')
A_LINK = EthereumToken('LINK')
A_ADX = EthereumToken('ADX')
A_TORN = EthereumToken('TORN')
A_CORN = EthereumToken('CORN-2')
A_GRAIN = EthereumToken('GRAIN')
