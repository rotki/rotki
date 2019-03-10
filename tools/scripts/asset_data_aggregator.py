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
from typing import Any, Dict, List

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.constants import FIAT_CURRENCIES
from rotkehlchen.externalapis import CoinPaprika, Cryptocompare
from rotkehlchen.utils import createTimeStamp

KNOWN_TO_MISS_FROM_COIN_PAPRIKA = ('DAO', 'KFEE', '1CR')

# These are just here for documentation and to make sure we search
# for a started date for each of them
NO_STARTED_AT_COIN_PAPRIKA = ('BSV', 'ICN', 'MLN', 'VEN', 'REP')

# For these assets we will definitely always use our data as they are more accurate
PREFER_OUR_STARTED = (
    # BCH forked on https://www.blockchain.com/btc/block-height/478558
    # and our data contain the correct timestamp
    'BCH',
    # The first BTC block timestamp is wrong in coin paprika. Our data is accurate
    # Taken from https://www.blockchain.com/btc/block-height/0
    'BTC',
    # The first DASH block is wrong in coin paprika. Our data is accurate.
    # Taken from:
    # https://explorer.dash.org/block/00000ffd590b1485b3caadc19b22e6379c733355108f107a430458cdf3407ab6
    'DASH',
    # The first DOGE block is wrong in coin paprika. Our data is accurate.
    # Taken from: https://dogechain.info/block/0
    'DOGE',
    # ETC forked on https://etherscan.io/block/1920000 and our data contain the
    # correct timestamp
    'ETC',
    # https://www.cryptoninjas.net/2017/04/24/gnosis-token-sale-ends-312-8-million-raised-hour/
    # Gno token sale ended on 24/04/2017 not on 2015 ..
    'GNO',
    # LTC first block was mined https://blockchair.com/litecoin/block/0
    # our data is more accurate
    'LTC',
    # Namecoin's first block was mined https://namecha.in/block/0
    # our data is more accurate
    'NMC',
    # VET is a cotinuation of VEN and coinpaprika regards VET's started as VEN's
    # started which is not what we need
    'VET',
    # Coin paprika's stellar XLM date is one year earlier than the actual launch
    # .. no idea why
    'XLM',
    # Monero's first block is mined https://moneroblocks.info/block/1
    # Our data is more accurate
    'XMR',
    # ZEC's first block is mined https://explorer.zcha.in/blocks/1
    # Our data is more accurate
    'ZEC',
)


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


def find_paprika_coin_id(asset: str, paprika_coins_list: List[Dict[str, Any]]) -> str:
    found_coin_id = None

    if asset in COINPAPRIKA_LOCK_SYMBOL_ID_MAP:
        return COINPAPRIKA_LOCK_SYMBOL_ID_MAP[asset]

    for coin in paprika_coins_list:
        if coin['symbol'] == asset:
            if found_coin_id:
                print(
                    f'Asset with symbol {asset} was found in coin paprika both '
                    f'with id {found_coin_id} and {coin["id"]}',
                )
                sys.exit(1)

            found_coin_id = coin['id']

    if not found_coin_id:
        print(
            f"Could not find asset with canonical symbol {asset} in coin "
            f"coinpaprika's coin list",
        )
        sys.exit(1)

    return found_coin_id


def main():
    our_data = AssetResolver().assets
    paprika = CoinPaprika()
    cryptocompare = Cryptocompare(data_directory='/tmp')
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
        coin_data = paprika.get_coin_by_id(found_coin_id)

        # Process the started_at data from coin paprika
        started = coin_data['started_at']
        if not started:
            print(f'Did not find a started date for asset {asset}')
        else:
            timestamp = createTimeStamp(started, formatstr='%Y-%m-%dT%H:%M:%SZ')
            our_started = our_asset.get('started', None)
            if our_started and timestamp != our_asset['started']:
                prefix = (
                    f"For asset {asset} our data have {our_asset['started']} "
                    f"as starting timestamp while coin paprika has {timestamp}. "
                )
                if asset in PREFER_OUR_STARTED:
                    print(f'{prefix} Our data is known to be more accurate. -- IGNORING')
                    continue

                question = f'{prefix} Replace ours with theirs?'
                if yes_or_no(question):
                    our_data[asset]['started'] = timestamp
            elif not our_started:
                question = (
                    f"For asset {asset} we have no starting timestamp "
                    f"Should we use coinpaprika's {timestamp} ?"
                )
                if not yes_or_no(question):
                    print("Can't find a starting timestamp for {asset}. Bailing ...")
                    sys.exit(1)

        # Process whether the is_active info agree
        if 'active' in our_asset and our_asset['active'] != coin_data['is_active']:
            print(
                f'Our data believe that {asset} active is {our_asset["active"]} '
                f'but coin paprika believes active is {coin_data["is_active"]}',
            )
            sys.exit(1)

        # Process whether the type info agree
        mismatch = (
            (our_asset['type'] == 'own chain' and coin_data['type'] != 'coin') or
            (our_asset['type'] == 'ethereum token' and coin_data['type'] != 'token') or
            (our_asset['type'] == 'omni token' and coin_data['type'] != 'token') or
            (our_asset['type'] == 'ethereum token and own chain' and coin_data['type'] != 'coin')
        )
        if mismatch:
            print(
                f'Our data believe that {asset} type is {our_asset["type"]} '
                f'but coin paprika believes it is {coin_data["type"]}',
            )
            sys.exit(1)

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
