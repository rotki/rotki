import sys
from typing import Any, Dict

from asset_aggregator.utils import choose_multiple

# For assets we support but no API has names for. We manually input the names then.
MANUALLY_CHECKED_NAMES = {
    'AMIS': 'Amis',
    'AVA-2': 'Avalon',
    'BITCAR': 'BitCar',
    'BMT': 'BMChain',
    'BOU': 'Boulle',
    'BTCE': 'EthereumBitcoin',
    'BTH': 'Bytether',
    'BTR-2': 'Bither',
    'CET-2': 'DICE Money',
    'CFTY': 'Crafty',
    'CTSI': 'Cartesi',
    'CO2': 'Climatecoin',
    'CRGO': 'CargoCoin',
    'DEPO': 'Depository Network',
    'DIP': 'Etherisc',
    'DPP': 'Digital Assets Power Play',
    'EMT': 'EasyMine',
    'ENTRP': 'Hut34 Entropy Token',
    'ETHB': 'EtherBTC',
    'FIH': 'FidelityHouse',
    'FLX': 'BitFlux',
    'FORK-2': 'Gastro Advisor Token',
    'HBD': 'Hive dollar',
    'HIVE': 'Hive',
    'HKG': 'Hacker Gold',
    'ITM': 'Intimate',
    'JOY': 'JOYSO',
    'KUE': 'Kuende',
    'LGR': 'Logarithm',
    'MILC': 'Micro Licensing Coin',
    'MNT': 'Media Network Token',
    'MRP': 'Money Rebel',
    'MRV': 'Macroverse',
    'OAK': 'Acorn Collective',
    'OCC-2': 'Original Crypto Coin',
    'REA': 'Realisto',
    'REDC': 'Red Cab',
    'RIPT': 'RiptideCoin',
    'RNDR': 'Render Token',
    'SKR': 'Skrilla Token',
    'SKYM': 'Skymap',
    'SPICE': 'Spice VC Token',
    'SSH': 'StreamSpace',
    'STP': 'StashPay',
    'TAN': 'Taklimakan',
    'TBT': 'T-Bot',
    'TRXBEAR': ' 3X Short TRX Token',
    'TRXBULL': ' 3X Long TRX Token',
    'URB': 'Urbit Data',
    'USDJ': 'USDJ',
    'VENUS': 'VenusEnergy',
    'WMK': 'WeMark',
    'WLK': 'Wolk',
    'ZIX': 'Zeex Token',
}


def name_check(
        asset_symbol: str,
        our_asset: Dict[str, Any],
        our_data: Dict[str, Any],
        paprika_data: Dict[str, Any],
        cmc_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Process the name from coin paprika and coinmarketcap

    Then compare to our data and provide choices to clean up the data.
    """

    our_name = our_asset.get('name', None)
    if our_name:
        # If we already got a name from manual input then keep it
        return our_data

    if asset_symbol in MANUALLY_CHECKED_NAMES:
        our_data[asset_symbol]['name'] = MANUALLY_CHECKED_NAMES[asset_symbol]
        return our_data

    paprika_name = None
    if paprika_data:
        paprika_name = paprika_data['name']
    cmc_name = None
    if cmc_data:
        cmc_name = cmc_data['name']

    if not paprika_name and not cmc_name and asset_symbol:
        print(f'No name in any external api for asset {asset_symbol}')
        sys.exit(1)

    if paprika_name == cmc_name:
        # If both external APIs agree just use their name
        our_data[asset_symbol]['name'] = paprika_name
        return our_data

    msg = (
        f'For asset {asset_symbol} the possible names are: \n'
        f'(1) Coinpaprika: {paprika_name}\n'
        f'(2) Coinmarketcap: {cmc_name}\n'
        f'Choose a number (1)-(2) to choose which name to use: '
    )
    choice = choose_multiple(msg, (1, 2))
    if choice == 1:
        name = paprika_name
    elif choice == 2:
        if not cmc_name:
            print("Chose coinmarketcap's name but it's empty. Bailing ...")
            sys.exit(1)
        name = cmc_name

    our_data[asset_symbol]['name'] = name
    return our_data
