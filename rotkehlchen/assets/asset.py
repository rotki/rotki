from typing import Any

from dataclasses import dataclass

from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.errors import UnknownAsset

WORLD_TO_KRAKEN = {
    'ETC': 'XETC',
    'ETH': 'XETH',
    'LTC': 'XLTC',
    'REP': 'XREP',
    'BTC': 'XXBT',
    'XMR': 'XXMR',
    'XRP': 'XXRP',
    'ZEC': 'XZEC',
    'EUR': 'ZEUR',
    'USD': 'ZUSD',
    'GBP': 'ZGBP',
    'CAD': 'ZCAD',
    'JPY': 'ZJPY',
    'KRW': 'ZKRW',
    'DAO': 'XDAO',
    'MLN': 'XMLN',
    'ICN': 'XICN',
    'GNO': 'GNO',
    'BCH': 'BCH',
    'XLM': 'XXLM',
    'DASH': 'DASH',
    'EOS': 'EOS',
    'USDT': 'USDT',
    'KFEE': 'KFEE',
    'ADA': 'ADA',
    'QTUM': 'QTUM',
    'NMC': 'XNMC',
    'VEN': 'XXVN',
    'DOGE': 'XXDG',
    'XTZ': 'XTZ',
    'BSV': 'BSV',
}

WORLD_TO_CRYPTOCOMPARE = {
    'RDN': 'RDN*',
    'DATAcoin': 'DATA',
    'IOTA': 'IOT',
    'BQX': 'ETHOS',
    'XRB': 'NANO',
    'AIR-2': 'AIR*',
}

WORLD_TO_POLONIEX = {
    # AIR-2 is aircoin for us and AIR is airtoken. Poloniex has only aircoin
    'AIR-2': 'AIR',
    # APH-2 is Aphrodite coin for us and APH is Aphelion. Poloniex has only aphrodite
    'APH-2': 'APH',
    # Poloniex listed BTCtalkcoin as BCC as it was its original ticker but the
    # ticker later changes and it is now known to the world  as TALK
    'TALK': 'BCC',
}


@dataclass(init=True, repr=True, eq=False, order=False, unsafe_hash=False, frozen=True)
class Asset():
    name: str

    def __post_init__(self):
        if not AssetResolver().is_name_canonical(self.name):
            raise UnknownAsset(self.name)

    def canonical(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.name

    def to_kraken(self) -> str:
        return WORLD_TO_KRAKEN[self.name]

    def to_cryptocompare(self) -> str:
        return WORLD_TO_CRYPTOCOMPARE.get(self.name, self.name)

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Asset):
            return self.name == other.name
        elif isinstance(other, str):
            return self.name == other
        else:
            raise ValueError(f'Invalid comparison of asset with {type(other)}')

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)
