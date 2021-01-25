from typing import Any, Dict, Optional

from eth_utils.address import to_checksum_address

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_ETH


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
