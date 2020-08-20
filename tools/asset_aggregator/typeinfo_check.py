import sys
from typing import Any, Dict

MANUALLY_CHECKED_TYPES = {
    'ADADOWN': 'own chain',
    'ADAUP': 'own chain',
    'BTCDOWN': 'own chain',
    'BTCUP': 'own chain',
    'ETHDOWN': 'own chain',
    'ETHUP': 'own chain',
    'LINKDOWN': 'own chain',
    'LINKUP': 'own chain',
    'AMIS': 'ethereum token',
    'AOA': 'ethereum token',
    'AR': 'own chain',
    'AVA-2': 'ethereum token',
    'BAL': 'ethereum token',
    'BCHBEAR': 'ethereum token',
    'BCHBULL': 'ethereum token',
    'BEAR': 'ethereum token',
    'BULL': 'ethereum token',
    'BSVBEAR': 'ethereum token',
    'BSVBULL': 'ethereum token',
    'BITCAR': 'ethereum token',
    'BNBBEAR': 'ethereum token',
    'BNBBULL': 'ethereum token',
    'BIDR': 'binance token',
    'BMT': 'ethereum token',
    'BOU': 'ethereum token',
    'BTCE': 'ethereum token',
    'BTE': 'ethereum token',
    'BTH': 'ethereum token',
    'BTR-2': 'ethereum token',
    'BZRX': 'ethereum token',
    'CET-2': 'ethereum token',
    'CFTY': 'ethereum token',
    'CELO': 'own chain',
    'CGLD': 'own chain',
    'CNTM': 'ethereum token',
    'CTSI': 'ethereum token',
    'CO2': 'ethereum token',
    'CRGO': 'ethereum token',
    'CCRB': 'ethereum token',
    'DAWN': 'ethereum token',
    'DEPO': 'ethereum token',
    'DEC-2': 'ethereum token',
    'DEP': 'ethereum token',
    'DIP': 'ethereum token',
    'DPP': 'ethereum token',
    'DTX-2': 'ethereum token',
    'DUSK': 'ethereum token',
    'EMT': 'ethereum token',
    'ENTRP': 'ethereum token',
    'ETHBEAR': 'ethereum token',
    'ETHBULL': 'ethereum token',
    'EOSDAC': 'ethereum token',
    'ERD': 'binance token',
    'ELAMA': 'ethereum token',
    'ETHB': 'ethereum token',
    'ETHD': 'ethereum token',
    'EOSBEAR': 'ethereum token',
    'EOSBULL': 'ethereum token',
    'FIH': 'ethereum token',
    'FORK-2': 'ethereum token',
    'HBD': 'own chain',
    'HDAO': 'ethereum token',
    'HIVE': 'own chain',
    'HKG': 'ethereum token',
    'HNS': 'own chain',
    'ITM': 'ethereum token',
    'IQ': 'eos token',
    'JOY': 'ethereum token',
    'JST': 'tron token',
    'KDAG': 'ethereum token',
    'KSM': 'own chain',
    'KUE': 'ethereum token',
    'LCT-2': 'ethereum token',
    'LGR': 'ethereum token',
    'LOON': 'ethereum token',
    'LUCY': 'own chain',
    'ME': 'own chain',
    'MILC': 'ethereum token',
    'MNT': 'ethereum token',
    'MNTP': 'ethereum token',
    'MRP': 'ethereum token',
    'MRV': 'ethereum token',
    'MTA': 'ethereum token',
    'NAC': 'ethereum token',
    'OAK': 'ethereum token',
    'OCC-2': 'ethereum token',
    'OXT': 'ethereum token',
    'OGN': 'ethereum token',
    'ONE-2': 'own chain',
    # In reality this is ethereum token and Waves token but got no way to
    # signify this with the current system apart from creating a new type.
    # So now I created a new generic type.
    # Either think of a change in the
    # system or just ignore it if it's just one token. Essentially PrimalBase
    # seems to have both an ethereum and a waves token. If more assets do this
    # then perhaps the system needs to change
    'PBT': 'ethereum token and more',
    'PLT': 'ethereum token',
    'POP-2': 'ethereum token',
    'REA': 'ethereum token',
    'REDC': 'ethereum token',
    'RIPT': 'ethereum token',
    'RING': 'ethereum token',
    'RNDR': 'ethereum token',
    'RUNE': 'own chain',
    'SKR': 'ethereum token',
    'SKYM': 'ethereum token',
    'SOL-2': 'own chain',
    'SPHTX': 'ethereum token',
    'SPICE': 'ethereum token',
    'STMX': 'ethereum token',
    'SS': 'ethereum token',
    'SRM': 'ethereum token',
    'SSH': 'ethereum token',
    'STP': 'ethereum token',
    'SUTER': 'ethereum token',
    'SUKU': 'ethereum token',
    'SWAP': 'ethereum token',
    'TAN': 'ethereum token',
    'TBT': 'ethereum token',
    'TCH-2': 'ethereum token',
    'TEND': 'ethereum token',
    'TEMCO': 'ethereum token',
    'TNC': 'ethereum token',
    'TOMO': 'ethereum token',
    'TRADE': 'ethereum token',
    'TROY': 'own chain',
    'TRXBEAR': 'ethereum token',
    'TRXBULL': 'ethereum token',
    'URB': 'ethereum token',
    'UTI': 'own chain',
    'USDJ': 'tron token',
    'VENUS': 'ethereum token',
    'VIN': 'ethereum token',
    'WMK': 'ethereum token',
    'WLK': 'ethereum token',
    'WRX': 'binance token',
    'YOYOW': 'ethereum token',
    'ZEUS': 'ethereum token',
    'ZIX': 'ethereum token',
    'ALGO': 'own chain',
    # For some reason the entry for KAVA does not have a platform entry in paprika
    'KAVA': 'own chain',
    'XTP': 'ethereum token',
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
            if asset_symbol in ('ZIL', 'WTC', 'KIN', 'LOCUS', 'MESH', 'ORBS', 'SMS', 'SNBL'):
                our_data[asset_symbol]['type'] = 'ethereum token'
                return our_data

            try:
                parent_id = paprika_data['parent']['id']
            except KeyError:
                parent_id = None

            if parent_id is None:
                try:
                    parent_id = paprika_data['platform']
                except KeyError:
                    parent_id = None

            if parent_id is None:
                print(
                    f'Paprika data for asset {asset_symbol} should have a parent or platform entry'
                )
                sys.exit(1)

            if parent_id == 'omni-omni':
                our_data[asset_symbol]['type'] = 'omni token'
            elif parent_id == 'eth-ethereum':
                our_data[asset_symbol]['type'] = 'ethereum token'
            elif parent_id == 'neo-neo':
                our_data[asset_symbol]['type'] = 'neo token'
            elif parent_id == 'xcp-counterparty':
                our_data[asset_symbol]['type'] = 'counterparty token'
            elif parent_id == 'bts-bitshares':
                our_data[asset_symbol]['type'] = 'bitshares token'
            elif parent_id == 'ardr-ardor':
                our_data[asset_symbol]['type'] = 'ardor token'
            elif parent_id == 'nxt-nxt':
                our_data[asset_symbol]['type'] = 'nxt token'
            elif parent_id == 'ubq-ubiq':
                our_data[asset_symbol]['type'] = 'Ubiq token'
            elif parent_id == 'usnbt-nubits':
                our_data[asset_symbol]['type'] = 'Nubits token'
            elif parent_id == 'burst-burst':
                our_data[asset_symbol]['type'] = 'Burst token'
            elif parent_id == 'waves-waves':
                our_data[asset_symbol]['type'] = 'waves token'
            elif parent_id == 'qtum-qtum':
                our_data[asset_symbol]['type'] = 'qtum token'
            elif parent_id == 'xlm-stellar':
                our_data[asset_symbol]['type'] = 'stellar token'
            elif parent_id == 'trx-tron':
                our_data[asset_symbol]['type'] = 'tron token'
            elif parent_id == 'ont-ontology':
                our_data[asset_symbol]['type'] = 'ontology token'
            elif parent_id == 'vet-vechain':
                our_data[asset_symbol]['type'] = 'vechain token'
            elif parent_id == 'bnb-binance-coin':
                our_data[asset_symbol]['type'] = 'binance token'
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
