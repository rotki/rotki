import sys
from typing import Any, Dict


def typeinfo_check(
        asset_symbol: str,
        our_asset: Dict[str, Any],
        our_data: Dict[str, Any],
        paprika_data: Dict[str, Any],
        cmc_data: Dict[str, Any],
):
    if 'type' not in our_asset and paprika_data:
        # If our data don't have a type, derive it from external data
        if paprika_data['type'] == 'coin':
            our_data[asset_symbol]['type'] = 'own chain'
        elif paprika_data['type'] == 'token':
            if 'parent' not in paprika_data:
                print(f'Paprika data for asset {asset_symbol} should have a parent')
                sys.exit(1)

            if paprika_data['parent']['id'] == 'omni-omni':
                our_data[asset_symbol]['type'] = 'omni token'
            elif paprika_data['parent']['id'] == 'eth-ethereum':
                our_data[asset_symbol]['type'] = 'ethereum token'
            elif paprika_data['parent']['id'] == 'neo-neo':
                our_data[asset_symbol]['type'] = 'neo token'
            else:
                print(
                    f'Paprika data for asset {asset_symbol} has unknown '
                    f'parent {paprika_data["parent"]["id"]}',
                )
                sys.exit(1)
        else:
            print(f'Unexpected type {paprika_data["type"]} for asset {asset_symbol}')
            sys.exit(1)

    if not paprika_data:
        # Can't check for mismatch if paprika has no data
        assert 'type' in our_asset, f'data for {asset_symbol} do not have a type'
        return our_data

    # Process whether the type info agree
    # Also keep in mind we got the 'exchange specific' type for assets like KFEE
    # but no API has an equivalent to check it against
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

    assert 'type' in our_asset, f'data for {asset_symbol} do not have a type'
    return our_data
