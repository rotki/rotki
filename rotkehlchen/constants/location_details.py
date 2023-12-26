from rotkehlchen.exchanges.constants import (
    ALL_SUPPORTED_EXCHANGES,
    EXCHANGES_WITH_PASSPHRASE,
    EXCHANGES_WITHOUT_API_SECRET,
    SUPPORTED_EXCHANGES,
)
from rotkehlchen.types import Location

LOCATION_DETAILS: dict = {
    Location.EXTERNAL: {'icon': 'book-2-line'},
    Location.KRAKEN: {'image': 'kraken.svg'},
    Location.POLONIEX: {'image': 'poloniex.svg'},
    Location.BITTREX: {'image': 'bittrex.svg'},
    Location.BINANCE: {'image': 'binance.svg'},
    Location.BITMEX: {'image': 'bitmex.svg'},
    Location.COINBASE: {'image': 'coinbase.svg'},
    Location.BANKS: {'icon': 'bank-line'},
    Location.BLOCKCHAIN: {'icon': 'link'},
    Location.COINBASEPRO: {
        'image': 'coinbasepro.svg',
        'label': 'Coinbase Pro',
    },
    Location.GEMINI: {'image': 'gemini.svg'},
    Location.EQUITIES: {'icon': 'suitcase-2-line'},
    Location.REALESTATE: {'icon': 'home-3-line'},
    Location.COMMODITIES: {'icon': 'leaf-line'},
    Location.CRYPTOCOM: {'image': 'crypto_com.svg'},
    Location.UNISWAP: {'image': 'uniswap.svg'},
    Location.BITSTAMP: {'image': 'bitstamp.svg'},
    Location.BINANCEUS: {
        'label': 'Binance US',
        'image': 'binance.svg',
    },
    Location.BITFINEX: {'image': 'bitfinex.svg'},
    Location.BITCOINDE: {'image': 'btcde.svg'},
    Location.ICONOMI: {'image': 'iconomi.svg'},
    Location.KUCOIN: {'image': 'kucoin.svg'},
    Location.BALANCER: {'image': 'balancer.svg'},
    Location.LOOPRING: {'image': 'loopring.svg'},
    Location.FTX: {'image': 'ftx.svg'},
    Location.NEXO: {'image': 'nexo.svg'},
    Location.BLOCKFI: {'image': 'blockfi.svg'},
    Location.INDEPENDENTRESERVE: {
        'label': 'Independent Reserve',
        'image': 'independentreserve.svg',
    },
    Location.GITCOIN: {'image': 'gitcoin.svg'},
    Location.SUSHISWAP: {'image': 'sushiswap.svg'},
    Location.SHAPESHIFT: {'image': 'shapeshift.svg'},
    Location.UPHOLD: {'image': 'uphold.svg'},
    Location.BITPANDA: {'image': 'bitpanda.svg'},
    Location.BISQ: {'image': 'bisq.svg'},
    Location.FTXUS: {
        'label': 'FTX US',
        'image': 'ftxus.svg',
    },
    Location.OKX: {'image': 'okx.svg'},
    Location.ETHEREUM: {'image': 'ethereum.svg'},
    Location.OPTIMISM: {'image': 'optimism.svg'},
    Location.POLYGON_POS: {'image': 'polygon_pos.svg'},
    Location.ARBITRUM_ONE: {'image': 'arbitrum_one.svg'},
    Location.BASE: {'image': 'base.svg'},
    Location.GNOSIS: {'image': 'gnosis.svg'},
    Location.WOO: {'image': 'woo.svg'},
    Location.BYBIT: {'image': 'bybit.svg'},
}
for key, value in LOCATION_DETAILS.items():
    if key in ALL_SUPPORTED_EXCHANGES:
        value['is_exchange'] = True
        if key in SUPPORTED_EXCHANGES:
            value['exchange_data'] = {'is_exchange_with_key': True}
            if key in EXCHANGES_WITH_PASSPHRASE:
                value['exchange_data']['is_exchange_with_passphrase'] = True
            if key in EXCHANGES_WITHOUT_API_SECRET:
                value['exchange_data']['is_exchange_without_api_secret'] = True
