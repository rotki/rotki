import sys
from typing import Any, Dict

MANUALLY_CHECKED_TYPES = {
    'AMIS': 'ethereum token',
    'AOA': 'ethereum token',
    'AVA-2': 'ethereum token',
    'BITCAR': 'ethereum token',
    'BMT': 'ethereum token',
    'BOU': 'ethereum token',
    'BTCE': 'ethereum token',
    'BTH': 'ethereum token',
    'BTR-2': 'ethereum token',
    'CET-2': 'ethereum token',
    'CFTY': 'ethereum token',
    'CO2': 'ethereum token',
    'CRGO': 'ethereum token',
    'CCRB': 'ethereum token',
    'DEPO': 'ethereum token',
    'DIP': 'ethereum token',
    'DPP': 'ethereum token',
    'DTX-2': 'ethereum token',
}


def typeinfo_check(
        asset_symbol: str,
        our_asset: Dict[str, Any],
        our_data: Dict[str, Any],
        paprika_data: Dict[str, Any],
        cmc_data: Dict[str, Any],
):
    if asset_symbol in MANUALLY_CHECKED_TYPES:
        our_data[asset_symbol]['type'] = MANUALLY_CHECKED_TYPES[asset_symbol]
        return our_data

    if 'type' not in our_asset and paprika_data:
        # If our data don't have a type, derive it from external data
        if paprika_data['type'] == 'coin':
            our_data[asset_symbol]['type'] = 'own chain'
        elif paprika_data['type'] == 'token':

            # a special case for which paprika has wrong/corrupt parent data
            if asset_symbol in ('ZIL', 'WTC'):
                our_data[asset_symbol]['type'] = 'ethereum token'
                return our_data

            if 'parent' not in paprika_data:
                print(f'Paprika data for asset {asset_symbol} should have a parent')
                sys.exit(1)

            if paprika_data['parent']['id'] == 'omni-omni':
                our_data[asset_symbol]['type'] = 'omni token'
            elif paprika_data['parent']['id'] == 'eth-ethereum':
                our_data[asset_symbol]['type'] = 'ethereum token'
            elif paprika_data['parent']['id'] == 'neo-neo':
                our_data[asset_symbol]['type'] = 'neo token'
            elif paprika_data['parent']['id'] == 'xcp-counterparty':
                our_data[asset_symbol]['type'] = 'counterparty token'
            elif paprika_data['parent']['id'] == 'bts-bitshares':
                our_data[asset_symbol]['type'] = 'bitshares token'
            elif paprika_data['parent']['id'] == 'ardr-ardor':
                our_data[asset_symbol]['type'] = 'ardor token'
            elif paprika_data['parent']['id'] == 'nxt-nxt':
                our_data[asset_symbol]['type'] = 'nxt token'
            elif paprika_data['parent']['id'] == 'ubq-ubiq':
                our_data[asset_symbol]['type'] = 'Ubiq token'
            elif paprika_data['parent']['id'] == 'usnbt-nubits':
                our_data[asset_symbol]['type'] = 'Nubits token'
            elif paprika_data['parent']['id'] == 'burst-burst':
                our_data[asset_symbol]['type'] = 'Burst token'
            elif paprika_data['parent']['id'] == 'waves-waves':
                our_data[asset_symbol]['type'] = 'waves token'
            elif paprika_data['parent']['id'] == 'qtum-qtum':
                our_data[asset_symbol]['type'] = 'qtum token'
            elif paprika_data['parent']['id'] == 'xlm-stellar':
                our_data[asset_symbol]['type'] = 'stellar token'
            elif paprika_data['parent']['id'] == 'trx-tron':
                our_data[asset_symbol]['type'] = 'tron token'
            elif paprika_data['parent']['id'] == 'ont-ontology':
                our_data[asset_symbol]['type'] = 'ontology token'
            else:
                print(
                    f'Paprika data for asset {asset_symbol} has unknown '
                    f'parent {paprika_data["parent"]["id"]}',
                )
                sys.exit(1)

        else:
            print(f'Unexpected type {paprika_data["type"]} for asset {asset_symbol}')
            sys.exit(1)

        print(f'{asset_symbol} is a {our_data[asset_symbol]["type"]}')

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
