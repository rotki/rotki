from rotkehlchen.assets.asset import WORLD_TO_CRYPTOCOMPARE, WORLD_TO_POLONIEX, Asset

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


def asset_from_kraken(kraken_name: str) -> Asset:
    return Asset(KRAKEN_TO_WORLD[kraken_name])


def asset_from_cryptocompare(cc_name: str) -> Asset:
    return Asset(CRYPTOCOMPARE_TO_WORLD[cc_name])


def asset_from_poloniex(poloniex_name: str) -> Asset:
    return Asset(POLONIEX_TO_WORLD[poloniex_name])
