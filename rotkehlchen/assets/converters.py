from rotkehlchen.assets.asset import WORLD_TO_CRYPTOCOMPARE, WORLD_TO_POLONIEX, Asset
from rotkehlchen.errors import UnsupportedAsset

KRAKEN_TO_WORLD = {
    'XDAO': 'DAO',
    'XETC': 'ETC',
    'XETH': 'ETH',
    'ETH': 'ETH',
    'XLTC': 'LTC',
    'XREP': 'REP',
    'XXBT': 'BTC',
    'XBT': 'BTC',
    'XXMR': 'XMR',
    'XXRP': 'XRP',
    'XZEC': 'ZEC',
    'ZEUR': 'EUR',
    'EUR': 'EUR',
    'ZUSD': 'USD',
    'USD': 'USD',
    'ZGBP': 'GBP',
    'GBP': 'GBP',
    'ZCAD': 'CAD',
    'CAD': 'CAD',
    'ZJPY': 'JPY',
    'JPY': 'JPY',
    'ZKRW': 'KRW',
    'KRW': 'KRW',
    'XMLN': 'MLN',
    'XICN': 'ICN',
    'GNO': 'GNO',
    'BCH': 'BCH',
    'XXLM': 'XLM',
    'DASH': 'DASH',
    'EOS': 'EOS',
    'USDT': 'USDT',
    'KFEE': 'KFEE',
    'ADA': 'ADA',
    'QTUM': 'QTUM',
    'XNMC': 'NMC',
    'XXVN': 'VEN',
    'XXDG': 'DOGE',
    'XTZ': 'XTZ',
    'BSV': 'BSV',
}

CRYPTOCOMPARE_TO_WORLD = {v: k for k, v in WORLD_TO_CRYPTOCOMPARE.items()}

POLONIEX_TO_WORLD = {v: k for k, v in WORLD_TO_POLONIEX.items()}
UNSUPPORTED_POLONIEX_ASSETS = (
    # This was a super shortlived coin.
    # Only info is here: https://bitcointalk.org/index.php?topic=632818.0
    # No price info in cryptocompare or paprika. So we don't support it.
    'AXIS',
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
)


def asset_from_kraken(kraken_name: str) -> Asset:
    return Asset(KRAKEN_TO_WORLD[kraken_name])


def asset_from_cryptocompare(cc_name: str) -> Asset:
    return Asset(CRYPTOCOMPARE_TO_WORLD[cc_name])


def asset_from_poloniex(poloniex_name: str) -> Asset:
    if poloniex_name in UNSUPPORTED_POLONIEX_ASSETS:
        raise UnsupportedAsset(poloniex_name)

    our_name = POLONIEX_TO_WORLD[poloniex_name]
    return Asset(our_name)
