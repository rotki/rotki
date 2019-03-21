from dataclasses import dataclass, field
from typing import Any, Optional

from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.errors import UnknownAsset
from rotkehlchen.typing import AssetType, Timestamp

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
    # GoldCoin is GLD in cryptocompare, but GLC in most other places including Rotkehlcen
    'GLC': 'GLD',
    # In Rotkehlchen we have GlobalCoin as GLC-2. In Cryptocompare it's GLC
    'GLC-2': 'GLC',
    # In Rotkehlchen and everywhere else Bitbean is BITB but in cryptocompare BEAN
    'BITB': 'BEAN',
    # For Rotkehlchen RCN is Ripio Credit Network and RCN-2 is Rcoin
    # Rcoin is RCN* in cryptocompare
    'RCN-2': 'RCN*',
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

WORLD_TO_BITTREX = {
    # In Rotkehlcen Bitswift is BITS-2 but in Bittrex it's BITS
    'BITS-2': 'BITS',
    # In Rotkehlcen NuBits is USNBT but in Bittrex it's NBT
    'USNBT': 'NBT',
}


@dataclass(init=True, repr=True, eq=False, order=False, unsafe_hash=False, frozen=True)
class Asset():
    symbol: str
    name: str = field(init=False)
    active: bool = field(init=False)
    asset_type: AssetType = field(init=False)
    started: Timestamp = field(init=False)
    ended: Optional[Timestamp] = field(init=False)
    forked: Optional[str] = field(init=False)
    swapped_for: Optional[str] = field(init=False)

    def __post_init__(self):
        if not AssetResolver().is_symbol_canonical(self.symbol):
            raise UnknownAsset(self.symbol)
        data = AssetResolver().get_asset_data(self.symbol)

        # Ugly hack to set attributes of a frozen data class as post init
        # https://docs.python.org/3/library/dataclasses.html#frozen-instances
        object.__setattr__(self, 'name', data.name)
        object.__setattr__(self, 'active', data.active)
        object.__setattr__(self, 'asset_type', data.asset_type)
        object.__setattr__(self, 'started', data.started)
        object.__setattr__(self, 'ended', data.ended)
        object.__setattr__(self, 'forked', data.forked)
        object.__setattr__(self, 'swapped_for', data.swapped_for)

    def canonical(self) -> str:
        return self.symbol

    def __str__(self) -> str:
        return self.name

    def to_kraken(self) -> str:
        return WORLD_TO_KRAKEN[self.symbol]

    def to_bittrex(self) -> str:
        return WORLD_TO_BITTREX.get(self.symbol, self.symbol)

    def to_cryptocompare(self) -> str:
        return WORLD_TO_CRYPTOCOMPARE.get(self.symbol, self.symbol)

    def __hash__(self):
        return hash(self.symbol)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Asset):
            return self.symbol == other.symbol
        elif isinstance(other, str):
            return self.symbol == other
        else:
            raise ValueError(f'Invalid comparison of asset with {type(other)}')

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)
