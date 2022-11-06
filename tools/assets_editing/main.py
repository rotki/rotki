import json
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

data_dir = default_data_directory()
coingecko = Coingecko()
COINGECKO_COINS_FILE = data_dir / 'coingecko.json'

if COINGECKO_COINS_FILE.exists():
    with open(COINGECKO_COINS_FILE, 'r') as f:
        coingecko_coins = json.loads(f.read())
else:
    coingecko_coins = coingecko.all_coins()
    with open(COINGECKO_COINS_FILE, 'w') as f:
        f.write(rlk_jsondumps(coingecko_coins))


coingecko_add = {
    'FTT': 'farmatrust',
    'SNX': 'synthetix-network-token',
    '0xBTC': '0xbitcoin',
    '1SG': '1sg',
    '1ST': 'first-blood',
    '1WO': '1world',
    '2GIVE': '2give',
    'ABBC': 'abbc',


    'ACC-3': 'accelerator-network',
    'ARB': 'arbitrage',
    'ARB-2': 'arbit-coin',
    'ARC': 'advanced-technology-coin',

    'ATX': 'aston',
    'ATX-2': 'artex-coin',
    'AVA': 'travala',
    'BBK': 'brickblock',
    'BBK-2': 'bitblocks-project',
    'BITS': 'bitstar',
    'BITS-2': 'bitswift',
    'BLOC': 'blockcloud',
    'BLOC-2': 'bloc-money',
    'BLZ': 'bluzelle',
    'BOX': 'box-token',
    'BOX-2': 'contentbox',
    'BTG': 'bitcoin-gold',
    'BTG-2': 'bitgem',
    'BTM': 'bitmark',
    'BTM-2': 'bytom',
    'BTR': 'bitether',
    'BTT': 'bittorrent',
    'BTT-2': 'blocktrade',
    'CAN': 'canyacoin',
    'CAT': 'bitclave',
    'CBC': 'cashbet-coin',
    'CBC-2': 'cashbery-coin',
    'CCN': 'custom-contract-network',
    'CET': 'coinex-token',
    'CMCT': 'crowd-machine',
    'CMCT-2': 'cyber-movie-chain',
    'CMT': 'cybermiles',
    'CPC': 'cpchain',
    'CPC-2': 'capricoin',
    'CRC': 'crycash',
    'CTX': 'centauri-coin',
    'DEC': 'darico-ecosystem-coin',
    'DEC-2': 'decentr',
    'DTX': 'data-exchange-token',
    'DTX-2': 'digital-ticks',
    'EDR': 'endor-protocol-token',
    'EDU': 'educoin',
    'EVN': 'envion',
    'EVN-2': 'evencoin',
    'EXC-2': 'eximchain',
    'FAIR-2': 'fairgame',
    'FORK-2': 'gastroadvisor',
    'GBX': 'gobyte',
    'GBX-2': 'globitex',
    'GENE': 'parkgene',
    'GENE-2': 'gene-source-code-token',
    'GET': 'get-protocol',
    'GET-2': 'themis',
    'GLC': 'goldcoin',
    'GLC-2': 'globalcoin',
    'GOT': 'gonetwork',
    'GOT-2': 'parkingo',
    'HC': 'hypercash',
    'HMC': 'hi-mutual-society',
    'HMC-2': 'harmonycoin',
    'HOT': 'holo',
    'HOT-2': 'hydro-protocol',
    'IQ': 'everipedia',
    'IQ-2': 'iq-cash',
    'KEY': 'selfkey',
    'KEY-2': 'key',
    'KNC': 'kyber-network',
    'KNT': 'kora-network',
    'KNT-2': 'knekted',
    'LNC': 'blocklancer',
    'LNC-2': 'linker-coin',
    'LUNA-2': 'terra-luna',
    'MORE': 'legends-room',
    'MTC': 'doc-com',
    'MTC-2': 'mtc-mesh-network',
    'NCC': 'neurochain',
    'NTK': 'neurotoken',
    'NTK-2': 'netkoin',
    'ONG': 'ontology-gas',
    'ONG-2': 'ong-social',
    'ORS': 'origin-sport',
    'ORS-2': 'orsgroup-io',
    'PAI': 'project-pai',
    'PAI-2': 'pchain',
    'PASS': 'blockpass',
    'PLA': 'plair',
    'PLA-2': 'playchip',
    'PNT': 'pnetwork',
    'PNT-2': 'penta-network-token',
    'POLY': 'polymath-network',
    'POP': 'popularcoin',
    'RCN': 'ripio-credit-network',
    'RCN-2': 'rcoinchain',
    'SLT': 'smartlands',
    'SLT-2': 'social-lending-token',
    'SMART': 'smartcash',
    'SOL-2': 'solana',
    'SOUL': 'phantasma',
    'SOUL-2': 'cryptosoul',
    'SPD': 'spindle',
    'SPD-2': 'stipend',
    'TCH': 'thorecash',
    'TCH-2': 'tigercash',
    'USDS': 'stably',
    'WEB': 'webcoin',
    'WIN-2': 'wcoin',
}

not_supported_in_coingecko = {
    '1CR',
    '300',
    'ACC',
    'AIR',
    'AIR-2',
    'APH',
    'ARC-2',
    'AVA-2',
    'BET',
    'BET-2',
    'BTR-2',
    'CAN-2',
    'CCN-2',
    'CET-2',
    'CMT-2',
    'CRC-2',
    'CTX-2',
    'EDR-2',
    'FAIR',
    'FT',
    'HC-2',
    'KEY-3',
    'LCT',
    'OCC',
    'POP-2',
    'SOL',
    'WEB-2',
    'WIN',
    'ADADOWN',
    'ADAUP',
    'AERO',
}

new_assets = {}
should_stop = False
changed = 2  # due to me manually changing BTC and YFI
same_name_count = 0
same_symbol_count = 0
for key, entry in assets.items():
    new_assets[key] = entry

    if entry['type'] == 'fiat':
        continue

    if key in not_supported_in_coingecko:
        new_assets[key]['coingecko'] = ''
        changed += 1
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
                    f' Our-name: {entry["name"]}. Coingecko-name: {coingecko_entry["name"]}',
                )

    # if 'coingecko' not in new_assets[key]:
    #     __import__("pdb").set_trace()
    #     a = 1


print(f'Managed to automatically map {changed}/{len(assets)} assets for coingecko')
print(f'Same name assets: {same_name_count}/{len(assets)}')
print(f'Same symbol assets: {same_symbol_count}/{len(assets)}')

with open(ASSETS_FILE, 'w') as f:
    f.write(
        json.dumps(
            new_assets, sort_keys=True, indent=4,
        ),
    )
