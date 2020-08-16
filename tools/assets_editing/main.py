import json
import sys
from pathlib import Path

from Levenshtein import distance as levenshtein_distance

from rotkehlchen.config import default_data_directory
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.utils.serialization import rlk_jsondumps


def find_coingecko_by_id(identifier: str, coins):
    for coingecko_entry in coins:
        if coingecko_entry['id'] == identifier:
            return coingecko_entry

    return None


root_dir = Path(__file__).resolve().parent.parent.parent
ASSETS_FILE = Path(f'{root_dir}/rotkehlchen/data/all_assets.json')
with open(ASSETS_FILE, 'r') as f:
    assets = json.loads(f.read())

coingecko = Coingecko()
COINGECKO_COINS_FILE = default_data_directory() / 'coingecko.json'

if COINGECKO_COINS_FILE.exists():
    with open(COINGECKO_COINS_FILE, 'r') as f:
        coingecko_coins = json.loads(f.read())
else:
    coingecko_coins = coingecko.all_coins()
    with open(COINGECKO_COINS_FILE, 'w') as f:
        f.write(rlk_jsondumps(coingecko_coins))


coingecko_add = {
    'BTT': 'bittorrent',
    'BTT-2': 'blocktrade',
    'FTT': 'farmatrust',
    'SNX': 'synthetix-network-token',
    '0xBTC': '0xbitcoin',
    '1SG': '1sg',
    '1ST': 'first-blood',
    '1WO': '1world',
    '2GIVE': '2give',
    'ABBC': 'abbc',
}

not_supported_in_coingecko = {'1CR', '300'}

new_assets = {}
should_stop = False
changed = 2  # due to me manually changing BTC and YFI
same_name_count = 0
same_symbol_count = 0
for key, entry in assets.items():
    new_assets[key] = entry

    if key in not_supported_in_coingecko:
        continue

    # Under here do entry specific editing
    if not should_stop and 'coingecko' not in new_assets:

        if key in coingecko_add:
            new_assets[key]['coingecko'] = coingecko_add[key]
            changed += 1
            continue

        for coingecko_entry in coingecko_coins:
            same_symbol = coingecko_entry['symbol'] == entry['symbol'].lower()
            entry_name = entry['name'].lower().replace(' ', '-')
            same_name = coingecko_entry['name'] == entry_name

            if same_symbol:
                new_assets[key]['coingecko'] = coingecko_entry['id']
                changed += 1
                same_symbol_count += 1

            if same_name:
                same_name_count += 1
                if not same_symbol:
                    changed += 1
                    new_assets[key]['coingecko'] = coingecko_entry['id']
                    print(f'Found asset with same name but not same symbol {coingecko_entry}')

            distance = levenshtein_distance(coingecko_entry['name'], entry_name)
            if distance <= 1 and 'coingecko' not in new_assets[key]:
                print(
                    f'Similar names. Our-id: {key}. Coingecko-id: {coingecko_entry["id"]}.'
                    f' Our-name: {entry["name"]}. Coingecko-name: {coingecko_entry["name"]}'
                )

    # if 'coingecko' not in new_assets[key]:
    #     __import__("pdb").set_trace()
    #     a = 1


        # if len(coingecko_add) == 0:
        #     print(f'{key} does not yet have a coingecko mapping')
        #     sys.exit(0)


print(f'Managed to automatically map {changed}/{len(assets)} assets for coingecko')
print(f'Same name assets: {same_name_count}/{len(assets)}')
print(f'Same symbol assets: {same_symbol_count}/{len(assets)}')

with open(ASSETS_FILE, 'w') as f:
    f.write(
        json.dumps(
            new_assets, sort_keys=True, indent=4,
        ),
    )
