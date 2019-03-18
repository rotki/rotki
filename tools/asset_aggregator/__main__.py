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

from rotkehlchen.assets.asset import WORLD_TO_CRYPTOCOMPARE
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.constants import FIAT_CURRENCIES
from rotkehlchen.externalapis import Coinmarketcap, CoinPaprika, Cryptocompare
from rotkehlchen.externalapis.coinmarketcap import WORLD_TO_CMC_ID
from rotkehlchen.externalapis.coinpaprika import WORLD_TO_PAPRIKA_ID
from rotkehlchen.utils import rlk_jsonloads

KNOWN_TO_MISS_FROM_PAPRIKA = (
    'DAO',
    'KFEE',
    '1CR',
    'ACH',
    'AERO',
    'AM',
    'AIR-2',
    'APH-2',
    'ARCH',
    'CAIX',
    'CGA',
    'CINNI',
    'CNL',
    'CNMT',
    'COMM',
    'DIEM',
    'DRKC',
    'EXE',
    'FIBRE',
    'FRAC',
    'GEMZ',
    'GPUC',
    'GUE',
    'HUGE',
    'HVC',
    'HZ',
    'KEY-3',  # KeyCoin
    'LTBC',
    'LTCX',
    'MCN',
    'MMC',
    'MMNXT',
    'MMXIV',
    'NAUT',
    'NRS',
    'NXTI',
    'POLY-2',  # Polybit
    'RZR',
    'SPA',
    'SQL',
    'SSD',
    'SWARM',  # Swarmcoin  https://coinmarketcap.com/currencies/swarm/
    'SYNC',
    'ULTC',
    'UTIL',
    'VOOT',
    'WOLF',
    'XAI',
    'XCR',
    'XDP',
    'XLB',
    'XPB',
    'XSI',
    'YACC',
)
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
    # Missing from API but is in website: https://coinmarketcap.com/currencies/bitcoindark/
    'BTCD',
    # Missing from API but is in website: https://coinmarketcap.com/currencies/cachecoin/
    'CACH',
    # Missing from API is in website https://coinmarketcap.com/currencies/caix/
    'CAIX',
    # Missing from API is in website https://coinmarketcap.com/currencies/cannacoin/
    'CCN-2',
    # Missing from API is in website https://coinmarketcap.com/currencies/cryptographic-anomaly/
    'CGA',
    # Missing from API, is in website https://coinmarketcap.com/currencies/cinni/
    'CINNI',
    # Missing from API, is in website https://coinmarketcap.com/currencies/concealcoin/
    'CNL',
    # Missing from API, is in website https://coinmarketcap.com/currencies/coinomat/
    'CNMT',
    # Missing from API, is in website https://coinmarketcap.com/currencies/communitycoin/
    'COMM',
    # Missing from API, is in website https://coinmarketcap.com/currencies/cryptcoin/
    'CRYPT',
    # Missing from API, is in https://coinmarketcap.com/currencies/conspiracycoin/
    'CYC',
    # Missing from API, is in https://coinmarketcap.com/currencies/diem/
    'DIEM',
    # Missing from API, is in https://coinmarketcap.com/currencies/darkcash/
    'DRKC',
    # Missing from API, is in https://coinmarketcap.com/currencies/dashcoin/
    'DSH',
    # Missing from API, is in https://coinmarketcap.com/currencies/earthcoin/
    'EAC',
    # Missing from API, is in https://coinmarketcap.com/currencies/execoin/
    'EXE',
    # Missing from API, is in https://coinmarketcap.com/currencies/fantomcoin/
    'FCN',
    # Missing from API, is in https://coinmarketcap.com/currencies/fibre/
    'FIBRE',
    # Missing from API, is in https://coinmarketcap.com/currencies/flappycoin/
    'FLAP',
    # Missing from API, is in https://coinmarketcap.com/currencies/fluttercoin/
    'FLT',
    # Missing from API, is in https://coinmarketcap.com/currencies/fractalcoin/
    'FRAC',
    # Missing from API, is in https://coinmarketcap.com/currencies/franko/
    'FRK',
    # Missing from API, is in https://coinmarketcap.com/currencies/gapcoin/
    'GAP',
    # Missing from API, is in https://coinmarketcap.com/currencies/gems/
    'GEMZ',
    # Missing from API, is in https://coinmarketcap.com/currencies/gameleaguecoin/
    'GML',
    # Missing from API, is in https://coinmarketcap.com/currencies/gpucoin/
    'GPUC',
    # Missing from API, is in https://coinmarketcap.com/currencies/guerillacoin/
    'GUE',
    # Missing from API, is in https://coinmarketcap.com/currencies/bigcoin/
    'HUGE',
    # Missing from API, is in https://coinmarketcap.com/currencies/heavycoin/
    'HVC',
    # Missing from API, is in https://coinmarketcap.com/currencies/next-horizon/
    'HZ',
    # Missing from API, is in https://coinmarketcap.com/currencies/klondikecoin/
    'KDC',
    # Missing from API, is in https://coinmarketcap.com/currencies/keycoin/
    'KEY-3',
    # Missing from API, is in https://coinmarketcap.com/currencies/leafcoin/
    'LEAF',
    # Missing from API, is in https://coinmarketcap.com/currencies/ltbcoin/
    'LTBC',
    # Missing from API, is in https://coinmarketcap.com/currencies/litecoinx/
    'LTCX',
    # Missing from API, is in https://coinmarketcap.com/currencies/monetaverde/
    'MCN',
    # Missing from API, is in https://coinmarketcap.com/currencies/minerals/
    'MIN',
    # Missing from API, is in https://coinmarketcap.com/currencies/memorycoin/
    'MMC',
    # Missing from API, is in https://coinmarketcap.com/currencies/mmnxt/
    'MMNXT',
    # Missing from API, is in https://coinmarketcap.com/currencies/mmxiv/
    'MMXIV',
    # Missing from API, is in https://coinmarketcap.com/currencies/marscoin/
    'MARS',
    # Missing from API, is in https://coinmarketcap.com/currencies/mazacoin/
    'MAZA',
    # Missing from API, is in https://coinmarketcap.com/currencies/nautiluscoin/
    'NAUT',
    # Missing from API, is in https://coinmarketcap.com/currencies/noblecoin/
    'NOBL',
    # Missing from API, is in https://coinmarketcap.com/currencies/noirshares/
    'NRS',
    # Missing from API, is in https://coinmarketcap.com/currencies/nxtinspect/
    'NXTI',
    # Missing from API is https://coinmarketcap.com/currencies/polybit/
    'POLY-2',
    # Missing from API is https://coinmarketcap.com/currencies/prospercoin/
    'PRC',
    # Missing from API is https://coinmarketcap.com/currencies/prcoin/
    'PRC-2',
    # Missing from API is https://coinmarketcap.com/currencies/qubitcoin/
    'Q2C',
    # Missing from API is https://coinmarketcap.com/currencies/qibuck/
    # and https://coinmarketcap.com/currencies/qibuck-asset/
    'QBK',
    # Missing from API is https://coinmarketcap.com/currencies/quazarcoin-old/
    # There is also a new one but we don't support the symbol yet
    # https://coinmarketcap.com/currencies/quasarcoin/ (QAC)
    'QCN',
    # Missing from API is https://coinmarketcap.com/currencies/qora/
    'QORA',
    # Missing from API is https://coinmarketcap.com/currencies/quatloo/
    'QTL',
    # Missing from API is https://coinmarketcap.com/currencies/riecoin/
    'RIC',
    # Missing from API is https://coinmarketcap.com/currencies/razor/
    'RZR',
    # Missing from API is https://coinmarketcap.com/currencies/shadowcash/
    'SDC',
    # Missing from API is https://coinmarketcap.com/currencies/silkcoin/
    'SILK',
    # Missing from API is https://coinmarketcap.com/currencies/spaincoin/
    'SPA',
    # Squallcoin. Completely missing ... but is in cryptocompare
    'SQL',
    # Missing from API is https://coinmarketcap.com/currencies/sonicscrewdriver/
    'SSD',
    # Missing from API is https://coinmarketcap.com/currencies/swarm/
    'SWARM',
    # Missing from API is https://coinmarketcap.com/currencies/sync/
    'SYNC',
    # Missing from API is https://coinmarketcap.com/currencies/torcoin-tor/
    'TOR',
    # Missing from API is https://coinmarketcap.com/currencies/trustplus/
    'TRUST',
    # Missing from API is https://coinmarketcap.com/currencies/unitus/
    'UIS',
    # Missing from API is https://coinmarketcap.com/currencies/umbrella-ltc/
    'ULTC',
    # Missing from API is https://coinmarketcap.com/currencies/supernet-unity/
    'UNITY',
    # Missing from API is https://coinmarketcap.com/currencies/uro/
    'URO',
    # Missing from API is https://coinmarketcap.com/currencies/usde/
    'USDE',
    # Missing from API is https://coinmarketcap.com/currencies/utilitycoin/
    'UTIL',
    # Missing from API is https://coinmarketcap.com/currencies/vootcoin/
    'VOOT',
    # InsanityCoin (WOLF). Completely missing ... but is in cryptocompare
    'WOLF',
    # Missing from API is https://coinmarketcap.com/currencies/sapience-aifx/
    'XAI',
    # Missing from API is https://coinmarketcap.com/currencies/crypti/
    'XCR',
    # Missing from API is https://coinmarketcap.com/currencies/dogeparty/
    'XDP',
    # Missing from API is https://coinmarketcap.com/currencies/libertycoin/
    'XLB',
    # Missing from API is https://coinmarketcap.com/currencies/pebblecoin/
    'XPB',
    # Missing from API is https://coinmarketcap.com/currencies/stabilityshares/
    'XSI',
    # Missing from API is https://coinmarketcap.com/currencies/vcash/
    'XVC',
    # Missing from API is https://coinmarketcap.com/currencies/yaccoin/
    'YACC',
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
    # BTCTalkCoin is not in cryptocompare but it's in coin paprika
    # https://api.coinpaprika.com/v1/coins/talk-btctalkcoin and in coinmarketcap
    # https://coinmarketcap.com/currencies/btctalkcoin/#charts
    'TALK',
    # CCN is CustomContractNetwork in Rotkehlchen but Cannacoin in cryptocompare
    # and cryptocompare does not have data for CustomContractNetwork
    'CCN',
    # Dreamcoin (https://coinmarketcap.com/currencies/dreamcoin/#charts) is not
    # in cryptocompare.
    'DRM',
    # KEY (bihu) (https://coinmarketcap.com/currencies/key/) is not in
    # cryptocompare. But it's in paprika
    'KEY-2',
    # MRS (Marginless) is not in cryptocompare. There is a coin with that
    # symbol there, but it's the MARScoin
    'MRS',
    # PRcoin, known as PRC-2 in Rotkehlcen has no data in cryptocompare
    'PRC-2',
    # Wiki coin/token is not in cryptocompare but is in paprika wiki-wiki-token
    'WIKI',
)

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
# CAIX is "Caishen", known as CAI in poloniex
# https://coinmarketcap.com/currencies/caix/


def find_paprika_coin_id(
        asset_symbol: str,
        paprika_coins_list: List[Dict[str, Any]],
) -> Optional[str]:
    found_coin_id = None
    if asset_symbol in WORLD_TO_PAPRIKA_ID:
        return WORLD_TO_PAPRIKA_ID[asset_symbol]

    if asset_symbol in KNOWN_TO_MISS_FROM_PAPRIKA:
        return None

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

    if asset_symbol in WORLD_TO_CMC_ID:
        coin_id = WORLD_TO_CMC_ID[asset_symbol]
        for coin in cmc_list:
            if coin['id'] == coin_id:
                return coin

        assert False, 'The CMC id should alway be correct. Is our data corrupt?'

    if asset_symbol in KNOWN_TO_MISS_FROM_CMC:
        return None

    found_coin_data = None
    for coin in cmc_list:
        if coin['symbol'] == asset_symbol:
            if found_coin_data:
                print(
                    f'Asset with symbol {asset_symbol} was found in coinmarketcap '
                    f'both as {found_coin_data["id"]} - {found_coin_data["name"]} '
                    f'and {coin["id"]} - {coin["name"]}',
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


def process_asset(
        our_data: Dict[str, Dict[str, Any]],
        asset_symbol: str,
        paprika_coins_list: List[Dict[str, Any]],
        paprika: CoinPaprika,
        cmc_list: Optional[List[Dict[str, Any]]],
        cryptocompare_coins_map: Dict[str, Any],
        always_keep_our_time: bool,
):
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

        with open(args.input_file, 'rb') as f:
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
            )

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
            )

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
