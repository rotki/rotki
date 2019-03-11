import sys
from typing import Any, Dict


def active_check(
        asset_symbol: str,
        our_asset: Dict[str, Any],
        our_data: Dict[str, Any],
        paprika_data: Dict[str, Any],
        cmc_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Process the active attribute from coin paprika and coinmarketcap

    Then compare to our data and provide choices to clean up the data.
    """
    our_active = our_asset.get('active', None)
    cmc_active = None
    if cmc_data:
        cmc_active = True if cmc_data['is_active'] == 1 else False
    paprika_active = None
    if paprika_data:
        paprika_active = paprika_data['is_active']

    if our_active:
        if paprika_active != our_active:
            print(
                f"For asset {asset_symbol}'s 'is_active' our data and "
                f"coin paprika do not agree.",
            )
            sys.exit(1)

    if cmc_data and paprika_data and cmc_active != paprika_active:
        print(
            f"For asset {asset_symbol}'s 'is_active' our coin paprika and "
            f"coinmarketcap do not agree.",
        )
        sys.exit(1)

    # If we get here and externals say it's not active then set it so
    if our_active is None and paprika_data and paprika_active is False:
        print(f'External APIs tell us that {asset_symbol} is not currently active')
        our_data[asset_symbol]['active'] = paprika_active

    return our_data
