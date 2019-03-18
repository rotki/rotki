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
    'BITS-2': 'BITS*',
    'BTM-2': 'BTM*',
    # In Rotkehlchen CCN-2 is Cannacoin and CCN is CustomContractNetwork
    'CCN-2': 'CCN',
    # In Rotkehlchen FAIR-2 is FairGame and FAIR is FairCoin
    'FAIR-2': 'FAIR*',
    # Almosst 100% certain that GPUC (https://coinmarketcap.com/currencies/gpucoin/)
    # is GPU in cryptocompare (https://www.cryptocompare.com/coins/gpu/overview)
    'GPUC': 'GPU',
    # In Rotkehlchen we got 3 coins with KEY symbol. Cryptocompare does not have
    # data for KEY-2
    # KEY -> Selfkey
    # KEY-2 -> KEY
    # KEY-3 -> KeyCoin
    'KEY-3': 'KEY*',
    # In Rotkehlchen KNC is KyberNetwork and KNC-2 is KingN coin. In cryptocompare
    # KNC** is KingN coin
    'KNC-2': 'KNC**',
    # Liquidity network is LQD in Rotkehlchen but LQDN in Cryptocompare
    'LQD': 'LQDN',
    # Monetaverde is as MNV in cryptocompare while it should be MCN
    # https://www.cryptocompare.com/coins/mnv/overview
    'MCN': 'MNV',
    # Marscoin is as MRS in cryptocompare
    # https://www.cryptocompare.com/coins/mrs/overview
    'MARS': 'MRS',
    # Marginless is not in cryptocompare. Asking for MRS will return MARScoin
    'MRS': None,
    # Mazacoin is as MZC in cryptocompare
    'MAZA': 'MZC',
    # NuBits is NBT in cryptocompare
    'USNBT': 'NBT',
    # Polymath is POLY in Rotkehlchen and POLY* in cryptocompare
    'POLY': 'POLY*',
    # Polybit is POLY-2 in Rotkehlchen and POLY in cryptocompare
    'POLY-2': 'POLY',
    # Steem dollars are SBD* in cryptocompare
    'SBD': 'SBD*',
    # YacCoin is YAC in cryptocompare
    'YACC': 'YAC',
}

WORLD_TO_POLONIEX = {
    # AIR-2 is aircoin for us and AIR is airtoken. Poloniex has only aircoin
    'AIR-2': 'AIR',
    # APH-2 is Aphrodite coin for us and APH is Aphelion. Poloniex has only aphrodite
    'APH-2': 'APH',
    # Poloniex listed BTCtalkcoin as BCC as it was its original ticker but the
    # ticker later changes and it is now known to the world  as TALK
    'TALK': 'BCC',
    # Poloniex delisted BCH and listed it as BCHABC after the Bitcoin Cash
    # ABC / SV fork. In Rotkehlchen we consider BCH to be the same as BCHABC
    'BCH': 'BCHABC',
    # Poloniex has the BCH Fork, Bitcoin Satoshi's vision listed as BCHSV.
    # We know it as BSV
    'BSV': 'BCHSV',
    # Caishen is known as CAI in Poloniex. This is before the swap to CAIX
    'CAIX': 'CAI',
    # CCN is Cannacoin in Poloniex but in Rotkehlchen we know it as CCN-2
    'CCN-2': 'CCN',
    # CCN is CustomContractNetwork in Rotkehlchen but does not exist in Cryptocompare
    # Putting it as conversion to make sure we don't accidentally ask for wrong price
    'CCN': '',
    # Faircoin is known as FAIR outside of Poloniex. Seems to be the same as the
    # now delisted Poloniex's FAC if you look at the bitcointalk announcement
    # https://bitcointalk.org/index.php?topic=702675.0
    'FAIR': 'FAC',
    # KeyCoin in Poloniex is KEY but in Rotkehlchen it's KEY-3
    'KEY-3': 'KEY',
    # Marscoin in Poloniex is MRS but in Rotkehlchen it's MARS
    'MARS': 'MRS',
    # Myriadcoin in Poloniex is MYR but in Rotkehlchen it's XMY
    'XMY': 'MYR',
    # NuBits in Poloniex is NBT but in Rotkehlchen it's USNBT
    'USNBT': 'NBT',
    # Stellar is XLM everywhere, apart from Poloniex
    'XLM': 'STR',
    # Poloniex still has the old name WC for WhiteCoin
    'XWC': 'WC',
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
