from collections.abc import Callable

from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.assets.utils import symbol_to_asset_or_token
from rotkehlchen.constants.assets import A_DAI, A_SAI
from rotkehlchen.constants.resolver import strethaddress_to_identifier
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.types import Location, Timestamp
from rotkehlchen.utils.misc import ts_now

COINBASE_DAI_UPGRADE_END_TS = 1575244800  # December 2

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
    'TESTMATIC',
    'TESTSOL',
    'TESTSOLF0',
    'TESTXAUT',
    'TESTXAUTF0',
)

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


def asset_from_kraken(kraken_name: str) -> AssetWithOracles:
    """May raise:
    - DeserializationError
    - UnknownAsset
    """
    if not isinstance(kraken_name, str):
        raise DeserializationError(f'Got non-string type {type(kraken_name)} for kraken asset')

    if kraken_name.endswith(('.S', '.M', '.P', '.F', '.B')):
        # this is a special staked/allocated coin. Map to the normal version
        # https://support.kraken.com/hc/en-us/articles/360039879471-What-is-Asset-S-and-Asset-M-
        kraken_name = kraken_name[:-2]

        if kraken_name != 'ETH2':
            while kraken_name[-1].isdigit():  # get rid of bonded number days assets
                kraken_name = kraken_name[:-1]  # see https://github.com/rotki/rotki/issues/6587

    kraken_name = kraken_name.removesuffix('.HOLD')

    # Some names are not in the map since kraken can have multiple representations
    # depending on the pair for the same asset. For example XXBT and XBT, XETH and ETH,
    # ZUSD and USD
    if kraken_name == 'SETH':
        name = 'ETH2'
    elif kraken_name == 'XBT':
        name = 'BTC'
    elif kraken_name == 'XDG':
        name = 'DOGE'
    elif kraken_name == 'FLOWH':
        name = 'FLOW'
    elif kraken_name in {'ETH', 'EUR', 'USD', 'GBP', 'CAD', 'JPY', 'KRW', 'CHF', 'AUD'}:
        name = kraken_name
    else:
        name = GlobalDBHandler.get_assetid_from_exchange_name(
            exchange=Location.KRAKEN,
            symbol=kraken_name,
            default=kraken_name,
        )
    return symbol_to_asset_or_token(name)


def asset_from_poloniex(poloniex_name: str) -> AssetWithOracles:
    """May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    """
    if not isinstance(poloniex_name, str):
        raise DeserializationError(f'Got non-string type {type(poloniex_name)} for poloniex asset')

    return symbol_to_asset_or_token(GlobalDBHandler.get_assetid_from_exchange_name(
        exchange=Location.POLONIEX,
        symbol=poloniex_name,
        default=poloniex_name,
    ))


def asset_from_bitfinex(bitfinex_name: str) -> AssetWithOracles:
    """May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset

    Currency map fetched in `<Bitfinex>._query_currency_map()` is already
    inserted into location_asset_mappings (prevent updating it on each call)
    """
    if not isinstance(bitfinex_name, str):
        raise DeserializationError(f'Got non-string type {type(bitfinex_name)} for bitfinex asset')

    return symbol_to_asset_or_token(GlobalDBHandler.get_assetid_from_exchange_name(
        exchange=Location.BITFINEX,
        symbol=bitfinex_name,
        default=bitfinex_name,
    ))


def asset_from_bitstamp(bitstamp_name: str) -> AssetWithOracles:
    """May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    """
    if not isinstance(bitstamp_name, str):
        raise DeserializationError(f'Got non-string type {type(bitstamp_name)} for bitstamp asset')

    # bitstamp assets are read as lowercase from the exchange
    return symbol_to_asset_or_token(GlobalDBHandler.get_assetid_from_exchange_name(
        exchange=Location.BITSTAMP,
        symbol=bitstamp_name.upper(),
        default=bitstamp_name,
    ))


def asset_from_bittrex(bittrex_name: str) -> AssetWithOracles:
    """May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    """
    if not isinstance(bittrex_name, str):
        raise DeserializationError(f'Got non-string type {type(bittrex_name)} for bittrex asset')

    return symbol_to_asset_or_token(GlobalDBHandler.get_assetid_from_exchange_name(
        exchange=Location.BITTREX,
        symbol=bittrex_name,
        default=bittrex_name,
    ))


def asset_from_coinbasepro(coinbase_pro_name: str) -> AssetWithOracles:
    """May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    """
    if not isinstance(coinbase_pro_name, str):
        raise DeserializationError(
            f'Got non-string type {type(coinbase_pro_name)} for '
            f'coinbasepro asset',
        )
    return symbol_to_asset_or_token(GlobalDBHandler.get_assetid_from_exchange_name(
        exchange=Location.COINBASEPRO,
        symbol=coinbase_pro_name,
        default=coinbase_pro_name,
    ))


def asset_from_binance(binance_name: str) -> AssetWithOracles:
    """May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    """
    if not isinstance(binance_name, str):
        raise DeserializationError(f'Got non-string type {type(binance_name)} for binance asset')

    if binance_name in RENAMED_BINANCE_ASSETS:
        return Asset(RENAMED_BINANCE_ASSETS[binance_name]).resolve_to_asset_with_oracles()

    return symbol_to_asset_or_token(GlobalDBHandler.get_assetid_from_exchange_name(
        exchange=Location.BINANCE,
        symbol=binance_name,
        default=binance_name,
    ))


def asset_from_coinbase(cb_name: str, time: Timestamp | None = None) -> AssetWithOracles:
    """May raise:
    - DeserializationError
    - UnknownAsset
    """
    # During the transition from DAI(SAI) to MCDAI(DAI) coinbase introduced an MCDAI
    # wallet for the new DAI during the transition period. We should be able to handle this
    # https://support.coinbase.com/customer/portal/articles/2982947
    if cb_name == 'MCDAI':
        return A_DAI.resolve_to_asset_with_oracles()
    if cb_name == 'DAI':
        # If it's dai and it's queried from the exchange before the end of the upgrade
        if not time:
            time = ts_now()
        if time < COINBASE_DAI_UPGRADE_END_TS:
            # Then it should be the single collateral version
            return A_SAI.resolve_to_asset_with_oracles()
        return A_DAI.resolve_to_asset_with_oracles()

    if not isinstance(cb_name, str):
        raise DeserializationError(f'Got non-string type {type(cb_name)} for coinbase asset')

    return symbol_to_asset_or_token(GlobalDBHandler.get_assetid_from_exchange_name(
        exchange=Location.COINBASE,
        symbol=cb_name.upper(),  # the upper is needed since Coinbase Prime uses lower case symbols in some places  # noqa: E501
        default=cb_name,
    ))


def asset_from_kucoin(kucoin_name: str) -> AssetWithOracles:
    """May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    """
    if not isinstance(kucoin_name, str):
        raise DeserializationError(f'Got non-string type {type(kucoin_name)} for kucoin asset')

    return symbol_to_asset_or_token(GlobalDBHandler.get_assetid_from_exchange_name(
        exchange=Location.KUCOIN,
        symbol=kucoin_name,
        default=kucoin_name,
    ))


def asset_from_gemini(symbol: str) -> AssetWithOracles:
    """May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    """
    if not isinstance(symbol, str):
        raise DeserializationError(f'Got non-string type {type(symbol)} for gemini asset')

    return symbol_to_asset_or_token(GlobalDBHandler.get_assetid_from_exchange_name(
        exchange=Location.GEMINI,
        symbol=symbol,
        default=symbol,
    ))


def asset_from_blockfi(symbol: str) -> AssetWithOracles:
    """May raise:
    - DeserializationError
    - UnknownAsset
    """
    if not isinstance(symbol, str):
        raise DeserializationError(f'Got non-string type {type(symbol)} for blockfi asset')

    symbol = symbol.upper()
    return symbol_to_asset_or_token(GlobalDBHandler.get_assetid_from_exchange_name(
        exchange=Location.BLOCKFI,
        symbol=symbol,
        default=symbol,
    ))


def asset_from_iconomi(symbol: str) -> AssetWithOracles:
    """May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    """
    if not isinstance(symbol, str):
        raise DeserializationError(f'Got non-string type {type(symbol)} for iconomi asset')
    symbol = symbol.upper()

    return symbol_to_asset_or_token(GlobalDBHandler.get_assetid_from_exchange_name(
        exchange=Location.ICONOMI,
        symbol=symbol,
        default=symbol,
    ))


def asset_from_uphold(symbol: str) -> AssetWithOracles:
    """May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    """
    if not isinstance(symbol, str):
        raise DeserializationError(f'Got non-string type {type(symbol)} for uphold asset')

    return symbol_to_asset_or_token(GlobalDBHandler.get_assetid_from_exchange_name(
        exchange=Location.UPHOLD,
        symbol=symbol,
        default=symbol,
    ))


def asset_from_nexo(nexo_name: str) -> AssetWithOracles:
    """May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    """
    if not isinstance(nexo_name, str):
        raise DeserializationError(f'Got non-string type {type(nexo_name)} for nexo asset')

    if nexo_name == 'USDTERC':  # map USDTERC to USDT
        nexo_name = strethaddress_to_identifier('0xdAC17F958D2ee523a2206206994597C13D831ec7')

    return symbol_to_asset_or_token(GlobalDBHandler.get_assetid_from_exchange_name(
        exchange=Location.NEXO,
        symbol=nexo_name,
        default=nexo_name,
    ))


def asset_from_bitpanda(bitpanda_name: str) -> AssetWithOracles:
    """May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    """
    if not isinstance(bitpanda_name, str):
        raise DeserializationError(f'Got non-string type {type(bitpanda_name)} for bitpanda asset')

    return symbol_to_asset_or_token(GlobalDBHandler.get_assetid_from_exchange_name(
        exchange=Location.BITPANDA,
        symbol=bitpanda_name,
        default=bitpanda_name,
    ))


def asset_from_cryptocom(cryptocom_name: str) -> AssetWithOracles:
    """May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    """
    if not isinstance(cryptocom_name, str):
        raise DeserializationError(
            f'Got non-string type {type(cryptocom_name)} for cryptocom asset',
        )

    return symbol_to_asset_or_token(GlobalDBHandler.get_assetid_from_exchange_name(
        exchange=Location.CRYPTOCOM,
        symbol=cryptocom_name,
        default=cryptocom_name,
    ))


def asset_from_okx(okx_name: str) -> AssetWithOracles:
    """May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    """
    if not isinstance(okx_name, str):
        raise DeserializationError(f'Got non-string type {type(okx_name)} for okx asset')

    return symbol_to_asset_or_token(GlobalDBHandler.get_assetid_from_exchange_name(
        exchange=Location.OKX,
        symbol=okx_name,
        default=okx_name,
    ))


def asset_from_ftx(ftx_name: str) -> AssetWithOracles:
    """May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    """
    if not isinstance(ftx_name, str):
        raise DeserializationError(f'Got non-string type {type(ftx_name)} for ftx asset')

    if ftx_name == 'SRM_LOCKED':
        name = strethaddress_to_identifier('0x476c5E26a75bd202a9683ffD34359C0CC15be0fF')  # SRM
    else:
        name = GlobalDBHandler.get_assetid_from_exchange_name(
            exchange=Location.FTX,
            symbol=ftx_name,
            default=ftx_name,
        )
    return symbol_to_asset_or_token(name)


def asset_from_bybit(name: str) -> AssetWithOracles:
    """May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    """
    if not isinstance(name, str):
        raise DeserializationError(f'Got non-string type {type(name)} for bybit asset')

    return symbol_to_asset_or_token(GlobalDBHandler.get_assetid_from_exchange_name(
        exchange=Location.BYBIT,
        symbol=name,
        default=name,
    ))


def asset_from_woo(woo_name: str) -> AssetWithOracles:
    """May raise:
    - DeserializationError
    - UnknownAsset
    """
    if not isinstance(woo_name, str):
        raise DeserializationError(f'Got non-string type {type(woo_name)} for woo asset')

    woo_name = GlobalDBHandler.get_assetid_from_exchange_name(
        exchange=Location.WOO,
        symbol=woo_name,
        default=woo_name.split('_', maxsplit=1)[-1],  # some woo assets are prefixed with the network for deposits/withdrawals  # noqa: E501
    )
    return symbol_to_asset_or_token(GlobalDBHandler.get_assetid_from_exchange_name(
        exchange=Location.WOO,
        symbol=woo_name,
        default=woo_name,
    ))


def asset_from_common_identifier(common_identifier: str) -> AssetWithOracles:
    """May raise:
    - DeserializationError
    - UnknownAsset
    """
    if not isinstance(common_identifier, str):
        raise DeserializationError(
            f'Got non-string type {type(common_identifier)} for an asset',
        )

    return symbol_to_asset_or_token(GlobalDBHandler.get_assetid_from_exchange_name(
        exchange=None,
        symbol=common_identifier,
        default=common_identifier,
    ))


def asset_from_htx(htx_name: str) -> AssetWithOracles:
    """May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    """
    if not isinstance(htx_name, str):
        raise DeserializationError(f'Got non-string type {type(htx_name)} for HTX asset')

    htx_name = htx_name.upper()
    return symbol_to_asset_or_token(GlobalDBHandler.get_assetid_from_exchange_name(
        exchange=Location.HTX,
        symbol=htx_name,
        default=htx_name,
    ))


def asset_from_bitcoinde(bitcoinde: str) -> AssetWithOracles:
    """May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    """
    bitcoinde = bitcoinde.upper()
    return symbol_to_asset_or_token(GlobalDBHandler.get_assetid_from_exchange_name(
        exchange=Location.BITCOINDE,
        symbol=bitcoinde,
        default=bitcoinde,
    ))


LOCATION_TO_ASSET_MAPPING: dict[Location, Callable[[str], AssetWithOracles]] = {
    Location.BINANCE: asset_from_binance,
    Location.CRYPTOCOM: asset_from_cryptocom,
    Location.BITPANDA: asset_from_bitpanda,
    Location.BITTREX: asset_from_bittrex,
    Location.COINBASEPRO: asset_from_coinbasepro,
    Location.FTX: asset_from_ftx,
    Location.KRAKEN: asset_from_kraken,
    Location.BITSTAMP: asset_from_bitstamp,
    Location.GEMINI: asset_from_gemini,
    Location.POLONIEX: asset_from_poloniex,
    Location.NEXO: asset_from_nexo,
    Location.KUCOIN: asset_from_kucoin,
    Location.OKX: asset_from_okx,
    Location.WOO: asset_from_woo,
    Location.HTX: asset_from_htx,
    Location.BITCOINDE: asset_from_bitcoinde,
    Location.EXTERNAL: asset_from_common_identifier,
}
