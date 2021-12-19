from typing import Any, Dict, Optional

import requests
from eth_utils.address import to_checksum_address

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.exchanges.data_structures import BinancePair
from rotkehlchen.globaldb.handler import GlobalDBHandler


def get_key_if_has_val(mapping: Dict[str, Any], key: str) -> Optional[str]:
    """Gets the key from mapping if it exists and has a value (non empty string)

    The assumption here is that the value of the key is str. If it's not str
    then this function will attempt to turn it into one.
    """
    val = mapping.get(key, None)
    # empty string has falsy value
    return str(val) if val else None


def deserialize_asset_movement_address(
        mapping: Dict[str, Any],
        key: str,
        asset: Asset,
) -> Optional[str]:
    """Gets the address from an asset movement mapping making sure that if it's
    an ethereum deposit/withdrawal the address is returned checksummed"""
    value = get_key_if_has_val(mapping, key)
    if value and asset == A_ETH:
        try:
            value = to_checksum_address(value)
        except ValueError:
            value = None

    return value


def query_binance_exchange_pairs(ignore_cache: bool = False) -> Dict[str, BinancePair]:
    if not ignore_cache:
        last_pair_check = Timestamp(GlobalDBHandler().get_setting_value('binance_pairs_queried_at', 0))
    else:
        last_pair_check = Timestamp(0)
    if ts_now() - last_pair_check > DAY_IN_SECONDS:
        try:
            data = requests.get('https://binance.com/api/v3/exchangeInfo')
        except requests.exceptions.RequestException as e:
            log.debug(f'Failed to obtain market pairs from binance. {str(e)}')
            # If request fails try to get them from 
            database_pairs = GlobalDBHandler().get_binance_pairs()
            pairs = {pair['symbol']: pair for pair in database_pairs}
        pairs = create_binance_symbols_to_pair(data.json())
        GlobalDBHandler().save_binance_pairs(pairs.values())
    else:
        database_pairs = GlobalDBHandler().get_binance_pairs()
        pairs = {pair['symbol']: pair for pair in database_pairs}
    return pairs
