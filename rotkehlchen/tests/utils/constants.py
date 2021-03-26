from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.typing import string_to_ethereum_address

A_RDN = EthereumToken('RDN')
A_GNO = EthereumToken('GNO')
A_DAO = EthereumToken('DAO')
A_MKR = EthereumToken('MKR')
A_SNGLS = EthereumToken('SNGLS')
A_USDT = EthereumToken('USDT')
A_MKR = EthereumToken('MKR')
A_BAT = EthereumToken('BAT')
A_WBTC = EthereumToken('WBTC')
A_USDC = EthereumToken('USDC')
A_PAXG = EthereumToken('PAXG')
A_ADAI = Asset('aDAI')
A_CDAI = Asset('cDAI')
A_CUSDC = Asset('cUSDC')
A_KCS = EthereumToken('KCS')
A_MCO = EthereumToken('MCO')
A_CRO = EthereumToken('CRO')
A_SUSHI = EthereumToken('SUSHI')
A_1INCH = EthereumToken('1INCH')
A_SDT2 = EthereumToken('SDT-2')
A_REP = EthereumToken('REP')
A_QTUM = EthereumToken('QTUM')
A_OCEAN = EthereumToken('OCEAN')

A_ADA = Asset('ADA')
A_AIR2 = Asset('AIR-2')
A_SDC = Asset('SDC')
A_DOGE = Asset('DOGE')
A_NANO = Asset('NANO')
A_XRP = Asset('XRP')
A_LTC = Asset('LTC')
A_SC = Asset('SC')
A_XMR = Asset('XMR')
A_DASH = Asset('DASH')
A_WAVES = Asset('WAVES')
A_EWT = Asset('EWT')
A_XTZ = Asset('XTZ')
A_IOTA = Asset('IOTA')
A_BSV = Asset('BSV')
A_BCH = Asset('BCH')
A_BNB = Asset('BNB')
A_CNY = Asset('CNY')
A_JPY = Asset('JPY')
A_ZEC = Asset('ZEC')
A_BUSD = Asset('BUSD')
A_DOT = Asset('DOT')
A_GBP = Asset('GBP')
A_CHF = Asset('CHF')
A_AUD = Asset('AUD')
A_EUR = Asset('EUR')
A_KRW = Asset('KRW')
A_CAD = Asset('CAD')

ETH_ADDRESS1 = string_to_ethereum_address('0x5153493bB1E1642A63A098A65dD3913daBB6AE24')
ETH_ADDRESS2 = string_to_ethereum_address('0x4FED1fC4144c223aE3C1553be203cDFcbD38C581')
ETH_ADDRESS3 = string_to_ethereum_address('0x267FdC6F9F1C1a783b36126c1A59a9fbEBf42f84')

TX_HASH_STR1 = '0x9c81f44c29ff0226f835cd0a8a2f2a7eca6db52a711f8211b566fd15d3e0e8d4'
TX_HASH_STR2 = '0x1c81f44c29ff0236f835cd0a8a2f2a7eca6db52a711f8211b566fd15d3e0e899'
TX_HASH_STR3 = '0x3c81144c29f60236f735cd0a8a2f2a7e3a6db52a713f8211b562fd15d3e0e192'

MOCK_INPUT_DATA = b'123'
MOCK_INPUT_DATA_HEX = '0x313233'

DEFAULT_TESTS_MAIN_CURRENCY = A_EUR
