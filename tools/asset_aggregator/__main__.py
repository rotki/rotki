"""
Aggregates data from various sources along with manually input data from us
in order to create the all_assets.json file


How do we manually get the started at if the coin paprika one is non-existent
or inaccurate?

1. Check internet to see if there was a presale and get its start date
2. Get coinmarket's cap price start range (not using their API due to the
   derivative work ToS clause)
3. If it is an own chain token find the first block mined timestamp
4. It it's a token sale find when it started.

"""

import json
import os
import sys
from typing import Any, Dict, List, Optional

from asset_aggregator.args import aggregator_args
from asset_aggregator.name_check import name_check
from asset_aggregator.timerange_check import timerange_check
from asset_aggregator.typeinfo_check import typeinfo_check

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.constants import FIAT_CURRENCIES
from rotkehlchen.externalapis import Coinmarketcap, CoinPaprika, Cryptocompare

KNOWN_TO_MISS_FROM_COIN_PAPRIKA = ('DAO', 'KFEE', '1CR')

# These are just here for documentation and to make sure we search
# for a started date for each of them
NO_STARTED_AT_COIN_PAPRIKA = ('BSV', 'ICN', 'MLN', 'VEN', 'REP')

# Some symbols in coin paprika exists multiple times with different ids each time.
# This requires manual intervention and a lock in of the id mapping by hand
COINPAPRIKA_LOCK_SYMBOL_ID_MAP = {
    # ICN has both icn-iconomi and icn-icoin. The correct one appears to be the first
    'ICN': 'icn-iconomi',
}


def yes_or_no(question: str):
    """From https://gist.github.com/garrettdreyfus/8153571#gistcomment-2321568"""
    while "the answer is invalid":
        reply = str(input(question + ' (y/n): ')).lower().strip()
        if reply[:1] == 'y':
            return True
        if reply[:1] == 'n':
            return False


def find_paprika_coin_id(asset_symbol: str, paprika_coins_list: List[Dict[str, Any]]) -> str:
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

    found_coin_data = None
    for coin in cmc_list:
        if coin['symbol'] == asset_symbol:
            if found_coin_data:
                print(
                    f'Asset with symbol {asset_symbol} was found in cryptocompare '
                    f'both with id {found_coin_data["id"]} and {coin["id"]}',
                )
                sys.exit(1)
            found_coin_data = coin

    if not found_coin_data:
        print(
            f"Could not find asset with canonical symbol {asset_symbol} in "
            f"cryptocompares's coin list",
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
    if args.cmc_api_key:
        cmc = Coinmarketcap(
            data_directory='~/.rotkehlchen',
            api_key=args.cmc_api_key,
        )
        cmc_list = cmc.get_cryptocyrrency_map()

    cryptocompare = Cryptocompare(data_directory='~/.rotkehlchen')
    paprika_coins_list = paprika.get_coins_list()
    cryptocompare_coins_map = cryptocompare.all_coins()

    for asset in our_data.keys():

        our_asset = our_data[asset]
        # Coin paprika does not have info on FIAT currencies
        if asset in FIAT_CURRENCIES:
            continue

        # after experimentation found out that coin paprika does not have
        # data for these tokens
        if asset in KNOWN_TO_MISS_FROM_COIN_PAPRIKA:
            continue

        found_coin_id = find_paprika_coin_id(asset, paprika_coins_list)
        paprika_coin_data = paprika.get_coin_by_id(found_coin_id)
        cmc_coin_data = find_cmc_coin_data(asset, cmc_list)

        our_data = timerange_check(
            asset_symbol=asset,
            our_asset=our_asset,
            our_data=our_data,
            paprika_data=paprika_coin_data,
            cmc_data=cmc_coin_data,
        )
        our_data = name_check(
            asset_symbol=asset,
            our_asset=our_asset,
            our_data=our_data,
            paprika_data=paprika_coin_data,
            cmc_data=cmc_coin_data,
        )
        typeinfo_check(
            asset_symol=asset,
            our_asset=our_asset,
            paprika_data=paprika_coin_data,
        )

        # Make sure that the asset is also known to cryptocompare
        assetobj = Asset(asset)
        if assetobj.to_cryptocompare() not in cryptocompare_coins_map:
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
