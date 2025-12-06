from rotkehlchen.exchanges.constants import (
    ALL_SUPPORTED_EXCHANGES,
    EXCHANGES_WITH_PASSPHRASE,
    EXCHANGES_WITHOUT_API_SECRET,
    EXPERIMENTAL_EXCHANGES,
    SUPPORTED_EXCHANGES,
)
from rotkehlchen.types import Location

LOCATION_DETAILS: dict = {
    Location.EXTERNAL: {'icon': 'lu-book-text'},
    Location.KRAKEN: {'image': 'kraken.svg'},
    Location.POLONIEX: {'image': 'poloniex.svg'},
    Location.BITTREX: {'image': 'bittrex.svg'},
    Location.BINANCE: {'image': 'binance.svg'},
    Location.BITMEX: {'image': 'bitmex.svg'},
    Location.COINBASE: {'image': 'coinbase.svg'},
    Location.COINBASEPRIME: {'image': 'coinbaseprime.svg', 'label': 'Coinbase Prime'},
    Location.BANKS: {'icon': 'lu-landmark'},
    Location.BLOCKCHAIN: {'icon': 'lu-link'},
    Location.COINBASEPRO: {
        'image': 'coinbasepro.svg',
        'label': 'Coinbase Pro',
    },
    Location.GEMINI: {'image': 'gemini.svg'},
    Location.EQUITIES: {'icon': 'lu-luggage'},
    Location.REALESTATE: {'icon': 'lu-house'},
    Location.COMMODITIES: {'icon': 'lu-leaf'},
    Location.CRYPTOCOM: {'image': 'crypto_com.svg'},
    Location.UNISWAP: {'image': 'uniswap.svg'},
    Location.BITSTAMP: {'image': 'bitstamp.svg'},
    Location.BINANCEUS: {
        'label': 'Binance US',
        'image': 'binance.svg',
    },
    Location.BITFINEX: {'image': 'bitfinex.svg'},
    Location.BITCOINDE: {
        'label': 'Bitcoin.de',
        'image': 'btcde.svg',
    },
    Location.ICONOMI: {'image': 'iconomi.svg'},
    Location.KUCOIN: {'image': 'kucoin.svg'},
    Location.BALANCER: {'image': 'balancer.svg'},
    Location.LOOPRING: {'image': 'loopring.svg'},
    Location.FTX: {
        'label': 'FTX',
        'image': 'ftx.svg',
    },
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
    Location.OKX: {
        'label': 'OKX',
        'image': 'okx.svg',
    },
    Location.ETHEREUM: {'image': 'ethereum.svg'},
    Location.OPTIMISM: {'image': 'optimism.svg'},
    Location.POLYGON_POS: {'image': 'polygon_pos.svg'},
    Location.ARBITRUM_ONE: {'image': 'arbitrum_one.svg'},
    Location.BASE: {'image': 'base.svg'},
    Location.GNOSIS: {'image': 'gnosis.svg'},
    Location.SCROLL: {'image': 'scroll.svg'},
    Location.BINANCE_SC: {'image': 'binance_sc.svg'},
    Location.WOO: {'image': 'woo.svg'},
    Location.BYBIT: {'image': 'bybit.svg'},
    Location.HTX: {
        'label': 'HTX',
        'image': 'htx.svg',
    },
    Location.ZKSYNC_LITE: {'image': 'zksync_lite.svg'},
    Location.BITCOIN: {'image': 'bitcoin.svg'},
    Location.BITCOIN_CASH: {
        'label': 'Bitcoin Cash',
        'image': 'bitcoin-cash.svg',
    },
    Location.POLKADOT: {'image': 'polkadot.svg'},
    Location.KUSAMA: {'image': 'kusama.svg'},
    Location.SOLANA: {'image': 'solana.svg'},
    Location.KRAKENFUTURES: {'image': 'kraken.svg', 'label': 'Kraken Futures'},
}
for key, value in LOCATION_DETAILS.items():
    if key in ALL_SUPPORTED_EXCHANGES:
        if key in SUPPORTED_EXCHANGES:
            value['exchange_details'] = {'is_exchange_with_key': True}
            if key in EXCHANGES_WITH_PASSPHRASE:
                value['exchange_details']['is_exchange_with_passphrase'] = True
            if key in EXCHANGES_WITHOUT_API_SECRET:
                value['exchange_details']['is_exchange_without_api_secret'] = True
            if key in EXPERIMENTAL_EXCHANGES:
                value['exchange_details']['experimental'] = True
            continue
        value['is_exchange'] = True


def get_formatted_location_name(location: Location) -> str:
    """Get a properly formatted location name either from the location details mapping,
    or by simply capitalizing the location name.
    """
    if location in LOCATION_DETAILS and 'label' in LOCATION_DETAILS[location]:
        return LOCATION_DETAILS[location]['label']

    return str(location).capitalize()
