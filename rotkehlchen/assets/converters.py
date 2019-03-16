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
