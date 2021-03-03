from dataclasses import dataclass, field
from functools import total_ordering
from typing import Any, Optional, Type, TypeVar

from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.errors import DeserializationError, UnknownAsset, UnsupportedAsset
from rotkehlchen.typing import AssetType, ChecksumEthAddress, EthTokenInfo, Timestamp

WORLD_TO_BITTREX = {
    # In Rotkehlchen Bitswift is BITS-2 but in Bittrex it's BITS
    'BITS-2': 'BITS',
    # In Rotkehlchen NuBits is USNBT but in Bittrex it's NBT
    'USNBT': 'NBT',
    # In Rotkehlchen BTM-2 is Bytom but in Bittrex it's BTM
    'BTM-2': 'BTM',
    # In Rotkehlchen PAI-2 is PCHAIN token but in Bittrex it's PI
    'PAI-2': 'PI',
    # In Rotkehlchen PLA-2 is Playchip but in Bittrex is PLA
    'PLA-2': 'PLA',
    # In Rotkehlchen sUSD is Synt USD but in Bittrex it's SUSD
    'sUSD': 'SUSD',
    # In Rotkehlchen LUNA-2 is Terra Luna but in Bittrex it's LUNA
    'LUNA-2': 'LUNA',
    # In Rotkehlchen WorldWideAssetExchange is WAX but in Bittrex it's WASP
    'WAX': 'WAXP',
    # In Rotkehlchen Validity is RADS, the old name but in Bittrex it's VAL
    'RADS': 'VAL',
}

WORLD_TO_POLONIEX = {
    # AIR-2 is aircoin for us and AIR is airtoken. Poloniex has only aircoin
    'AIR-2': 'AIR',
    # Decentr is DEC-2 for us but DEC in Poloniex
    'DEC-2': 'DEC',
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
    'cUSDT': 'CUSDT',
    # Faircoin is known as FAIR outside of Poloniex. Seems to be the same as the
    # now delisted Poloniex's FAC if you look at the bitcointalk announcement
    # https://bitcointalk.org/index.php?topic=702675.0
    'FAIR': 'FAC',
    # KeyCoin in Poloniex is KEY but in Rotkehlchen it's KEY-3
    'KEY-3': 'KEY',
    # Mazacoin in Poloniex is MZC but in Rotkehlchen it's MAZA
    'MAZA': 'MZC',
    # Myriadcoin in Poloniex is MYR but in Rotkehlchen it's XMY
    'XMY': 'MYR',
    # NuBits in Poloniex is NBT but in Rotkehlchen it's USNBT
    'USNBT': 'NBT',
    # Stellar is XLM everywhere, apart from Poloniex
    'XLM': 'STR',
    # Poloniex still has the old name WC for WhiteCoin
    'XWC': 'WC',
    # Poloniex uses a different name for 1inch. Maybe due to starting with number?
    '1INCH': 'ONEINCH',
}

WORLD_TO_KRAKEN = {
    'ATOM': 'ATOM',
    'ALGO': 'ALGO',
    'AUD': 'ZAUD',
    'BAT': 'BAT',
    'COMP': 'COMP',
    'DOT': 'DOT',
    'KAVA': 'KAVA',
    'KNC': 'KNC',
    'LINK': 'LINK',
    'BSV': 'BSV',
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
    'CHF': 'CHF',
    'KRW': 'ZKRW',
    'REPV2': 'REPV2',
    'DAO': 'XDAO',
    'MLN': 'XMLN',
    'ICN': 'XICN',
    'GNO': 'GNO',
    'BCH': 'BCH',
    'XLM': 'XXLM',
    'DASH': 'DASH',
    'EOS': 'EOS',
    'USDC': 'USDC',
    'USDT': 'USDT',
    'KFEE': 'KFEE',
    'ADA': 'ADA',
    'QTUM': 'QTUM',
    'NMC': 'XNMC',
    'VEN': 'XXVN',
    'DOGE': 'XXDG',
    'DAI': 'DAI',
    'XTZ': 'XTZ',
    'WAVES': 'WAVES',
    'ICX': 'ICX',
    'NANO': 'NANO',
    'OMG': 'OMG',
    'SC': 'SC',
    'PAXG': 'PAXG',
    'LSK': 'LSK',
    'TRX': 'TRX',
    'OXT': 'OXT',
    'STORJ': 'STORJ',
    'BAL': 'BAL',
    'KSM': 'KSM',
    'CRV': 'CRV',
    'SNX': 'SNX',
    'FIL': 'FIL',
    'UNI': 'UNI',
    'YFI': 'YFI',
    'ANT': 'ANT',
    'KEEP': 'KEEP',
    'TBTC': 'TBTC',
    'ETH2': 'ETH2',
    'AAVE': 'AAVE',
    'MANA': 'MANA',
    'GRT': 'GRT',
    'FLOW': 'FLOW',
}

WORLD_TO_BINANCE = {
    # When BCH forked to BCHABC and BCHSV, binance renamed the original to ABC
    'BCH': 'BCHABC',
    'BSV': 'BCHSV',
    # ETHOS is known as BQX in Binance
    'ETHOS': 'BQX',
    # GXChain is GXS in Binance but GXC in Rotkehlchen
    'GXC': 'GXS',
    # Luna Terra is LUNA-2 in rotki
    'LUNA-2': 'LUNA',
    # YOYOW is known as YOYO in Binance
    'YOYOW': 'YOYO',
    # Solana is SOL-2 in rotki
    'SOL-2': 'SOL',
    # BETH is the eth staked in beacon chain
    'ETH2': 'BETH',
    # STX is Blockstack in Binance
    'STX-2': 'STX',
    # ONE is Harmony in Binance
    'ONE-2': 'ONE',
}

WORLD_TO_BITFINEX = {
    'BCH': 'BCHABC',
    'CNY': 'CNH',
    'DOGE': 'DOG',
    'REPV2': 'REP',
    'TRIO': 'TRI',
    'ZB': 'ZBT',
}

WORLD_TO_KUCOIN = {
    'BSV': 'BCHSV',
    'LUNA-2': 'LUNA',
}

WORLD_TO_ICONOMI = {
    # In Rotkehlchen LUNA-2 is Terra Luna but in Iconomi it's LUNA
    'LUNA-2': 'LUNA',
}


@total_ordering
@dataclass(init=True, repr=True, eq=False, order=False, unsafe_hash=False, frozen=True)
class Asset():
    identifier: str
    name: str = field(init=False)
    symbol: str = field(init=False)
    active: bool = field(init=False)
    asset_type: AssetType = field(init=False)
    started: Timestamp = field(init=False)
    ended: Optional[Timestamp] = field(init=False)
    forked: Optional[str] = field(init=False)
    swapped_for: Optional[str] = field(init=False)
    # None means no special mapping. '' means not supported
    cryptocompare: Optional[str] = field(init=False)
    coingecko: Optional[str] = field(init=False)

    def __post_init__(self) -> None:
        """
        Asset post initialization

        The only thing that is given to initialize an asset is a string.

        If a non string is given then it's probably a deserialization error or
        invalid data were given to us by the server if an API was queried.

        May raise UnknownAsset if the asset identifier can't be matched to anything
        """
        if not isinstance(self.identifier, str):
            raise DeserializationError(
                'Tried to initialize an asset out of a non-string identifier',
            )

        canonical_id = AssetResolver().is_identifier_canonical(self.identifier)
        if canonical_id is None:
            raise UnknownAsset(self.identifier)
        # else let's make sure we got the canonical id in our data struct
        object.__setattr__(self, 'identifier', canonical_id)

        data = AssetResolver().get_asset_data(self.identifier)
        # Ugly hack to set attributes of a frozen data class as post init
        # https://docs.python.org/3/library/dataclasses.html#frozen-instances
        object.__setattr__(self, 'name', data.name)
        object.__setattr__(self, 'symbol', data.symbol)
        object.__setattr__(self, 'active', data.active)
        object.__setattr__(self, 'asset_type', data.asset_type)
        object.__setattr__(self, 'started', data.started)
        object.__setattr__(self, 'ended', data.ended)
        object.__setattr__(self, 'forked', data.forked)
        object.__setattr__(self, 'swapped_for', data.swapped_for)
        object.__setattr__(self, 'cryptocompare', data.cryptocompare)
        object.__setattr__(self, 'coingecko', data.coingecko)

    def serialize(self) -> str:
        return self.identifier

    def is_fiat(self) -> bool:
        return self.asset_type == AssetType.FIAT

    def is_eth_token(self) -> bool:
        return self.asset_type in (AssetType.ETH_TOKEN, AssetType.ETH_TOKEN_AND_MORE)

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f'<Asset identifier:{self.identifier} name:{self.name} symbol:{self.symbol}>'

    def to_kraken(self) -> str:
        return WORLD_TO_KRAKEN[self.identifier]

    def to_bitfinex(self) -> str:
        return WORLD_TO_BITFINEX.get(self.identifier, self.identifier)

    def to_bittrex(self) -> str:
        return WORLD_TO_BITTREX.get(self.identifier, self.identifier)

    def to_binance(self) -> str:
        return WORLD_TO_BINANCE.get(self.identifier, self.identifier)

    def to_cryptocompare(self) -> str:
        """Returns the symbol with which to query cryptocompare for the asset

        May raise:
            - UnsupportedAsset() if the asset is not supported by cryptocompare
        """
        cryptocompare_str = self.identifier if self.cryptocompare is None else self.cryptocompare
        # There is an asset which should not be queried in cryptocompare
        if cryptocompare_str == '':
            raise UnsupportedAsset(f'{self.identifier} is not supported by cryptocompare')

        # Seems cryptocompare capitalizes everything. So cDAI -> CDAI
        return cryptocompare_str.upper()

    def to_coingecko(self) -> str:
        """Returns the symbol with which to query coingecko for the asset

        May raise:
            - UnsupportedAsset() if the asset is not supported by coingecko
        """
        coingecko_str = '' if self.coingecko is None else self.coingecko
        # This asset has no coingecko mapping
        if coingecko_str == '':
            raise UnsupportedAsset(f'{self.identifier} is not supported by coingecko')
        return coingecko_str

    def has_coingecko(self) -> bool:
        return self.coingecko is not None and self.coingecko != ''

    def __hash__(self) -> int:
        return hash(self.identifier)

    def __eq__(self, other: Any) -> bool:
        if other is None:
            return False

        if isinstance(other, Asset):
            return self.identifier == other.identifier
        if isinstance(other, str):
            return self.identifier == other
        # else
        raise ValueError(f'Invalid comparison of asset with {type(other)}')

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, Asset):
            return self.identifier < other.identifier
        if isinstance(other, str):
            return self.identifier < other
        # else
        raise ValueError(f'Invalid comparison of asset with {type(other)}')


@dataclass(init=True, repr=True, eq=False, order=False, unsafe_hash=False, frozen=True)
class HasEthereumToken(Asset):
    """ Marker to denote assets having an Ethereum token address """
    ethereum_address: ChecksumEthAddress = field(init=False)
    decimals: int = field(init=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        data = AssetResolver().get_asset_data(self.identifier)  # pylint: disable=no-member

        if not data.ethereum_address:
            raise DeserializationError(
                'Tried to initialize a non Ethereum asset as Ethereum Token',
            )

        object.__setattr__(self, 'ethereum_address', data.ethereum_address)
        object.__setattr__(self, 'decimals', data.decimals)


# Create a generic variable that can be 'EthereumToken', or any subclass.
T = TypeVar('T', bound='EthereumToken')


@dataclass(init=True, repr=True, eq=False, order=False, unsafe_hash=False, frozen=True)
class EthereumToken(HasEthereumToken):

    def token_info(self) -> EthTokenInfo:
        return EthTokenInfo(
            identifier=self.identifier,
            address=self.ethereum_address,
            symbol=self.symbol,
            name=self.name,
            decimals=self.decimals,
        )

    @classmethod
    def from_asset(cls: Type[T], asset: Asset) -> Optional[T]:
        """Attempts to turn an asset into an EthereumToken. If it fails returns None"""
        try:
            return cls(asset.identifier)
        except DeserializationError:
            return None
