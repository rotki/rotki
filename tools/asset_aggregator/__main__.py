"""
Aggregates data from various sources along with manually input data from us
in order to create the all_assets.json file


How do we manually get the started timestamps if no api has good enough data?

1. Check internet to see if there was a presale and get its start date
2. If it is an own chain token find the first block mined timestamp
3. It it's a token sale find when it started.

"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from asset_aggregator.active_check import active_check
from asset_aggregator.args import aggregator_args
from asset_aggregator.name_check import name_check
from asset_aggregator.timerange_check import timerange_check
from asset_aggregator.typeinfo_check import typeinfo_check

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.constants import FIAT_CURRENCIES
from rotkehlchen.externalapis import Coinmarketcap, CoinPaprika, Cryptocompare

KNOWN_TO_MISS_FROM_PAPRIKA = ('DAO', 'KFEE', '1CR', 'ACH', 'AERO', 'AM', 'AIR-2', 'APH-2', 'ARCH')
KNOWN_TO_MISS_FROM_CMC = (
    'VEN',
    '1CR',
    'DAO',
    'KFEE',
    'AC',
    'ACH',
    'ADN',
    'AERO',
    'AM',
    'AIR-2',
    'AIR',
    'APH-2',
    'ARCH',
)
# TODO: For the ones missing from cryptocompare make sure to also
# disallow price queries to cryptocompare for these assets
KNOWN_TO_MISS_FROM_CRYPTOCOMPARE = (
    # This is just kraken's internal fee token
    'KFEE',
    # For us ACH is the Altcoin Herald token. For cryptocompare it's
    # Achievecoin
    # https://www.cryptocompare.com/coins/ach/overview
    'ACH',
    # We got APH as Aphelion and APH-2 as a very shortlived Aphrodite coin
    # Cryptocompare has no data for Aphrodite coin
    'APH-2',
    # BitcoinTalkCoin is not in cryptocompare but it's in coin paprika
    # https://api.coinpaprika.com/v1/coins/talk-btctalkcoin and in coinmarketcap
    # https://coinmarketcap.com/currencies/btctalkcoin/#charts
    'TALK',
)

# Some symbols in coin paprika exists multiple times with different ids each time.
# This requires manual intervention and a lock in of the id mapping by hand
COINPAPRIKA_LOCK_SYMBOL_ID_MAP = {
    # ICN has both icn-iconomi and icn-icoin. The correct one appears to be the first
    'ICN': 'icn-iconomi',
    # In Rotkehlchen BAT means the basic attention token and not bat-batcoin
    'BAT': 'bat-basic-attention-token',
}

# Info on where data was taken for coins which have no data anywhere
# 1CR. Launch date: https://github.com/1credit/1credit
#      End date: https://coinmarketcap.com/currencies/1credit/
# AC: https://coinmarketcap.com/currencies/asiacoin/#charts
# ACH: https://coinmarketcap.com/currencies/ach/
# ADN: https://coinmarketcap.com/currencies/aiden/
#      Note there is also "adrenaline" but we don't support it yet.
#      If we did it would be with data from:
#      https://coinmarketcap.com/currencies/adrenaline/ and with "ADN-2" symbol
# AERO and AM:
#      https://coinmarketcap.com/currencies/aerocoin/#charts
#      https://www.cryptocompare.com/coins/aero/overview
#      https://www.cryptocompare.com/coins/am/overview
#      https://bitcointalk.org/index.php?topic=955204.0
# AIR-2 is "Aircoin":
#      https://coinmarketcap.com/currencies/aircoin/
# AIR is "Airtoken":
#      https://coinmarketcap.com/currencies/airtoken/#charts


def find_paprika_coin_id(asset_symbol: str, paprika_coins_list: List[Dict[str, Any]]) -> str:

    if asset_symbol in KNOWN_TO_MISS_FROM_PAPRIKA:
        return None

    found_coin_id = None
    if asset_symbol in COINPAPRIKA_LOCK_SYMBOL_ID_MAP:
        return COINPAPRIKA_LOCK_SYMBOL_ID_MAP[asset_symbol]

    for coin in paprika_coins_list:
        if coin['symbol'] == asset_symbol:
            if found_coin_id:
                print(
                    f'Asset with symbol {asset_symbol} was found in coin paprika both '
                    f'with id {found_coin_id} and {coin["id"]}',
                )
                sys.exit(1)

            found_coin_id = coin['id']

    if not found_coin_id:
        print(
            f"Could not find asset with canonical symbol {asset_symbol} in coin "
            f"coinpaprika's coin list",
        )
        sys.exit(1)

    return found_coin_id


def find_cmc_coin_data(
        asset_symbol: str,
        cmc_list: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not cmc_list:
        return None

    if asset_symbol in KNOWN_TO_MISS_FROM_CMC:
        return None

    found_coin_data = None
    for coin in cmc_list:
        if coin['symbol'] == asset_symbol:
            if found_coin_data:
                print(
                    f'Asset with symbol {asset_symbol} was found in coinmarketcap '
                    f'both with id {found_coin_data["id"]} and {coin["id"]}',
                )
                sys.exit(1)
            found_coin_data = coin

    if not found_coin_data:
        print(
            f"Could not find asset with canonical symbol {asset_symbol} in "
            f"coinmarketcap's coin list",
        )
        sys.exit(1)

    return found_coin_data


def main():
    arg_parser = aggregator_args()
    args = arg_parser.parse_args()
    our_data = AssetResolver().assets
    paprika = CoinPaprika()
    cmc = None
    cmc_list = None
    data_directory = f'{Path.home()}/.rotkehlchen'
    if args.cmc_api_key:
        cmc = Coinmarketcap(
            data_directory=data_directory,
            api_key=args.cmc_api_key,
        )
        cmc_list = cmc.get_cryptocyrrency_map()

    cryptocompare = Cryptocompare(data_directory=data_directory)
    paprika_coins_list = paprika.get_coins_list()
    cryptocompare_coins_map = cryptocompare.all_coins()

    for asset in our_data.keys():

        our_asset = our_data[asset]
        # Coin paprika does not have info on FIAT currencies
        if asset in FIAT_CURRENCIES:
            continue

        found_coin_id = find_paprika_coin_id(asset, paprika_coins_list)
        if found_coin_id:
            paprika_coin_data = paprika.get_coin_by_id(found_coin_id)
        else:
            paprika_coin_data = None
        cmc_coin_data = find_cmc_coin_data(asset, cmc_list)

        our_data = timerange_check(
            asset_symbol=asset,
            our_asset=our_asset,
            our_data=our_data,
            paprika_data=paprika_coin_data,
            cmc_data=cmc_coin_data,
            always_keep_our_time=args.always_keep_our_time,
        )
        our_data = name_check(
            asset_symbol=asset,
            our_asset=our_asset,
            our_data=our_data,
            paprika_data=paprika_coin_data,
            cmc_data=cmc_coin_data,
        )
        our_data = active_check(
            asset_symbol=asset,
            our_asset=our_asset,
            our_data=our_data,
            paprika_data=paprika_coin_data,
            cmc_data=cmc_coin_data,
        )
        our_data = typeinfo_check(
            asset_symbol=asset,
            our_asset=our_asset,
            our_data=our_data,
            paprika_data=paprika_coin_data,
            cmc_data=cmc_coin_data,
        )

        # Make sure that the asset is also known to cryptocompare
        assetobj = Asset(asset)
        cryptocompare_problem = (
            asset not in KNOWN_TO_MISS_FROM_CRYPTOCOMPARE and
            assetobj.to_cryptocompare() not in cryptocompare_coins_map
        )
        if cryptocompare_problem:
            print(f'Asset {asset} is not in cryptocompare')
            sys.exit(1)

    # Finally overwrite the all_assets.json with the modified assets
    dir_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    with open(os.path.join(dir_path, 'rotkehlchen', 'data', 'all_assets.json'), 'w') as f:
        f.write(
            json.dumps(
                our_data, sort_keys=True, indent=4,
            ),
        )


if __name__ == "__main__":
    main()
