import logging
from collections.abc import Callable
from json.decoder import JSONDecodeError
from typing import Any

import requests
from eth_utils.address import to_checksum_address

from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.assets.converters import asset_from_binance
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, UnprocessableTradePair, UnsupportedAsset
from rotkehlchen.exchanges.data_structures import BinancePair
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.binance import GlobalDBBinance
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location, Timestamp
from rotkehlchen.utils.misc import ts_now

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def get_key_if_has_val(mapping: dict[str, Any], key: str) -> str | None:
    """Gets the key from mapping if it exists and has a value (non empty string)

    The assumption here is that the value of the key is str. If it's not str
    then this function will attempt to turn it into one.
    """
    val = mapping.get(key)
    # empty string has falsy value
    return str(val) if val else None


def deserialize_asset_movement_address(
        mapping: dict[str, Any],
        key: str,
        asset: Asset,
) -> str | None:
    """Gets the address from an asset movement mapping making sure that if it's
    an ethereum deposit/withdrawal the address is returned checksummed"""
    value = get_key_if_has_val(mapping, key)
    if value and (asset == A_ETH or asset.is_evm_token()):
        try:
            value = to_checksum_address(value)
        except ValueError:
            value = None

    return value


def create_binance_symbols_to_pair(
        exchange_data: dict[str, Any],
        location: Location,
) -> dict[str, BinancePair]:
    """Parses the result of 'exchangeInfo' endpoint and creates the symbols_to_pair mapping

    May raise:
    - KeyError if the given exchange data has unexpected format
    """
    result: dict[str, BinancePair] = {}
    for symbol in exchange_data['symbols']:
        symbol_str = symbol['symbol']
        if isinstance(symbol_str, FVal):
            # the to_int here may raise but should never due to the if check above
            symbol_str = str(symbol_str.to_int(exact=True))
        try:
            result[symbol_str] = BinancePair(
                symbol=symbol_str,
                base_asset=asset_from_binance(symbol['baseAsset']),
                quote_asset=asset_from_binance(symbol['quoteAsset']),
                location=location,
            )
        except (UnknownAsset, UnsupportedAsset) as e:
            log.debug(f'Found binance pair with no processable asset. {e!s}')
    return result


def query_binance_exchange_pairs(location: Location) -> dict[str, BinancePair]:
    """Query all the binance pairs for a valid binance location (binance or binanceus).
    This function first tries to update the list of known pairs and store them in the database.
    If it fails tries to return available information in the database.

    May raise:
    - InputError when adding the pairs to the database fails
    """
    db = GlobalDBHandler()
    last_pair_check_ts = Timestamp(
        db.get_setting_value(f'binance_pairs_queried_at_{location}', 0),
    )
    gdb_binance = GlobalDBBinance(db)

    assert location in (Location.BINANCE, Location.BINANCEUS), f'Invalid location used as argument for binance pair query. {location}'  # noqa: E501
    if location == Location.BINANCE:
        url = 'https://api.binance.com/api/v3/exchangeInfo'
    elif location == Location.BINANCEUS:
        url = 'https://api.binance.us/api/v3/exchangeInfo'

    if ts_now() - last_pair_check_ts > DAY_IN_SECONDS:
        try:
            response = requests.get(url, timeout=CachedSettings().get_timeout_tuple())
            pairs = create_binance_symbols_to_pair(
                exchange_data=response.json(),
                location=location,
            )
        except (JSONDecodeError, requests.exceptions.RequestException, KeyError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key: {msg} in Binance response: {response.text}'
            log.debug(f'Failed to obtain market pairs from {location}. {msg}')
            # If request fails try to get them from the database
            database_pairs = gdb_binance.get_all_binance_pairs(location)
            return {pair.symbol: pair for pair in database_pairs}
        gdb_binance.save_all_binance_pairs(new_pairs=pairs.values(), location=location)
    else:
        database_pairs = gdb_binance.get_all_binance_pairs(location)
        pairs = {pair.symbol: pair for pair in database_pairs}
    return pairs


def pair_symbol_to_base_quote(
        symbol: str,
        asset_deserialize_fn: Callable[[str], AssetWithOracles],
        five_letter_assets: tuple[str, ...],
        six_letter_assets: tuple[str, ...] | None = None,
) -> tuple[AssetWithOracles, AssetWithOracles]:
    """Turns a symbol product into a base/quote asset tuple. Currently used for gemini and bybit.

    - Can raise UnprocessableTradePair if symbol is in unexpected format
    - Case raise UnknownAsset if any of the pair assets are not known to rotki
    """
    if len(symbol) == 5:
        base_asset = asset_deserialize_fn(symbol[:2].upper())
        quote_asset = asset_deserialize_fn(symbol[2:].upper())
    elif len(symbol) == 6:
        try:
            base_asset = asset_deserialize_fn(symbol[:3].upper())
            quote_asset = asset_deserialize_fn(symbol[3:].upper())
        except UnknownAsset:
            base_asset = asset_deserialize_fn(symbol[:2].upper())
            quote_asset = asset_deserialize_fn(symbol[2:].upper())
    elif len(symbol) == 7:
        try:
            base_asset = asset_deserialize_fn(symbol[:4].upper())
            quote_asset = asset_deserialize_fn(symbol[4:].upper())
        except UnknownAsset:
            base_asset = asset_deserialize_fn(symbol[:3].upper())
            quote_asset = asset_deserialize_fn(symbol[3:].upper())
    elif len(symbol) == 8:
        if any(asset in symbol for asset in five_letter_assets):
            base_asset = asset_deserialize_fn(symbol[:5].upper())
            quote_asset = asset_deserialize_fn(symbol[5:].upper())
        else:
            base_asset = asset_deserialize_fn(symbol[:4].upper())
            quote_asset = asset_deserialize_fn(symbol[4:].upper())
    elif len(symbol) == 9:
        if any(asset in symbol for asset in five_letter_assets):
            base_asset = asset_deserialize_fn(symbol[:5].upper())
            quote_asset = asset_deserialize_fn(symbol[5:].upper())
        else:
            base_asset = asset_deserialize_fn(symbol[:6].upper())
            quote_asset = asset_deserialize_fn(symbol[6:].upper())
    elif len(symbol) == 10 and six_letter_assets is not None:
        if any(asset in symbol for asset in six_letter_assets):
            base_asset = asset_deserialize_fn(symbol[:6].upper())
            quote_asset = asset_deserialize_fn(symbol[6:].upper())
    else:
        raise UnprocessableTradePair(symbol)

    return base_asset, quote_asset
