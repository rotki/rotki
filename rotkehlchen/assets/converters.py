from typing import Dict, Optional

from rotkehlchen.assets.asset import (
    WORLD_TO_BINANCE,
    WORLD_TO_BITFINEX,
    WORLD_TO_BITTREX,
    WORLD_TO_ICONOMI,
    WORLD_TO_KRAKEN,
    WORLD_TO_KUCOIN,
    WORLD_TO_POLONIEX,
    Asset,
)
from rotkehlchen.constants.assets import A_DAI, A_SAI
from rotkehlchen.db.upgrades.v7_v8 import COINBASE_DAI_UPGRADE_END_TS
from rotkehlchen.errors import DeserializationError, UnsupportedAsset
from rotkehlchen.typing import Timestamp
from rotkehlchen.utils.misc import ts_now

UNSUPPORTED_POLONIEX_ASSETS = (
    # This was a super shortlived coin.
    # Only info is here: https://bitcointalk.org/index.php?topic=632818.0
    # No price info in cryptocompare or paprika. So we don't support it.
    'AXIS',
    'APH',
    # This was yet another shortlived coin whose announcement is here:
    # https://bitcointalk.org/index.php?topic=843495 and coinmarketcap:
    # https://coinmarketcap.com/currencies/snowballs/.
    # No price info in cryptocompare or paprika. So we don't support it.
    'BALLS',
    # There are two coins with the name BankCoin, neither of which seems to
    # be this. This market seems to have beend added in May 2014
    # https://twitter.com/poloniex/status/468070096913432576
    # but both other bank coins are in 2017 and 2018 respectively
    # https://coinmarketcap.com/currencies/bankcoin/
    # https://coinmarketcap.com/currencies/bank-coin/
    # So this is an unknown coin
    'BANK',
    # BitBlock seems to be this: https://coinmarketcap.com/currencies/bitblock/
    # and seems to have lived for less than a month. It does not seem to be the
    # same as BBK, the BitBlocks project (https://www.cryptocompare.com/coins/bbk/overview)
    # No price info in cryptocompare or paprika. So we don't support it.
    'BBL',
    # Black Dragon Coin. Seems like a very short lived scam from Russia.
    # Only info that I found is here: https://bitcointalk.org/index.php?topic=597006.0
    # No price info in cryptocompare or paprika. So we don't support it.
    'BDC',
    # Badgercoin. A very shortlived coin. Only info found is here:
    # https://coinmarketcap.com/currencies/badgercoin/
    # Same symbol is used for an active coin called "Bitdegreee"
    # https://coinmarketcap.com/currencies/bitdegree/
    # No price info in cryptocompare or paprika. So we don't support it.
    'BDG',
    # Bonuscoin. A shortlived coin. Only info found is here:
    # https://coinmarketcap.com/currencies/bonuscoin/
    # No price info in cryptocompare or paprika. So we don't support it.
    'BNS',
    # Bonescoin. A shortlived coin. Only info found is here:
    # https://coinmarketcap.com/currencies/bones/
    # No price info in cryptocompare or paprika. So we don't support it.
    'BONES',
    # Burnercoin. A shortlived coind Only info is here:
    # https://coinmarketcap.com/currencies/burnercoin/
    # No price info in cryptocompare or paprika. So we don't support it.
    'BURN',
    # Colbertcoin. Shortlived coin. Only info is here:
    # https://coinmarketcap.com/currencies/colbertcoin/
    # No price info in cryptocompare or paprika. So we don't support it.
    'CC',
    # Chancecoin.
    # https://coinmarketcap.com/currencies/chancecoin/
    'CHA',
    # C-note. No data found anywhere. Only this:
    # https://bitcointalk.org/index.php?topic=397916.0
    'CNOTE',
    # Coino. Shortlived coin with only data found here
    # https://coinmarketcap.com/currencies/coino/
    # A similar named token, coin(o) with symbol CNO has data
    # both in cmc and paprika, but CON doesn't so we don't support it
    'CON',
    # CorgiCoin. No data found except from here:
    # https://coinmarketcap.com/currencies/corgicoin/
    'CORG',
    # Neodice. No data found except from here:
    # https://coinmarketcap.com/currencies/neodice/
    # A lot more tokens with the DICE symbol exist so we don't support this
    'DICE',
    # Distrocoin. No data found except from here:
    # https://coinmarketcap.com/currencies/distrocoin/
    'DIS',
    # Bitshares DNS. No data found except from here:
    # https://coin.market/crypto/dns
    'DNS',
    # DvoraKoin. No data found except from here:
    # https://bitcointalk.org/index.php?topic=613854.0
    'DVK',
    # EBTcoin. No data found except from here:
    # https://coinmarketcap.com/currencies/ebtcoin/
    'EBT',
    # EmotiCoin. No data found except from here:
    # https://coinmarketcap.com/currencies/emoticoin/
    'EMO',
    # EntropyCoin. No data found except from here:
    # https://coinmarketcap.com/currencies/entropycoin/
    'ENC',
    # eToken. No data found except from here:
    # https://coinmarketcap.com/currencies/etoken/
    'eTOK',
    # ETHBNT. No data found outside of poloniex:
    # https://poloniex.com/exchange#btc_ethbnt
    'ETHBNT',
    # FoxCoin. No data found except from here:
    # https://coinmarketcap.com/currencies/foxcoin/
    'FOX',
    # FairQuark. No data found except from here:
    # https://coinmarketcap.com/currencies/fairquark/
    'FRQ',
    # FVZCoin. No data found except from here:
    # https://coin.market/crypto/fvz
    'FVZ',
    # Frozen. No data found except from here:
    # https://coinmarketcap.com/currencies/frozen/
    'FZ',
    # Fuzon. No data found except from here:
    # https://coinmarketcap.com/currencies/fuzon/
    'FZN',
    # Global Denomination. No data found except from here:
    # https://coinmarketcap.com/currencies/global-denomination/
    'GDN',
    # Giarcoin. No data found except from here:
    # https://bitcointalk.org/index.php?topic=545529.0
    'GIAR',
    # Globe. No data found except from here:
    # https://coinmarketcap.com/currencies/globe/
    'GLB',
    # GenesisCoin. No data found except from here:
    # https://bitcointalk.org/index.php?topic=518258.0
    'GNS',
    # GoldEagles. No data found.
    'GOLD',
    # GroupCoin. No data found except from here:
    # https://coinmarketcap.com/currencies/groupcoin/
    'GPC',
    # Gridcoin X. Not sure what this is. Perhaps a fork of Gridcoin
    # https://coinmarketcap.com/currencies/gridcoin-classic/#charts
    # In any case only poloniex lists it for a bit so ignoring it
    'GRCX',
    # H2Ocoin. No data found except from here:
    # https://coinmarketcap.com/currencies/h2ocoin/
    'H2O',
    # Hirocoin. No data found except from here:
    # https://coinmarketcap.com/currencies/hirocoin/
    'HIRO',
    # Hotcoin. Super shortlived. No data found except from here:
    # https://coinmarketcap.com/currencies/hotcoin/
    # Note there are 2 more coins with this symbol.
    # https://coinmarketcap.com/currencies/hydro-protocol/
    # https://coinmarketcap.com/currencies/holo/
    'HOT',
    # CoinoIndex. No data found except from here:
    # https://coinmarketcap.com/currencies/coinoindex/
    'INDEX',
    # InformationCoin. No data found except from here:
    # https://coinmarketcap.com/currencies/informationcoin/
    'ITC',
    # jl777hodl. No data found except from here:
    # https://coinmarketcap.com/currencies/jl777hodl/
    'JLH',
    # Jackpotcoin. No data found except from here:
    # https://coinmarketcap.com/currencies/jackpotcoin/
    'JPC',
    # Juggalocoin. No data found except from here:
    # https://bitcointalk.org/index.php?topic=555896.0
    'JUG',
    # KTON - Darwinia commitment token. No data found
    'KTON',
    # Limecoin. No data found except from here:
    # https://coinmarketcap.com/currencies/limecoin/
    'LC',
    # LimecoinLite. No data found except from here:
    # https://coinmarketcap.com/currencies/limecoinlite/
    'LCL',
    # LogiCoin. No data found except from here:
    # https://coinmarketcap.com/currencies/logicoin/
    'LGC',
    # LeagueCoin. No data found except from here:
    # https://coinmarketcap.com/currencies/leaguecoin/
    'LOL',
    # LoveCoin. No data found except from here:
    # https://coinmarketcap.com/currencies/lovecoin/
    'LOVE',
    # Mastiffcoin. No data found except from here:
    # https://coinmarketcap.com/currencies/mastiffcoin/
    'MAST',
    # CryptoMETH. No data found except from here:
    # https://coinmarketcap.com/currencies/cryptometh/
    'METH',
    # Millenium coin. No data found except from here:
    # https://coinmarketcap.com/currencies/millenniumcoin/
    'MIL',
    # Moneta. No data found except from here:
    # https://coinmarketcap.com/currencies/moneta/
    # There are other moneta coins like this:
    # https://www.cryptocompare.com/coins/moneta/overview/BTC
    # but they don't seem to bethe same
    'MNTA',
    # Monocle. No data found except from here:
    # https://coinmarketcap.com/currencies/monocle/
    'MON',
    # MicroCoin. No data found except from here:
    # https://coinmarketcap.com/currencies/microcoin/
    'MRC',
    # Metiscoin. No data found except from here:
    # https://coinmarketcap.com/currencies/metiscoin/
    'MTS',
    # Muniti. No data found except from here:
    # https://coinmarketcap.com/currencies/muniti/
    'MUN',
    # N5coin. No data found except from here:
    # https://coinmarketcap.com/currencies/n5coin/
    'N5X',
    # NAS. No data found except from here:
    # https://coinmarketcap.com/currencies/nas/
    # Note: This is not the Nebulas NAS token
    'NAS',
    # Nanolite. No data found except from here:
    # https://www.reddit.com/r/CryptoCurrency/comments/26neqz/nanolite_a_new_x11_cryptocurrency_which_launched/
    'NL',
    # NobleNXT. No data found except from here:
    # https://coinmarketcap.com/currencies/noblenxt/
    'NOXT',
    # NTX. No data found except from here:
    # https://coinmarketcap.com/currencies/ntx/
    'NTX',
    # (PAND)a coin. No data found except here:
    # https://coinmarketcap.com/currencies/pandacoin-panda/
    # Note: This is not the PND Panda coin
    'PAND',
    # Pawncoin. No data found except from here:
    # https://coinmarketcap.com/currencies/pawncoin/
    'PAWN',
    # Parallaxcoin. No data found except from here:
    # https://coinmarketcap.com/currencies/parallaxcoin/
    # Note: This is not PLEX coin
    'PLX',
    # Premine. No data found except from here:
    # https://coinmarketcap.com/currencies/premine/
    'PMC',
    # Particle. No data found except from here:
    # https://coinmarketcap.com/currencies/particle/
    'PRT',
    # Bitshares PTS. No data found except from here:
    # https://coinmarketcap.com/currencies/bitshares-pts/
    'PTS',
    # ShibeCoin. No data found except from here:
    # https://coinmarketcap.com/currencies/shibecoin/
    'SHIBE',
    # ShopX. No data found except from here:
    # https://coinmarketcap.com/currencies/shopx/
    'SHOPX',
    # SocialCoin. No data found except from here:
    # https://coinmarketcap.com/currencies/socialcoin/
    # Note this is not The SOCC Social coin
    # https://coinmarketcap.com/currencies/socialcoin-socc/
    'SOC',
    # SourceCoin. No data found except from here:
    # https://bitcointalk.org/index.php?topic=688494.160
    'SRCC',
    # SurgeCoin. No data found except from here:
    # https://coinmarketcap.com/currencies/surgecoin/
    'SRG',
    # SummerCoin. No data found except from here:
    # https://coinmarketcap.com/currencies/summercoin/
    'SUM',
    # SunCoin. No data found except from here:
    # https://coinmarketcap.com/currencies/suncoin/
    'SUN',
    # TalkCoin. No data found except from here:
    # https://coinmarketcap.com/currencies/talkcoin/
    'TAC',
    # Twecoin. No data found except from here:
    # https://bitcointalk.org/index.php?topic=553593.0
    'TWE',
    # UniversityCoin. No data found except from here:
    # https://coinmarketcap.com/currencies/universitycoin/
    'UVC',
    # Voxels. No data found except from here:
    # https://coincodex.com/crypto/voxels/
    'VOX',
    # X13 coin. No data found. Except from maybe this:
    # https://bitcointalk.org/index.php?topic=635382.200;wap2
    'X13',
    # ApiCoin. No data found except from here:
    # https://coinmarketcap.com/currencies/apicoin/
    'XAP',
    # Xcurrency. No data found except from here:
    # https://coinmarketcap.com/currencies/xcurrency/
    'XC',
    # ClearingHouse. No data found except from here:
    # https://coinmarketcap.com/currencies/clearinghouse/
    'XCH',
    # Filecoin IOU. No data found for this except from in poloniex.
    # As of 22/07/2020
    'XFIL',
    # HonorCoin. No data found except from here:
    # https://bitcointalk.org/index.php?topic=639043.0
    'XHC',
    # SilliconValleyCoin. No data found except from here:
    # https://coinmarketcap.com/currencies/siliconvalleycoin-old/
    'XSV',
    # CoinoUSD. No data found except from here:
    # https://coinmarketcap.com/currencies/coinousd/
    'XUSD',
    # Creds. No data found except from here:
    # https://bitcointalk.org/index.php?topic=513483.0
    'XXC',
    # YangCoin. No data found except from here:
    # https://coinmarketcap.com/currencies/yangcoin/
    'YANG',
    # YellowCoin. No data found except from here:
    # https://coinmarketcap.com/currencies/yellowcoin/
    'YC',
    # YinCoin. No data found except from here:
    # https://coinmarketcap.com/currencies/yincoin/
    'YIN',
    # Bitcoin and Volatility and Inverse volatility token.
    # No data found yet but should probably revisit. They are
    # in cryptocompare but they have no price
    'BVOL',
    'IBVOL',
    'XDOT',  # old polkadot before the split
    'BCC',  # neither in coingecko nor cryptocompare
    'BTCTRON',  # neither in coingecko nor cryptocompare
    'FCT2',  # neither in coingecko nor cryptocompare
    'XFLR',  # neither in coingecko nor cryptocompare (is an iou for FLR - SPARK)
)

UNSUPPORTED_BITTREX_ASSETS = (
    # 4ART, As of 22/07/2020 no data found outside of Bittrex
    '4ART',
    # APIX, As of 19/12/2019 no data found outside of Bittrex
    # https://medium.com/apisplatform/apix-trading-open-on-bittrex-global-61653fa346fa
    'APIX',
    # APM Coin. As of 16/11/2019 no data found outside of Bittrex for this token
    # https://global.bittrex.com/Market/Index?MarketName=BTC-APM
    'APM',
    # Tether CNH. As of 30/09/2019 no data found outside of Bittrex for this token
    # https://medium.com/bittrex/new-bittrex-international-listing-tether-cnh-cnht-c9ad966ac303
    'CNHT',
    # Credit coin. As of 29/01/2020 no data found outside of Bittrex for this token
    # https://global.bittrex.com/Market/Index?MarketName=BTC-CTC
    'CTC',
    # Foresting. As of 22/03/2019 no data found.
    # Only exists in bittrex. Perhaps it will soon be added to other APIs.
    # https://international.bittrex.com/Market/Index?MarketName=BTC-PTON
    'PTON',
    # VDX IEO. As of 16/05/2019 no data found.
    # Only exists in bittrex. Perhaps it will soon be added to other APIs.
    # https://international.bittrex.com/Market/Index?MarketName=BTC-VDX
    'VDX',
    # Origo. As of 02/06/2019 no data found outside of bittrex
    # https://international.bittrex.com/Market/Index?MarketName=BTC-OGO
    'OGO',
    # OriginChain. As of 29/01/2021 no cryptocompare/coingecko data
    # https://medium.com/bittrexglobal/new-listing-originchain-ogt-b119736dd3f6
    'OGT',
    # STPT. As of 06/06/2019 no data found outside of bittrex
    # https://twitter.com/BittrexIntl/status/1136045052164227079
    'STPT',
    # PHNX. As of 07/06/2020 no data found outside of bittrex for PhoenixDAO
    # https://www.coingecko.com/en/coins/phoenixdao
    'PHNX',
    # PROM. As of 28/06/2019 no data found outside of bittrex for Prometheus
    # https://twitter.com/BittrexIntl/status/1144290718325858305
    'PROM',
    # URAC. As of 12/07/2019 no data found outside of bittrex for Uranus
    # https://twitter.com/BittrexIntl/status/1149370485735591936
    'URAC',
    # BRZ. As of 16/06/2019 no data found outside of Bittrex for this token
    # https://twitter.com/BittrexIntl/status/1150870819758907393
    'BRZ',
    # HINT. As of 28/07/2019 no data found outside of Bittrex for this token
    # https://twitter.com/BittrexIntl/status/1154445165257474051
    'HINT',
    # TUDA. As of 02/08/2019 no data found outside of Bittrex for this token
    # https://mobile.twitter.com/BittrexIntl/status/1156974900986490880
    'TUDA',
    # TwelveShips. As of 23/08/2019 no data found outside of Bittrex for this token
    # https://twitter.com/BittrexIntl/status/1164689364997353472
    'TSHP',
    # BlockTV. As of 29/11/2019 no data found outside of Bittrex for this token
    # https://global.bittrex.com/Market/Index?MarketName=BTC-BLTV
    'BLTV',
    # Forkspot. As for 01/03/2020 no data found outside of Bittrex for this token
    # https://global.bittrex.com/Market/Index?MarketName=BTC-FRSP
    'FRSP',
    # Universal Protocol Token. As of 19/03/2020 no data found outside of Bittrex for this token.
    # https://global.bittrex.com/Market/Index?MarketName=BTC-UPT
    'UPT',
    # Universal USD and EUR. As of 19/03/2020 no data found outside of Bittrex for this token.
    # https://global.bittrex.com/Market/Index?MarketName=BTC-UPUSD
    'UPEUR',
    'UPUSD',
    # Vanywhere. As of 19/03/2020 no data found outside of Bittrex for this token.
    # https://global.bittrex.com/Market/Index?MarketName=BTC-VANY
    'VANY',
    # Ecochain. As of 22/07/2020 no data found outside of Bittrex for this token.
    # All ECOC data refer to a different coin called EcoCoin
    'ECOC',
    # As of 28/08/2020 the following assets don't have prices listed anywhere
    'FME',
    'INX',
    'MFA',
    'FCT2',  # neither in coingecko nor cryptocompare
    'UPXAU',  # neither in coingecko nor cryptocompare
    'TEA',  # neither in coingecko nor cryptocompare
    'PANDO',  # neither in coingecko nor cryptocompare (own blockchain, released on 2020)
    # bittrex tokenized stocks -- not sure how to handle yet
    'AAPL',
    'AMC',
    'AMZN',
    'BABA',
    'BB',
    'BILI',
    'BNTX',
    'BYND',
    'FB',
    'GME',
    'GOOGL',
    'MSTR',
    'NFLX',
    'NOK',
    'PFE',
    'SLV',  # iShares Silver Trust
    'SPY',
    'SQ',
    'TSLA',
)


UNSUPPORTED_BINANCE_ASSETS = (
    'ETF',  # ETF is a dead coin given to all ETH holders. Just ignore
    # BTCB, USDSB, BGBP are not yet supported anywhere else
    'BTCB',  # https://www.binance.com/en/support/articles/360029288972
    'USDSB',  # https://www.binance.com/en/support/articles/360029522132
    'BGBP',  # https://www.binance.com/en/support/articles/360030827252
    'TUSDB',  # https://www.binance.com/en/support/articles/360032154071
    'NGN',  # https://www.binance.com/en/support/articles/360035511611
    '123',  # https://twitter.com/rotkiapp/status/1161977327078838272
    '456',  # https://twitter.com/rotkiapp/status/1161977327078838272
    'UNIDOWN',  # no cryptocompare/coingecko data
    'UNIUP',  # no cryptocompare/coingecko data
    'SXPDOWN',  # no cryptocompare/coingecko data
    'SXPUP',  # no cryptocompare/coingecko data
    'AAVEDOWN',  # no cryptocompare/coingecko data
    'AAVEUP',  # no cryptocompare/coingecko data
    'SUSHIDOWN',  # no cryptocompare/coingecko data
    'SUSHIUP',  # no cryptocompare/coingecko data
    'XLMDOWN',  # no cryptocompare/coingecko data
    'XLMUP',  # no cryptocompare/coingecko data
    'UAH',  # no cryptocompare/coingecko data
)

UNSUPPORTED_BITFINEX_ASSETS = (
    'BCHN',  # https://www.bitfinex.com/posts/566  no cryptocompare/coingecko data
    'B21X',  # no cryptocompare/coingecko data
    'GTX',  # no cryptocompare/coingecko data (GT, Gate.io token)
    'IQX',  # no cryptocompare/coingecko data (EOS token)
)

# https://api.kucoin.com/api/v1/currencies
UNSUPPORTED_KUCOIN_ASSETS = (
    'AXE',  # delisted
    'BTCP',  # delisted
    'CADH',  # no cryptocompare/coingecko data
    'EPRX',  # delisted and no cryptocompare/coingecko data
    'ETF',  # delisted and no cryptocompare/coingecko data
    'GGC',  # delisted and no cryptocompare/coingecko data
    'GMB',  # delisted
    'GOD',  # delisted
    'GZIL',  # delisted
    'KTS',  # delisted
    'LOL',  # delisted
    'MAP2',  # delisted
    'MHC',  # delisted
    'SATT',  # delisted
    'SERO',  # delisted
    'SPRK',  # delisted
    'TNC2',  # delisted and no cryptocompare/coingecko data
    'TT',  # delisted
    'VNX',  # delisted and no cryptocompare/coingecko data
    'VOL',  # delisted
)

# https://api.iconomi.com/v1/assets marks delisted assets
UNSUPPORTED_ICONOMI_ASSETS = (
    'ICNGS',
    'FTR',  # delisted
    'TT',  # delisted
)

# Exchange symbols that are clearly for testing purposes. They appear in all
# these places: supported currencies list, supported exchange pairs list and
# currency map.
BITFINEX_EXCHANGE_TEST_ASSETS = (
    'AAA',
    'BBB',
    'TESTBTC',
    'TESTBTCF0',
    'TESTUSD',
    'TESTUSDT',
    'TESTUSDTF0',
)


POLONIEX_TO_WORLD = {v: k for k, v in WORLD_TO_POLONIEX.items()}
BITTREX_TO_WORLD = {v: k for k, v in WORLD_TO_BITTREX.items()}
BINANCE_TO_WORLD = {v: k for k, v in WORLD_TO_BINANCE.items()}
BITFINEX_TO_WORLD = {v: k for k, v in WORLD_TO_BITFINEX.items()}
KRAKEN_TO_WORLD = {v: k for k, v in WORLD_TO_KRAKEN.items()}
KUCOIN_TO_WORLD = {v: k for k, v, in WORLD_TO_KUCOIN.items()}
ICONOMI_TO_WORLD = {v: k for k, v in WORLD_TO_ICONOMI.items()}

RENAMED_BINANCE_ASSETS = {
    # The old BCC in binance forked into BCHABC and BCHSV
    # but for old trades the canonical chain is ABC (BCH in rotkehlchen)
    'BCC': 'BCH',
    # HCash (HSR) got swapped for Hyperchash (HC)
    # https://support.binance.com/hc/en-us/articles/360012489731-Binance-Supports-Hcash-HSR-Mainnet-Swap-to-HyperCash-HC-
    'HSR': 'HC',
    # Red pulse got swapped for Phoenix
    # https://support.binance.com/hc/en-us/articles/360012507711-Binance-Supports-Red-Pulse-RPX-Token-Swap-to-PHOENIX-PHX-
    'RPX': 'PHX',
}

ETH_TOKENS_MOVED_TO_OWN_CHAIN = {
    'NET': 'NIM',
    'EOS': 'EOS',
    'META': 'META',
}


def asset_from_kraken(kraken_name: str) -> Asset:
    """May raise:
    - DeserializationError
    - UnknownAsset
    """
    if not isinstance(kraken_name, str):
        raise DeserializationError(f'Got non-string type {type(kraken_name)} for kraken asset')

    if kraken_name.endswith('.S') or kraken_name.endswith('.M'):
        # this is a staked coin. For now since we don't show staked coins
        # consider it as the normal version. In the future we may perhaps
        # differentiate between them in the balances https://github.com/rotki/rotki/issues/569
        kraken_name = kraken_name[:-2]

    if kraken_name.endswith('.HOLD'):
        kraken_name = kraken_name[:-5]

    # Some names are not in the map since kraken can have multiple representations
    # depending on the pair for the same asset. For example XXBT and XBT, XETH and ETH,
    # ZUSD and USD
    if kraken_name == 'SETH':
        name = 'ETH2'
    elif kraken_name == 'XBT':
        name = 'BTC'
    elif kraken_name == 'XDG':
        name = 'DOGE'
    elif kraken_name in ('ETH', 'EUR', 'USD', 'GBP', 'CAD', 'JPY', 'KRW', 'CHF', 'AUD'):
        name = kraken_name
    else:
        name = KRAKEN_TO_WORLD.get(kraken_name, kraken_name)
    return Asset(name)


def asset_from_poloniex(poloniex_name: str) -> Asset:
    """May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    """
    if not isinstance(poloniex_name, str):
        raise DeserializationError(f'Got non-string type {type(poloniex_name)} for poloniex asset')

    if poloniex_name in UNSUPPORTED_POLONIEX_ASSETS:
        raise UnsupportedAsset(poloniex_name)

    our_name = POLONIEX_TO_WORLD.get(poloniex_name, poloniex_name)
    return Asset(our_name)


def asset_from_bitfinex(
        bitfinex_name: str,
        currency_map: Dict[str, str],
        is_currency_map_updated: bool = True,
) -> Asset:
    """May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset

    Currency map coming from `<Bitfinex>._query_currency_map()` is already
    updated with BITFINEX_TO_WORLD (prevent updating it on each call)
    """
    if not isinstance(bitfinex_name, str):
        raise DeserializationError(f'Got non-string type {type(bitfinex_name)} for bitfinex asset')

    if bitfinex_name in UNSUPPORTED_BITFINEX_ASSETS:
        raise UnsupportedAsset(bitfinex_name)

    if is_currency_map_updated is False:
        currency_map.update(BITFINEX_TO_WORLD)

    name = currency_map.get(bitfinex_name, bitfinex_name)
    return Asset(name)


def asset_from_bitstamp(bitstamp_name: str) -> Asset:
    """May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    """
    if not isinstance(bitstamp_name, str):
        raise DeserializationError(f'Got non-string type {type(bitstamp_name)} for bitstamp asset')

    return Asset(bitstamp_name)


def asset_from_bittrex(bittrex_name: str) -> Asset:
    """May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    """
    if not isinstance(bittrex_name, str):
        raise DeserializationError(f'Got non-string type {type(bittrex_name)} for bittrex asset')

    if bittrex_name in UNSUPPORTED_BITTREX_ASSETS:
        raise UnsupportedAsset(bittrex_name)

    name = BITTREX_TO_WORLD.get(bittrex_name, bittrex_name)
    return Asset(name)


def asset_from_binance(binance_name: str) -> Asset:
    """May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    """
    if not isinstance(binance_name, str):
        raise DeserializationError(f'Got non-string type {type(binance_name)} for binance asset')

    if binance_name in UNSUPPORTED_BINANCE_ASSETS:
        raise UnsupportedAsset(binance_name)

    if binance_name in RENAMED_BINANCE_ASSETS:
        return Asset(RENAMED_BINANCE_ASSETS[binance_name])

    name = BINANCE_TO_WORLD.get(binance_name, binance_name)
    return Asset(name)


def asset_from_coinbase(cb_name: str, time: Optional[Timestamp] = None) -> Asset:
    """May raise UnknownAsset
    """
    # During the transition from DAI(SAI) to MCDAI(DAI) coinbase introduced an MCDAI
    # wallet for the new DAI during the transition period. We should be able to handle this
    # https://support.coinbase.com/customer/portal/articles/2982947
    if cb_name == 'MCDAI':
        return A_DAI
    if cb_name == 'DAI':
        # If it's dai and it's queried from the exchange before the end of the upgrade
        if not time:
            time = ts_now()
        if time < COINBASE_DAI_UPGRADE_END_TS:
            # Then it should be the single collateral version
            return A_SAI
        # else
        return A_DAI

    # else
    return Asset(cb_name)


def asset_from_kucoin(kucoin_name: str) -> Asset:
    """May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    """
    if not isinstance(kucoin_name, str):
        raise DeserializationError(f'Got non-string type {type(kucoin_name)} for kucoin asset')

    if kucoin_name in UNSUPPORTED_KUCOIN_ASSETS:
        raise UnsupportedAsset(kucoin_name)

    name = KUCOIN_TO_WORLD.get(kucoin_name, kucoin_name)
    return Asset(name)
