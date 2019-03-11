import sys
from typing import Any, Dict


def typeinfo_check(
        asset_symbol: str,
        our_asset: Dict[str, Any],
        paprika_data: Dict[str, Any],
):
    # Process whether the is_active info agree
    if 'active' in our_asset and our_asset['active'] != paprika_data['is_active']:
        print(
            f'Our data believe that {asset_symbol} active is {our_asset["active"]} '
            f'but coin paprika believes active is {paprika_data["is_active"]}',
        )
        sys.exit(1)

    # Process whether the type info agree
    mismatch = (
        (our_asset['type'] == 'own chain' and paprika_data['type'] != 'coin') or
        (our_asset['type'] == 'ethereum token' and paprika_data['type'] != 'token') or
        (our_asset['type'] == 'omni token' and paprika_data['type'] != 'token') or
        (our_asset['type'] == 'ethereum token and own chain' and paprika_data['type'] != 'coin')
    )
    if mismatch:
        print(
            f'Our data believe that {asset_symbol} type is {our_asset["type"]} '
            f'but coin paprika believes it is {paprika_data["type"]}',
        )
        sys.exit(1)
