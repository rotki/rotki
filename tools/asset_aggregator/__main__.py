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
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from asset_aggregator.active_check import active_check
from asset_aggregator.args import aggregator_args
from asset_aggregator.name_check import name_check
from asset_aggregator.timerange_check import timerange_check
from asset_aggregator.typeinfo_check import typeinfo_check

from rotkehlchen.assets.converters import ETH_TOKENS_JSON_TO_WORLD, UNSUPPORTED_ETH_TOKENS_JSON
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.constants.assets import FIAT_CURRENCIES
from rotkehlchen.externalapis import Coinmarketcap, CoinPaprika, Cryptocompare
from rotkehlchen.externalapis.coinmarketcap import find_cmc_coin_data
from rotkehlchen.externalapis.coinpaprika import find_paprika_coin_id
from rotkehlchen.externalapis.cryptocompare import (
    KNOWN_TO_MISS_FROM_CRYPTOCOMPARE,
    WORLD_TO_CRYPTOCOMPARE,
)
from rotkehlchen.utils import rlk_jsonloads


def process_asset(
        our_data: Dict[str, Dict[str, Any]],
        asset_symbol: str,
        paprika_coins_list: List[Dict[str, Any]],
        paprika: CoinPaprika,
        cmc_list: Optional[List[Dict[str, Any]]],
        cryptocompare_coins_map: Dict[str, Any],
        always_keep_our_time: bool,
        given_by_eth_token_json: bool,
) -> Dict[str, Any]:
    """
    Process a single asset symbol. Compare to all external APIs and if there is no
    local data on the symbol query the user on which data to use for each asset attribute.
    """
    if given_by_eth_token_json:
        if asset_symbol in UNSUPPORTED_ETH_TOKENS_JSON:
            return our_data

        asset_symbol = ETH_TOKENS_JSON_TO_WORLD.get(asset_symbol, asset_symbol)

        our_data[asset_symbol] = {}

    our_asset = our_data[asset_symbol]
    # Coin paprika does not have info on FIAT currencies
    if asset_symbol in FIAT_CURRENCIES:
        return our_data

    found_coin_id = find_paprika_coin_id(asset_symbol, paprika_coins_list)
    if found_coin_id:
        paprika_coin_data = paprika.get_coin_by_id(found_coin_id)
    else:
        paprika_coin_data = None
    cmc_coin_data = find_cmc_coin_data(asset_symbol, cmc_list)

    our_data = timerange_check(
        asset_symbol=asset_symbol,
        our_asset=our_asset,
        our_data=our_data,
        paprika_data=paprika_coin_data,
        cmc_data=cmc_coin_data,
        always_keep_our_time=always_keep_our_time,
    )
    our_data = name_check(
        asset_symbol=asset_symbol,
        our_asset=our_asset,
        our_data=our_data,
        paprika_data=paprika_coin_data,
        cmc_data=cmc_coin_data,
    )
    our_data = active_check(
        asset_symbol=asset_symbol,
        our_asset=our_asset,
        our_data=our_data,
        paprika_data=paprika_coin_data,
        cmc_data=cmc_coin_data,
    )
    our_data = typeinfo_check(
        asset_symbol=asset_symbol,
        our_asset=our_asset,
        our_data=our_data,
        paprika_data=paprika_coin_data,
        cmc_data=cmc_coin_data,
    )
    if given_by_eth_token_json:
        assert our_data[asset_symbol]['type'] == 'ethereum token'
    # add the symbol as an asset attribute in the data
    symbol = asset_symbol
    match = re.search('(.*)-\\d+', symbol)
    # If our key is a numbered key, like 'PAI-2', 'PAI-3' e.t.c. use the
    # non suffixed symbol, iow just 'PAI'
    if match:
        symbol = match.group(1)
    our_data[asset_symbol]['symbol'] = symbol

    # Make sure that the asset is also known to cryptocompare
    cryptocompare_symbol = WORLD_TO_CRYPTOCOMPARE.get(asset_symbol, asset_symbol)
    cryptocompare_problem = (
        asset_symbol not in KNOWN_TO_MISS_FROM_CRYPTOCOMPARE and
        cryptocompare_symbol not in cryptocompare_coins_map
    )
    if cryptocompare_problem:
        print(f'Asset {asset_symbol} is not in cryptocompare')
        sys.exit(1)

    return our_data


def main():
    arg_parser = aggregator_args()
    args = arg_parser.parse_args()
    our_data = AssetResolver().assets
    paprika = CoinPaprika()
    cmc = None
    cmc_list = None
    root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
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

    if args.input_file:
        if not os.path.isfile(args.input_file):
            print(f'Given input file {args.input_file} is not a file')
            sys.exit(1)

        with open(args.input_file, 'r') as f:
            input_data = rlk_jsonloads(f.read())

        given_symbols = set(input_data.keys())
        current_symbols = set(our_data.keys())
        if not given_symbols.isdisjoint(current_symbols):
            print(
                f'The following given input symbols already exist in the '
                f'all_assets.json file {given_symbols.intersection(current_symbols)}',
            )
            sys.exit(1)

        # If an input file is given, iterate only its assets and perform checks
        for asset_symbol in input_data.keys():
            input_data = process_asset(
                our_data=input_data,
                asset_symbol=asset_symbol,
                paprika_coins_list=paprika_coins_list,
                paprika=paprika,
                cmc_list=cmc_list,
                cryptocompare_coins_map=cryptocompare_coins_map,
                always_keep_our_time=args.always_keep_our_time,
                given_by_eth_token_json=False,
            )

        # and now combine the two dictionaries to get the final one. Note that no
        # checks are perfomed for what was in all_assets.json before the script
        # ran in this case
        our_data = {**our_data, **input_data}

    elif args.process_eth_tokens:
        with open(os.path.join(root_path, 'rotkehlchen', 'data', 'eth_tokens.json'), 'r') as f:
            token_data = rlk_jsonloads(f.read())

        start = 16
        stop_after = start + 2
        input_data = {}
        for index, entry in enumerate(token_data[start:], start):
            token_symbol = entry['symbol']
            # at least for now skip all already known tokens
            if ETH_TOKENS_JSON_TO_WORLD.get(token_symbol, token_symbol) in our_data:
                print(f"Skipping ETH token {token_symbol} since it's already known")
            else:
                input_data = process_asset(
                    our_data=input_data,
                    asset_symbol=token_symbol,
                    paprika_coins_list=paprika_coins_list,
                    paprika=paprika,
                    cmc_list=cmc_list,
                    cryptocompare_coins_map=cryptocompare_coins_map,
                    always_keep_our_time=args.always_keep_our_time,
                    given_by_eth_token_json=True,
                )

            if index >= stop_after:
                break

        # and now combine the two dictionaries to get the final one. Note that no
        # checks are perfomed for what was in all_assets.json before the script
        # ran in this case
        our_data = {**our_data, **input_data}

    else:
        # Iterate all of the assets of the all_assets.json file and perform checks
        for asset_symbol in our_data.keys():
            our_data = process_asset(
                our_data=our_data,
                asset_symbol=asset_symbol,
                paprika_coins_list=paprika_coins_list,
                paprika=paprika,
                cmc_list=cmc_list,
                cryptocompare_coins_map=cryptocompare_coins_map,
                always_keep_our_time=args.always_keep_our_time,
                given_by_eth_token_json=False,
            )

    # Finally overwrite the all_assets.json with the modified assets
    with open(os.path.join(root_path, 'rotkehlchen', 'data', 'all_assets.json'), 'w') as f:
        f.write(
            json.dumps(
                our_data, sort_keys=True, indent=4,
            ),
        )


if __name__ == "__main__":
    main()
