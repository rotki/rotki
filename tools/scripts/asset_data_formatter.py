import os
import sys

from rotkehlchen.assets.architecture import AssetResolver
from rotkehlchen.externalapis.coinpaprika import CoinPaprika
from rotkehlchen.utils import iso8601ts_to_timestamp, rlk_jsondumps


def main():
    our_data = AssetResolver().assets
    paprika = CoinPaprika()
    coins_list = paprika.get_coins_list()

    for asset in our_data.keys():
        found_coin_id = None
        for coin in coins_list:
            if coin['symbol'] == asset:
                found_coin_id = coin['id']
                break

        if not found_coin_id:
            print(
                f"Could not find asset with canonical symbol {asset} in coin "
                f"coinpaprikas coin list",
            )
            sys.exit(1)

        coin_data = paprika.get_coin_by_id(found_coin_id)
        started = coin_data['started_at']
        if not started:
            print(f'Did not find a started date for asset {asset}')
            continue

        our_data[asset]['started'] = iso8601ts_to_timestamp(started)

    dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    with open(os.path.join(dir_path, 'rotkehlchen', 'data', 'all_assets.json'), 'w') as f:
        f.write(rlk_jsondumps(our_data))


if __name__ == "__main__":
    main()
