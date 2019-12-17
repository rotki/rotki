from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.constants.assets import A_EUR
from rotkehlchen.typing import EthAddress

A_RDN = EthereumToken('RDN')
A_GNO = EthereumToken('GNO')
A_DAO = EthereumToken('DAO')
A_DOGE = Asset('DOGE')
A_XMR = Asset('XMR')
A_DASH = Asset('DASH')
A_IOTA = Asset('IOTA')
A_BSV = Asset('BSV')
A_BCH = Asset('BCH')
A_SNGLS = Asset('SNGLS')
A_BNB = Asset('BNB')
A_USDT = Asset('USDT')
A_CNY = Asset('CNY')
A_JPY = Asset('JPY')
A_MKR = Asset('MKR')

ETH_ADDRESS1 = EthAddress('0x5153493bB1E1642A63A098A65dD3913daBB6AE24')
ETH_ADDRESS2 = EthAddress('0x4FED1fC4144c223aE3C1553be203cDFcbD38C581')
ETH_ADDRESS3 = EthAddress('0x267FdC6F9F1C1a783b36126c1A59a9fbEBf42f84')

TX_HASH_STR1 = '0x9c81f44c29ff0226f835cd0a8a2f2a7eca6db52a711f8211b566fd15d3e0e8d4'
TX_HASH_STR2 = '0x1c81f44c29ff0236f835cd0a8a2f2a7eca6db52a711f8211b566fd15d3e0e899'
TX_HASH_STR3 = '0x3c81144c29f60236f735cd0a8a2f2a7e3a6db52a713f8211b562fd15d3e0e192'

MOCK_INPUT_DATA = b'123'
MOCK_INPUT_DATA_HEX = '0x313233'

DEFAULT_TESTS_MAIN_CURRENCY = A_EUR
