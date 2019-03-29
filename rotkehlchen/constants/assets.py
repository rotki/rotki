from typing import cast

from rotkehlchen.assets.asset import Asset
from rotkehlchen.typing import EthToken, FiatAsset, NonEthTokenBlockchainAsset

S_USD = FiatAsset('USD')
S_EUR = FiatAsset('EUR')
S_GBP = FiatAsset('GBP')
S_JPY = FiatAsset('JPY')
S_CNY = FiatAsset('CNY')
S_CAD = FiatAsset('CAD')
S_KRW = FiatAsset('KRW')
FIAT_CURRENCIES = (S_USD, S_EUR, S_GBP, S_JPY, S_CNY, S_CAD, S_KRW)

S_ETC = 'ETC'
S_BCH = 'BCH'
S_BTC = 'BTC'
S_ETH = 'ETH'

A_BTC = Asset(S_BTC)
A_BCH = Asset(S_BCH)
S_BSV = cast(NonEthTokenBlockchainAsset, 'BSV')
A_ETH = Asset(S_ETH)
A_ETC = Asset(S_ETC)
S_DATACOIN = cast(NonEthTokenBlockchainAsset, 'DATAcoin')
S_XMR = cast(NonEthTokenBlockchainAsset, 'XMR')
S_NANO = cast(NonEthTokenBlockchainAsset, 'NANO')
S_RAIBLOCKS = cast(NonEthTokenBlockchainAsset, 'XRB')
S_MLN_OLD = EthToken('MLN (old)')
S_MLN_NEW = EthToken('MLN (new)')
S_MLN = EthToken('MLN')
S_YOYOW = cast(NonEthTokenBlockchainAsset, 'YOYOW')
S_RDN = cast(EthToken, 'RDN')
A_USD = Asset(S_USD)
A_EUR = Asset(S_EUR)
